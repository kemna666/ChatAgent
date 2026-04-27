# This is a memory management service
import inspect
from typing import List, Optional, Union
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
                            "dbname": 'chat_db',
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
                            "model": "BAAI/bge-large-zh-v1.5",  # 必须用嵌入模型
                            "api_key": self._api_key,
                            "openai_base_url": self._base_url
                        }
                    },
                }
            self._memory = AsyncMemory.from_config(config_dict)
        return self._memory
    
    def _scope_id(self, session_id: Union[str, UUID]) -> str:
        return str(session_id)

    async def add_memory(self,session_id:Union[str, UUID],message:List[dict],metadata:dict =None,infer:bool = False) -> List[str]:
        # add memory scoped to the current session and return created memory ids
        try:
            memory:AsyncMemory = await self._get_memory()
            result = await memory.add(
                message,
                user_id=self._scope_id(session_id),
                metadata=metadata,
                infer=infer,
            )
            logger.info('memory update sucessfully')
            return [
                str(item.get("id"))
                for item in (result or {}).get("results", [])
                if item.get("id")
            ]
        except Exception as e:
            logger.exception(f"failed_to_update_session_memory,error={str(e)}")
            return []

    async def search(self,session_id:Union[str, UUID],query:str) -> str:
        # search memory only within the current session
        try:
            memory = await self._get_memory()
            results = await memory.search(
                user_id=self._scope_id(session_id),
                query=query,
                limit=8,
            )
            lines = []
            for result in results["results"]:
                memory_text = str(result.get("memory", "")).strip()
                if not memory_text:
                    continue
                role = str(result.get("role") or result.get("metadata", {}).get("role") or "").strip()
                prefix = f"[{role}] " if role else ""
                lines.append(f"* {prefix}{memory_text}")
            return '\n'.join(lines)
        except Exception as e:
            logger.error(f"failed_to_get_relevant_memory,error = {str(e)}")
            return ""

    async def delete_memories(self, memory_ids: List[str]) -> None:
        # delete a list of memories precisely by memory id
        if not memory_ids:
            return

        try:
            memory = await self._get_memory()
            for memory_id in {str(item) for item in memory_ids if item}:
                try:
                    await memory.delete(memory_id)
                except Exception as delete_error:
                    logger.warning(f"failed_to_delete_memory,error={str(delete_error)},memory_id={memory_id}")
            logger.info("deleted_session_memories,count={}", len({str(item) for item in memory_ids if item}))
        except Exception as e:
            logger.warning(f"failed_to_delete_memories,error={str(e)}")

    async def clear_memory(self, session_id: Union[str, UUID]) -> None:
        # best-effort cleanup for memory belonging to a single conversation
        try:
            memory = await self._get_memory()
            delete_all = getattr(memory, "delete_all", None)

            if not callable(delete_all):
                logger.warning("memory_backend_has_no_delete_all, session_id={}", self._scope_id(session_id))
                return

            try:
                result = delete_all(user_id=self._scope_id(session_id))
            except TypeError:
                result = delete_all(filters={"user_id": self._scope_id(session_id)})

            if inspect.isawaitable(result):
                await result

            logger.info("session_memory_cleared, session_id={}", self._scope_id(session_id))
        except Exception as e:
            logger.warning(f"failed_to_clear_session_memory,error={str(e)}")
        
        
memory_service = MemoryService()
