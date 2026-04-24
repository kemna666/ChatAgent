


import json
from typing import Optional
from loguru import logger
from redis import asyncio as aioredis
from sqlalchemy.dialects.postgresql import UUID
from models.session import Base, Session as ChatSession
from models.usermodel import User
from services.databaseservice import DataBaseService,database_service


# this is a class that used to connect to redis
class RedisClient:
    _instance:Optional[aioredis.Redis] = None
    @classmethod
    async def get_client(cls):
        try:
            redis_url = 'redis://localhost:6379'
            cls._instance = aioredis.from_url(
                redis_url,
                encoding = 'utf-8',
                decode_responses = False,
                socket_timeout = 5,
                socket_connect_timeout=10,
                max_connections = 20
            )
            await cls._instance.ping()
            logger.success('redis created')
        except Exception as e:
            logger.error(f'radis client failed,err = {str(e)}')
        return cls._instance    

    @classmethod    
    async def close(cls):
        if cls._instance:
            await cls._instance.close()
            logger.info('redis connection closed')
    

redis_client = RedisClient()


class CacheDBService:

    def __init__(self):
        self.db:DataBaseService = database_service
        self.redis:Optional[aioredis.Redis] = None
        self.ttl = 10


    async def get_redis_client(self):
        self.redis = await redis_client.get_client()
        logger.success('successfully get redis session')

    def _serialize(self,obj):
        data = obj.__dict__.copy()
        data.pop("_sa_instance_state", None)
        if not object:
            return None
        return json.dumps(
            data,
            default= lambda x:str(x) if isinstance(x,UUID) else str(x)
        )
    
    def _deserialize(self,data,model_cls):

        if not data:
            return None
        try:
            return model_cls(**json.loads(data))
        except Exception as e:
            logger.error(f'deserialize failed,err = {str(e)}')
    
    async def get_user(self, user_id: UUID) -> Optional[User]:
        key = f"user:id:{user_id}"
        data = await self.redis.get(key)
        if data:
            return self._deserialize(data, User)
        
        user = await self.db.get_user(user_id)
        ttl = 100 if user else 0
        await self.redis.setex(key, ttl, self._serialize(user))
        return user

    async def get_user_by_email(self,email:str) -> Optional[User]:
        
        key = f"user:email:{email}"
        cached = await self.redis.get(key)

        if cached:
            return self._deserialize(cached,User)
        
        user = await self.db.get_user_by_email(email)

        ttl = self.ttl
        await self.redis.setex(key,ttl,self._serialize(user))

        return user
    
    async def create_user(self,email:str,username:str,passwd:str) -> User:
        user_cache_ttl = 100

        user = await self.db.create_user(email,username,passwd)
        await self.redis.setex(f"user:id:{user.id}",user_cache_ttl,self._serialize(user))
        await self.redis.setex(f"user:email:{user.email}",user_cache_ttl,self._serialize(user))
        return user
    
    async def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        key = f"session:{session_id}"
        data = await self.redis.get(key)
        if data:
            return self._deserialize(data, ChatSession)
        
        session = await self.db.get_session(session_id)
        ttl = self.ttl if session else 1
        await self.redis.setex(key, ttl, self._serialize(session))
        return session

    async def get_chat_sessions(self, user_id: UUID) -> List[ChatSession]:
        key = f"sessions:user:{user_id}"
        data = await self.redis.get(key)
        if data:
            return [self._deserialize(s, ChatSession) for s in json.loads(data)]
        
        sessions = await self.db.get_chat_sessions(user_id)
        serialized = json.dumps([self._serialize(s) for s in sessions])
        await self.redis.setex(key, self.ttl, serialized)
        return sessions

    async def create_session(self,user_id:UUID,session_name:str):
        session = await self.db.create_session(user_id, session_name)
        await self.redis.delete(f"sessions:user:{user_id}")
        return session
    
    async def update_session_name(self, session_id: UUID, name: str) -> ChatSession:
        session = await self.db.update_session_name(session_id, name)
        # 更新 → 清理单会话+用户列表缓存
        await self.redis.delete(f"session:id:{session_id}", f"sessions:user:{session.user_id}")
        return session
    
    async def delete_session(self, session_id: UUID) -> bool:
        session = await self.db.get_session(session_id)
        if not session:
            return False
        ok = await self.db.delete_session(session_id)
        if ok:
            await self.redis.delete(f"session:id:{session_id}", f"sessions:user:{session.user_id}")
        return ok
    
cache_service =  CacheDBService()