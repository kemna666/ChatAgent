import asyncio
import json
import traceback
from typing import AsyncGenerator, List, Optional
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import AsyncEngine
from langchain_core.messages import ToolMessage
from schemas.llm import GraphState
from utils.llm_process import dump_messages, handle_response, prepare_message
from services.LLMService import llmservice
from loguru import logger
from agent.tools.tools import tools
from mem0 import AsyncMemory
from langgraph.graph.state import CompiledStateGraph,Command, RunnableConfig
from sqlalchemy.dialects.postgresql import UUID
from schemas.llm import Message
from langchain_core.messages import convert_to_openai_messages
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
    
    async def _get_memory(self,user_id:UUID,query:str) ->str:
        # get relevant memory about th query for user
        try:
            # if memory is not initialized , initialize it
            return await self.memory_service.search(user_id=user_id,query=query)
        except Exception as e:
            logger.error(f'failed to get memory,error = {str(e)}')
            return ''
    
    async def _update_long_term_memory(self,user_id:UUID,messages:List[dict],metadata:dict) -> None:
        # update memory through user's messages
        try:
            await self.memory_service.add_memory(user_id=user_id,message=messages,metadata=metadata)
        except Exception as e:
            logger.exception(
                f'failed to update memory',user_id,error=str(e)
            )
    
    async def _chat(self,state:GraphState,config:RunnableConfig) -> Command:
        #process message and generate a response

        #get the llm 
        current_llm = self.llm_service.get_llm()

        # get llm info

        # load system prompts
        SYSTEM_PROMPT = '你是一个猫娘助手，喵喵喵～，能调用工具的情况下尽量调用已有工具实现问题'
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
    
    async def get_response(self,message:List[Message],session_id:str,user_id:Optional[UUID]=None) -> List[Message]:
        # get response from llm
          if self._graph is None:
              await self.create_graph()
          config = {
            "configurable": {"thread_id": session_id},
            "callbacks": [],
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "environment": '',
                "debug": '',
            },
        }
          logger.debug(f'config = {config}')
          relavent_memory = (
              await self._get_memory(user_id,message[-1].content)
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
                        input={"messages": dump_messages(message), "long_term_memory": relavent_memory},
                        config=config,
                    )
              logger.debug('remembering')
              asyncio.create_task(
                  self._update_long_term_memory(
                      user_id,
                      convert_to_openai_messages(response['messages']),
                      config['metadata']
                  )
              )
              r = await self.__process_messages(response['messages'])
              assistant_message = [msg for msg in r if msg.role == 'assistant']
              if assistant_message:
                  return [assistant_message[-1]]
              else:
                  logger.warning(f'no assistant message found in response')
                  return []
          except Exception as e:
              logger.error(f'error to get response,error = {str(e)}\n{traceback.format_exc()}')
              return []

    async def get_stream_response(self,messages:List[Message],session_id:UUID,user_id:Optional[str] = None) -> AsyncGenerator[str,None]:
        # get a stream response from LLM
        config = {
            "configurable": {"thread_id": str(session_id)},
            "callbacks": [],
            "metadata": {
                "user_id": str(user_id),
                "session_id": str(session_id),
            },
        }
        if self._graph is None:
                self._graph =await self.create_graph()
        try:
            state = await self._graph.aget_state(config)
            
            relevant_memory = await memory_service.search(user_id, messages[-1].content) or 'No relevant memory found'
            if  state and state.next:
                logger.info('resuming interupted graph stream')
                graph_input = Command(resume=messages[-1].content)
            else:
                relevant_memory = (
                    await memory_service.search(user_id,messages[-1].content)
                ) or 'No relevant memory found'
                graph_input =  {"messages": dump_messages(messages), "long_term_memory": relevant_memory}
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
                # add memory for user 
                asyncio.create_task(
                    memory_service.add_memory(user_id,convert_to_openai_messages(state.values['messages']),config['metadata'])
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
            # Convert LangChain messages to OpenAI-style format
            openai_style_messages = convert_to_openai_messages(messages)
            
            result = []
            for item in openai_style_messages:
                # if it is tool message jump it
                if (isinstance(item, dict) and item.get("role") == "tool") or (hasattr(item, "type") and getattr(item, "type", None) == "tool"):
                    continue
                # Check if item is a dictionary (expected format)
                if isinstance(item, dict) and "role" in item and "content" in item:
                    role = item["role"]
                    content = str(item["content"])
                # Otherwise, it might be a LangChain message object
                elif hasattr(item, 'type') and hasattr(item, 'content'):
                    # Map LangChain message type to our role
                    lc_type = getattr(item, 'type', '')
                    if lc_type == 'ai':
                        role = 'assistant'
                    elif lc_type == 'human':
                        role = 'user'
                    elif lc_type == 'system':
                        role = 'system'
                    else:
                        role = 'user'  # default
                    content = str(item.content)
                else:
                    # Skip items that don't match expected formats
                    continue
                
                # Only add messages with supported roles and non-empty content
                if role in ["assistant", "user", "system"] and content:
                    result.append(Message(role=role, content=content))
                
            return result
        except Exception as e:
            logger.error(f'Error in __process_messages: {str(e)}')
            # Fallback: process individual messages
            result = []
            for msg in messages:
                try:
                    # Extract role from LangChain message type
                    if hasattr(msg, 'type'):
                        lc_type = msg.type
                        if lc_type == 'ai':
                            role = 'assistant'
                        elif lc_type == 'human':
                            role = 'user'
                        elif lc_type == 'system':
                            role = 'system'
                        else:
                            role = 'user'  # default
                        content = str(msg.content)
                        if content:
                            result.append(Message(role=role, content=content))
                except Exception as msg_error:
                    logger.warning(f'Skipping message due to error: {msg_error}')
                    continue
            return result
    
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

        except Exception as e:
            logger.error(f"failed_to_clear_chat_history, error={str(e)}")
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
