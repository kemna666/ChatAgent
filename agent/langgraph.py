import asyncio
from typing import AsyncGenerator, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from langchain_core.messages import BaseMessage, ToolMessage
from schemas.llm import GraphState
from utils.llm_process import dump_messages, handle_response, prepare_message
from services.LLMService import llmservice
from loguru import logger
from agent.tools.tools import tools
from mem0 import AsyncMemory
from langgraph.graph.state import CompiledStateGraph,Command, RunnableConfig
from sqlalchemy.dialects.postgresql import UUID
from schemas.llm import Message
from langchain_core.callbacks.manager import CallbackManager
from langchain_core.messages import convert_to_openai_messages
from langgraph.graph import StateGraph,END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver 
from services.memory import memory_service
from langgraph.errors import GraphInterrupt
from langgraph.types import StateSnapshot


DATABASE_URL =  ''
CHCKPT_TABLE = ''


class LangGraphAgent:


    def __init__(self):
        # initialize llm service
        self.llm_service = llmservice
        # bind tools
        self.llm_service.bind_tools(tools)
        self._async_enfine:Optional[AsyncEngine] = None
        self._graph:Optional[CompiledStateGraph] = None
        self.memory:Optional[AsyncMemory] = None
        self.tools_by_name = {tool.name: tool for tool in tools}
        logger.info('agent has been initialized')

    async def _get_async_engine(self) -> Optional[AsyncEngine]:
        if self._async_enfine is None:
            try:
                # postgresql+asyncpg://user:pass@host:port/db
              
                self._engine = create_async_engine(
                    DATABASE_URL,
                    pool_pre_ping=True,  # 自动检测失效连接
                    echo=False           # 生产环境关闭SQL日志
                )
            except Exception:
                return None # 连接失败返回None
        return self._engine
    async def _long_term_memory(self) -> AsyncMemory:
        #initialize long term memory
        if self.memory is None:
            self.memory = await AsyncMemory.from_config(
                          config_dict={
                    "vector_store": {
                        "provider": "pgvector",
                        "config": {
                            "collection_name": '',
                            "dbname": 'memories',
                            "user": 'postgres',
                            "password": '123456',
                            "host": 'localhost',
                            "port": '5432',
                        },
                    },
                    "llm": {
                        "provider": "openai",
                        "config": {"model": ''},
                    },
                    "embedder": {"provider": "openai", "config": {"model": ''}},
                    # "custom_fact_extraction_prompt": load_custom_fact_extraction_prompt(),
                }
            )
        return self.memory
    
    async def _get_memory(self,user_id:UUID,query:str) ->str:
        # get relevant memory about th query for user
        try:
            memory = await self._long_term_memory()
            results = await memory.search(user_id= str(user_id),query=query)

            return '\n'.join(f"{result[memory]}"for result in results)
        
        except Exception as e:
            logger.error(f'failed to get memory,error = {str(e)}')
            return ''
    
    async def _update_long_term_memory(self,user_id:UUID,messages:List[dict],metadata:dict) -> None:
        # update memory through user's messages
        try:
            self.memory = await self._long_term_memory()
            await self.memory.add(messages=messages,user_id=str(user_id),metadata=metadata)
            logger.info('memory updated successfully')

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
        SYSTEM_PROMPT = ''
        # handle messages in advance
        messages = prepare_message()

        try:
            # use llm with auto retries and circular fdllback
            # 
            # process response
            response_message = handle_response(response_message)

            logger.info(
                'llm response generated'
            ) 
            if response_message.tool_calls:
                goto = 'tool_call'
            else:
                goto = 'end'

            return Command(update = {'messages':[response_message]},goto = goto)
        
        except Exception as e:
            logger.error(
                f'llm failed all models,error = {str(e)}'
            )
            raise Exception(f'failed to get response')
          
    async def _call_tool(self,state:GraphState) -> Command:
        #process tool calling
        outputs:List[ToolMessage] = []
        for tool in state.messages[-1].tool_calls:
            # ASYNC INVOKE TOOL
            tool_result = await self.tools_by_name[tool['name'].ainvoke(tool['args'])]
            outputs.append(
                ToolMessage(
                    content= tool_result,
                    name = tool['name'],
                    tool_call_id = tool['id']
                )
            )
        return Command(update={'messages':outputs},goto = 'chat')
    
    async def create_graph(self) -> Optional[CompiledStateGraph]:
        # create langchain workflow
        if self._graph is None:
            try:
                # create a graph whose nodes communicate by reading and writing to a shared state.
                graph_builder = StateGraph(GraphState)
                # add a chat node that can go to the end of calling tools or  
                graph_builder.add_node('chat',self._chat,ends = ['tool_call',END])
                graph_builder.add_node('tool_call',self._call_tool,ends = ['chat'])
                # set entry and finish node 
                graph_builder.set_entry_point('chat')
                graph_builder.set_finish_point('chat')
                # get the connection pool of sqlalchemy
                async_engine:AsyncEngine = await self._get_async_engine()
                checkpointer = None
                if async_engine:
                    checkpointer = AsyncPostgresSaver(async_engine)
                    await checkpointer.setup()
                else:
                    raise Exception('connection initialization failed')
                self._graph = graph_builder.compile(
                    checkpointer = checkpointer,
                    name = f'Agent'
                )
                logger.info('graph created')
            
            except Exception as e:
                logger.error(f"graph_creation_failed,error = {str(e)}")
                raise e

    async def get_response(self,message:List[Message],session_id:str,thread_id:str,user_id:Optional[UUID]=None) -> List[dict]:
        # get response from llm

          config = {
            "configurable": {"thread_id": session_id},
            "callbacks": [CallbackManager()],
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "environment": '',
                "debug": '',
            },
        }
          relavent_memory = (
              await self._get_memory(user_id,message[-1].content)
          ) or 'No relevant memory found'

          try:
              
              response = await self._graph.ainvoke(
                  input = {'messages':dump_messages(message),'memory':relavent_memory},
                  config=config
              )
              asyncio.create_task(
                  self._update_long_term_memory(
                      user_id,
                      convert_to_openai_messages(response['messages']),
                      config['metadata']
                  )
              )
              return self.__process_messages(response['messages'])
          except Exception as e:
              logger.error(f'error to get response,error = {str(e)}')

    async def get_stream_response(self,messages:List[Message],session_id:UUID,user_id:Optional[str] = None) -> AsyncGenerator[str,None]:
        # get a stream response from LLM
        config = {
            "configurable": {"thread_id": str(session_id)},
            #"callbacks": [langfuse_callback_handler],
            "metadata": {
                "user_id": str(user_id),
                "session_id": str(session_id),
            },
        }

        if self._graph is None:
            self.create_graph()

        try:
            state = await self._graph.aget_state(config)
            if state.next:
                logger.info('resuming interupted graph stream')
                graph_input = Command(resume=messages[-1].content)
            else:
                relavent_memory = (
                    await memory_service.search(user_id,messages[-1].content)
                ) or 'No relavent memory found'
                graph_input={'messages':dump_messages(messages),'memory': relavent_memory},
            
            async for token,_ in self._graph.astream(
                input = graph_input,
                config=config,
                stream_mode='messages'
            ):
                if isinstance(token.content,str) and token.content:
                    yield token.content
            
            state = await self._graph.aget_state(config)
            if state.next:  
                interrupt_value = state.tasks[0].interrupts[0].value if state.tasks else "Waiting for input."
                logger.info("graph_interrupted", session_id=str(session_id), interrupt_value=str(interrupt_value))
                yield str(interrupt_value)

            elif state.values and 'message' in state.values:
                # add memory for user 
                asyncio.create_task(
                    memory_service.add_memory(user_id,convert_to_openai_messages(state.values['messages']),config['metadata'])
                )
            
        except GraphInterrupt:
            state = await self._graph.aget_state(config)
            interrupt_value = state.tasks[0].interrupts[0].value if state.tasks else "Waiting for input."
            logger.info("graph_interrupted_stream", session_id=str(session_id), interrupt_value=str(interrupt_value))
            yield str(interrupt_value)
        except Exception as stream_error:
            logger.exception("stream_processing_failed", error=str(stream_error), session_id=str(session_id))
            raise stream_error  
    
    async def get_chat_history(self,session_id:UUID) ->List[Message]:
        # get the chat history for a given id

        if self._graph is None:
            self._graph = await self.create_graph()
        
        state:StateSnapshot = await self._graph.aget_state(
            config={"configurable": {"thread_id": str(session_id)}}
        )

        return self.__process_messages(state.valuess['messages']) if state.values else []
    
    async def __process_messages(self,messages:List[BaseMessage]) -> List[Message]:

        openai_style_messages = convert_to_openai_messages(messages)

        return [
            Message(role=message["role"], content=str(message["content"]))
            for message in openai_style_messages
            if message["role"] in ["assistant", "user"] and message["content"]
        ]
    
    async def clear_history(self,session_id:UUID) -> None:
        # clear all history that correspond the session id
        try: 
            engine:AsyncEngine = await self._get_async_engine()

            if not engine:
                raise Exception()
            
            async with engine.begin() as conn:
                for table in CHCKPT_TABLE:
                    try:
                        await conn.execute(
                        text(f"DELETE FROM {table} WHERE thread_id = :session_id"),
                        {"session_id": str(session_id)}
                        )
                        logger.info('deleted chat history successfully')
                    
                    except Exception as e:
                        logger.error(f'failed to delete chat history ,error = {str(e)}')

        except Exception as e:
            logger.error(f"failed_to_clear_chat_history, error=str(e)")
            raise