import asyncio
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy import AsyncAdaptedQueuePool, Integer,String, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base
from loguru import logger
import tomllib
from models.usermodel import User
from models.session import Base, Session as ChatSession
from config.config import config





class DataBaseService:
    #the base class of database operations
    def __init__(self):
        #initialize the database
        try:
            pool_size = 10
            max_overflow = 10
            connection_url = config.chat_db
            self.engine = create_async_engine(
                url= connection_url,
                pool_size=pool_size,
                pool_pre_ping = True,
                max_overflow = max_overflow,
                # connection timeout
                pool_timeout=30,
                # retry connection after 30 minutes
                pool_recycle = 1800,
            )
            
        except SQLAlchemyError as e:
            logger.error(f'database initialization error!,error = {str(e)}')
            raise

    async def create_table(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    #create a new user
    async def create_user(self,email:str,username:str,passwd:str) -> User:
        async with AsyncSession(self.engine) as session:

            user = User(email=email,username = username,hashed_passwd = passwd)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f'user created,username:{username}')
            return user  
        
    async def get_user(self,userid:UUID) -> User:
        async with AsyncSession(self.engine) as  session:
            user = await session.get(User,userid)
            return user
    
    async def get_user_by_email(self,email:str):
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                select(User).where(User.email==email)
            )
            result = result.scalar_one_or_none()
            return result
    
    async def delete_user_by_email(self,email:str) -> bool:
        async with AsyncSession(self.engine) as session:

            result = await session.execute(
                select(User).where(User.email == email)
            )
            result.scalar_one_or_none()
            if not result:
                return False
            session.delete(result)
            await session.commit()
            logger.info(f'user is deleted,email:{email}')
            return True
    
    async def create_session(self,user_id:UUID,session_name:str) -> ChatSession:
        # create a chat session
        """
        Args:
        session_id : the id of a session
        user_id : who owns the session
        """
        async with AsyncSession(self.engine) as session:

            chat_session = ChatSession(user_id=user_id,session_name=session_name)
            sessionid = chat_session.session_id
            session.add(chat_session)
            await session.commit()
            await session.refresh(chat_session)
            logger.info(f'a new session created,session id:{sessionid}')
            return chat_session
        
    async def delete_session(self,session_id:UUID) -> bool:
        async with AsyncSession(self.engine) as session:
            chat_session = await session.get(ChatSession,session_id)
            if not chat_session:
                return False
            session.delete(chat_session)
            await session.commit()
            logger.info(f'session deleted,id:{session_id}')
            return True
        
    async def get_session(self,session_id:UUID) -> Optional[ChatSession]:
        # get a specific session by session id
        async with AsyncSession(self.engine) as session:
            chat_session = await session.get(ChatSession,session_id)
            return chat_session
    
    async def get_chat_sessions(self,user_id:UUID) -> List[ChatSession]:
        async with AsyncSession(self.engine) as session:
            chat_sessions = await session.execute(
                select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.created_at)
            )
            chat_sessions = chat_sessions.scalars().all()
            return chat_sessions
    
    async def update_session_name(self,session_id:UUID,name:str) -> ChatSession:
        async with AsyncSession(self.engine) as session:
            chat_session = await session.get(ChatSession,session_id)
            if not chat_session:
                raise HTTPException(
                    status_code=404,
                    detail='session not found'
                )
            chat_session.session_name = name
            session.add(chat_session)
            await session.commit()
            await session.refresh(chat_session)
            logger.info('successfully updated the session name')
            return chat_session
    
    async def check_health(self) -> bool:
        # check if database connection health
        try:
            async with AsyncSession(self.engine) as session:
                await session.execute(select(1))
                return True
        except Exception as e:
            logger.error(f'database health check failed,error = {str(e)}')
            return False


database_service = DataBaseService()