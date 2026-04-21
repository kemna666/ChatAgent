# This is a memory management service
from typing import List, Optional
from sqlalchemy.dialects.postgresql import UUID
from loguru import logger
from mem0 import AsyncMemory
from config.config import config


class MemoryService:
    def __init__(self):
        self._memory:Optional[AsyncMemory] =None 
        self._base_url = config.llms['base_url']
        self._model = config.llms['default_model']
        self._api_key = config.llms['api_key']
    async def _get_memory(self) -> AsyncMemory:
        if self._memory is None:
            config_dict={
                    "vector_store": {
                        "provider": "pgvector",
                        "config": {
                            "collection_name": 'memories',
                            "dbname": 'memories',
                            "user": 'postgres',
                            "password": '123456',
                            "host": 'localhost',
                            "port": '5432',
                        },
                    },
                    "llm": {
                        "provider": "openai",
                        "config": {
                            "model": self._model,
                            "api_key": self._api_key,
                            "openai_base_url": self._base_url
                        }
                    },
                    "embedder": {
                        "provider": "openai",
                        "config": {
                            "model": "BAAI/bge-m3",  # 必须用嵌入模型
                            "api_key": self._api_key,
                            "openai_base_url": self._base_url
                        }
                    },
                }
            self._memory = AsyncMemory.from_config(config_dict)
        return self._memory
    
    async def add_memory(self,user_id:UUID,message:List[dict],metadata:dict =None):
        # add memory to database
        try:
            memory:AsyncMemory = await self._get_memory()
            await memory.add(message,user_id=str(user_id),metadata=metadata)
            logger.info('memory update sucessfully')
        except Exception as e:
            logger.exception(f"failed_to_update_long_term_memory,error={str(e)}")

    async def search(self,user_id:UUID,query:str) -> str:
        # search memory form database
        try:
            memory = await self._get_memory()
            results = await memory.search(user_id=str(user_id),query=query)
            return '\n'.join([f"* {r['memory']}" for r in results["results"]])
        except Exception as e:
            logger.error(f"failed_to_get_relevant_memory,error = {str(e)}")
            return ""
        
        
memory_service = MemoryService()