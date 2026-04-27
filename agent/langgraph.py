import asyncio
import json
import traceback
from typing import Any, AsyncGenerator, List, Optional, Sequence
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import AsyncEngine
from langchain_core.messages import BaseMessage, RemoveMessage, ToolMessage
from schemas.llm import GraphState
from utils.llm_process import dump_messages, handle_response, prepare_message
from services.LLMService import llmservice
from loguru import logger
from agent.tools.tools import tools
from mem0 import AsyncMemory
from langgraph.graph.state import CompiledStateGraph,Command, RunnableConfig
from sqlalchemy.dialects.postgresql import UUID
from schemas.llm import Message
from langgraph.graph import StateGraph,END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver 
from services.memory import memory_service
from langgraph.errors import GraphInterrupt
from langgraph.types import StateSnapshot
from mem0.configs.base import MemoryConfig
from config.config import config

DATABASE_URL =  'postgresql://postgres:123456@localhost:5432/ckpt'
CHCKPT_TABLE = 'checkpoints'


class LangGraphAgent:


    def __init__(self):
        # initialize llm service
        self.llm_service = llmservice
        # bind tools
        self.llm_service.bind_tools(tools)
        self._async_engine:Optional[AsyncEngine] = None
        self._graph:Optional[CompiledStateGraph] = None
        self.memory_service = memory_service
        self.tools_by_name = {tool.name: tool for tool in tools}
        self._connection_pool:Optional[AsyncConnectionPool] = None
        logger.success('agent has been initialized')
    
    async def _get_session_memory(self,session_id:str,query:str) ->str:
        # get relevant memory only within the current session
        try:
            return await self.memory_service.search(session_id=session_id,query=query)
        except Exception as e:
            logger.error(f'failed to get memory,error = {str(e)}')
            return ''

    def _message_role(self, message: Any) -> Optional[str]:
        raw_role = None
        if isinstance(message, dict):
            raw_role = message.get("role") or message.get("type")
        else:
            raw_role = getattr(message, "type", getattr(message, "role", None))

        role_map = {
            "human": "user",
            "ai": "assistant",
            "system": "system",
            "tool": "tool",
            "user": "user",
            "assistant": "assistant",
        }
        return role_map.get(str(raw_role), None)

    def _message_content(self, message: Any) -> str:
        content = message.get("content", "") if isinstance(message, dict) else getattr(message, "content", "")
        if isinstance(content, list):
            blocks = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        blocks.append(str(block.get("text", "")))
                    elif "content" in block:
                        blocks.append(str(block.get("content", "")))
                else:
                    blocks.append(str(block))
            return "".join(blocks)
        return str(content or "")

    def _extract_memory_ids(self, message: BaseMessage) -> List[str]:
        additional_kwargs = dict(getattr(message, "additional_kwargs", {}) or {})
        memory_ids = additional_kwargs.get("memory_ids", [])
        if isinstance(memory_ids, list):
            return [str(memory_id) for memory_id in memory_ids if memory_id]
        return []

    async def _sync_message_memories(
        self,
        session_id: str,
        messages: Sequence[Any],
        config: RunnableConfig,
    ) -> None:
        if self._graph is None or not messages:
            return

        pending_messages: List[BaseMessage] = []
        for message in reversed(list(messages)):
            if not isinstance(message, BaseMessage):
                continue

            role = self._message_role(message)
            if role == "tool":
                continue
            if role not in {"user", "assistant"}:
                if pending_messages:
                    break
                continue

            additional_kwargs = dict(getattr(message, "additional_kwargs", {}) or {})
            if additional_kwargs.get("memory_synced") or additional_kwargs.get("memory_ids") is not None:
                if pending_messages:
                    break
                continue

            if not getattr(message, "id", None) or not self._message_content(message).strip():
                if pending_messages:
                    break
                continue

            pending_messages.append(message)

        if not pending_messages:
            return

        updates: List[BaseMessage] = []
        for message in reversed(pending_messages):
            role = self._message_role(message)
            content = self._message_content(message).strip()

            try:
                memory_ids = await self.memory_service.add_memory(
                    session_id=session_id,
                    message=[{"role": role, "content": content}],
                    metadata={
                        "message_id": str(message.id),
                        "role": role,
                    },
                    infer=False,
                )
            except Exception as memory_error:
                logger.warning(
                    f"failed_to_sync_message_memory,error={str(memory_error)},session_id={session_id},message_id={getattr(message, 'id', None)}"
                )
                continue

            additional_kwargs = dict(getattr(message, "additional_kwargs", {}) or {})
            additional_kwargs["memory_ids"] = memory_ids
            additional_kwargs["memory_synced"] = True
            updates.append(
                message.model_copy(
                    update={"additional_kwargs": additional_kwargs}
                )
            )

        if updates:
            await self._graph.aupdate_state(
                config,
                {"messages": updates},
                as_node="chat",
            )

    def _build_system_prompt(self, session_memory: str) -> str:
        base_prompt = (
            '你是一个猫娘助手，喵喵喵～，能调用工具的情况下尽量调用已有工具实现问题。'
            '调用工具后，必须基于工具结果给出完整结论，不要只输出检索过程、results 列表、'
            'source/chunk 原文片段或原始 tool 返回。'
            '如果回答因为各种原因不得不截断，必须提醒用户，如果可以继续，也要提醒用户'
        )
        memory_block = session_memory.strip()

        if not memory_block or memory_block == 'No relevant memory found':
            return base_prompt

        return (
            f"{base_prompt}\n\n"
            "以下是当前对话的会话记忆，仅对当前 session 生效，"
            "不要把它当作跨会话长期记忆；如果与用户最新消息冲突，以最新消息为准。\n"
            f"{memory_block}"
        )
    
    async def _chat(self,state:GraphState,config:RunnableConfig) -> Command:
        #process message and generate a response

        #get the llm 
        current_llm = self.llm_service.get_llm()

        # get llm info

        # load system prompts
        SYSTEM_PROMPT = self._build_system_prompt(state.session_memory)
        # handle messages in advance
    
        messages = prepare_message(state.messages, current_llm, SYSTEM_PROMPT)

        try:
            # use llm with auto retries and circular fdllback
            # 
            response_message = await self.llm_service.call(dump_messages(messages))
            # process response

            if not response_message.content:
                ak = response_message.additional_kwargs or {}

                response_message.content = (
                ak.get("content")
                or ak.get("text")
                or ak.get("output")
                or ak.get("response")
                or ak.get("reasoning_content")
                or str(ak)
            )
            response_message = handle_response(response_message)


            if response_message.tool_calls:
                goto = 'tool_call'
            else:
                goto = END
            logger.debug(f'goto = {goto}')
            return Command(update = {'messages':state.messages + [response_message]},goto = goto)
        
        except Exception as e:
            logger.error(
                f'llm failed all models,error = {str(e)}'
            )
            raise Exception(f'failed to get response,error = {str(e)}')
          
    async def _call_tool(self,state:GraphState) -> Command:
        #process tool calling
        outputs:List[ToolMessage] = []
        for tool in state.messages[-1].tool_calls:
            # ASYNC INVOKE TOOL
            tool_result = await self.tools_by_name[tool['name']].ainvoke(tool['args'])
            if not isinstance(tool_result, str):
            
                tool_result = json.dumps(tool_result, ensure_ascii=False)
            outputs.append(
                ToolMessage(
                    content= tool_result,
                    name = tool['name'],
                    tool_call_id = tool['id']
                )
            )
        return Command(update={'messages':state.messages + outputs},goto = 'chat')
    

    async def create_graph(self) -> Optional[CompiledStateGraph]:
        # create langchain workflow
        if self._graph is None:
            try:
                # create a graph whose nodes communicate by reading and writing to a shared state.
                graph_builder = StateGraph(GraphState)
                # add a chat node that can go to the end of calling tools or  
                graph_builder.add_node('chat',self._chat,ends = ['tool_call',END])
                graph_builder.add_node('tool_call',self._call_tool,ends = ['chat',END])
                graph_builder.add_conditional_edges(
                    "chat",
                    self._route_after_chat,
                    {"tool_call": "tool_call", END: END}
                )
                # set entry and finish node 
                graph_builder.set_entry_point('chat')
                # get the connection pool of pgsql
                self._checkpointer_cm = AsyncPostgresSaver.from_conn_string(DATABASE_URL)

                self._checkpointer = await self._checkpointer_cm.__aenter__()

                await self._checkpointer.setup()
                self._graph = graph_builder.compile(
                    checkpointer=self._checkpointer
                )

                logger.info('graph created')
                
            except Exception as e:
                logger.error(f"graph_creation_failed,error = {str(e)}")
                raise e
            return self._graph
        
    def _route_after_chat(self, state: GraphState) -> str:
        last_message = state.messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tool_call"
        # if there is not any tool calls,end the conversation
        return END  
    
    async def close_ckpt(self):
        if hasattr(self, "_checkpointer_cm"):
            await self._checkpointer_cm.__aexit__(None, None, None)
    
    async def get_response(self,message:List[Message],session_id:str) -> List[Message]:
        # get response from llm
        if self._graph is None:
            await self.create_graph()
        config = {
            "configurable": {"thread_id": session_id},
            "callbacks": [],
            "metadata": {
                "session_id": session_id,
                "environment": '',
                "debug": '',
            },
        }
        logger.debug(f'config = {config}')
        session_memory = (
            await self._get_session_memory(session_id,message[-1].content)
        ) or 'No relevant memory found'

        try:
            state = await self._graph.aget_state(config=config)
            logger.info('invoke model')
            if state.next:
                logger.info("resuming_interrupted_graph", session_id=session_id, next_nodes=state.next)
                response = await self._graph.ainvoke(
                    Command(resume=message[-1].content),
                    config=config,
                )
            else:
                response = await self._graph.ainvoke(
                    input={"messages": dump_messages(message), "session_memory": session_memory},
                    config=config,
                )
            logger.debug('remembering')
            await self._sync_message_memories(
                session_id,
                response["messages"],
                config,
            )
            r = await self.__process_messages(response['messages'])
            assistant_message = [msg for msg in r if msg.role == 'assistant']
            if assistant_message:
                return [assistant_message[-1]]

            logger.warning('no assistant message found in response')
            return []
        except Exception as e:
            logger.error(f'error to get response,error = {str(e)}\n{traceback.format_exc()}')
            return []

    async def get_stream_response(self,messages:List[Message],session_id:str) -> AsyncGenerator[str,None]:
        # get a stream response from LLM
        config = {
            "configurable": {"thread_id": str(session_id)},
            "callbacks": [],
            "metadata": {
                "session_id": str(session_id),
            },
        }
        if self._graph is None:
            self._graph = await self.create_graph()
        try:
            state = await self._graph.aget_state(config)
            
            session_memory = await self._get_session_memory(str(session_id), messages[-1].content) or 'No relevant memory found'
            if  state and state.next:
                logger.info('resuming interupted graph stream')
                graph_input = Command(resume=messages[-1].content)
            else:
                graph_input =  {"messages": dump_messages(messages), "session_memory": session_memory}
                logger.debug(f'graph_input = {graph_input}')

             
            async for token,_ in self._graph.astream(
                input = graph_input,
                config=config,
                stream_mode='messages'
            ):
                if isinstance(token.content,str) and token.content:
                    yield token.content
            # After streaming completes, check for interrupt or update memory
            state = await self._graph.aget_state(config)
            if state.next:  
                interrupt_value = state.tasks[0].interrupts[0].value if state.tasks else "Waiting for input."
                logger.info("graph_interrupted", session_id=str(session_id), interrupt_value=str(interrupt_value))
                yield str(interrupt_value)

            elif state.values and 'messages' in state.values:
                # update memory for the current session
                await self._sync_message_memories(
                    str(session_id),
                    state.values['messages'],
                    config,
                )
            
        except GraphInterrupt:
            interrupt_value = state.tasks[0].interrupts[0].value if state.tasks else "Waiting for input."
            logger.info("graph_interrupted_stream", session_id=str(session_id), interrupt_value=str(interrupt_value))
            yield str(interrupt_value)
        except Exception as stream_error:
            logger.exception("stream_processing_failed", error=str(stream_error), session_id=str(session_id))
            raise stream_error  
    
    async def get_chat_history(self,session_id:str) ->List[Message]:
        # get the chat history for a given id

        if self._graph is None:
            self._graph = await self.create_graph()
        config={"configurable": {"thread_id": session_id}}
        state:StateSnapshot = await self._graph.aget_state(
            config=config
        )
        return await self.__process_messages(state.values['messages']) if state.values and 'messages' in state.values else []
    
    async def __process_messages(self,messages:List[Message]) -> List[Message]:
        try:
            result = []
            for item in messages:
                role = self._message_role(item)
                content = self._message_content(item)
                message_id = item.get("id") if isinstance(item, dict) else getattr(item, "id", None)

                if role == "tool":
                    continue

                if role in ["assistant", "user", "system"] and content:
                    result.append(Message(role=role, content=content, id=str(message_id) if message_id else None))

            return result
        except Exception as e:
            logger.error(f'Error in __process_messages: {str(e)}')
            # Fallback: process individual messages
            result = []
            for msg in messages:
                try:
                    role = self._message_role(msg)
                    content = self._message_content(msg)
                    message_id = msg.get("id") if isinstance(msg, dict) else getattr(msg, "id", None)
                    if role in ["assistant", "user", "system"] and content:
                        result.append(Message(role=role, content=content, id=str(message_id) if message_id else None))
                except Exception as msg_error:
                    logger.warning(f'Skipping message due to error: {msg_error}')
                    continue
            return result

    async def delete_message(self, session_id: str, message_id: str) -> None:
        # delete a single message and any memories linked to it
        if self._graph is None:
            self._graph = await self.create_graph()

        config = {"configurable": {"thread_id": str(session_id)}}
        state:StateSnapshot = await self._graph.aget_state(config=config)

        if not state.values or 'messages' not in state.values:
            raise ValueError("message not found")

        raw_messages = state.values['messages']
        target_message = next(
            (
                message
                for message in raw_messages
                if isinstance(message, BaseMessage) and str(getattr(message, "id", "")) == str(message_id)
            ),
            None,
        )

        if target_message is None:
            raise ValueError("message not found")

        memory_ids = self._extract_memory_ids(target_message)
        if memory_ids:
            await self.memory_service.delete_memories(memory_ids)

        await self._graph.aupdate_state(
            config,
            {"messages": [RemoveMessage(id=str(message_id))]},
            as_node="chat",
        )
    
    async def clear_history(self,session_id:str) -> None:
        # clear all history that correspond the session id
        try: 
            engine: AsyncConnectionPool = await self._get_connection_pool()

            if not engine:
                raise Exception("No DB engine")

            async with engine.connection() as conn:
                    try:
                        table = CHCKPT_TABLE
                        result = await conn.execute(
                                    f"DELETE FROM {CHCKPT_TABLE} WHERE thread_id = %s",
                                    (str(session_id),)
                        )

                        if result.rowcount > 0:
                            logger.info(f"{table}: deleted  rows")
                        else:
                            logger.warning(f"{table}: no rows `found`")

                    except Exception as e:
                        logger.error(f"{table}: delete failed, error={e}")
                        raise 

            await self.clear_memory(session_id)

        except Exception as e:
            logger.error(f"failed_to_clear_chat_history, error={str(e)}")
            raise

    async def clear_memory(self, session_id: str) -> None:
        # clear memory only and keep checkpoint history intact
        try:
            await self.memory_service.clear_memory(session_id)
        except Exception as e:
            logger.error(f"failed_to_clear_session_memory, error={str(e)}")
            raise

    async def _get_connection_pool(self) -> AsyncConnectionPool:
        if self._connection_pool is None:
            try:
                # Configure pool size based on environment
                max_size = 10

                connection_url = DATABASE_URL

                self._connection_pool = AsyncConnectionPool(
                    connection_url,
                    open=False,
                    max_size=max_size,
                    kwargs={
                        "autocommit": True,
                        "connect_timeout": 5,
                        "prepare_threshold": None,
                    },
                )
                await self._connection_pool.open()
                logger.info(f"connection_pool_created,max_size={max_size}")
            except Exception as e:
                logger.error(f"connection_pool_creation_failed,error = {str(e)}")
                # In production, we might want to degrade gracefully
                raise e
        return self._connection_pool
