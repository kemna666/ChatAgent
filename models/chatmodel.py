import datetime
from wsgiref.validate import validator
from pydantic import BaseModel, ValidationError
from sqlalchemy import Column,Integer,String,DateTime,ForeignKey,UniqueConstraint
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.sql.functions import user
from database.database import Base
from schemas.chatschema import ChatMessages



class ChatMessagesDB(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    sender = Column(String(10))
    create_time = Column(DateTime,default=datetime.datetime.now)
    content = Column(String(102400))

def save_chat(message:ChatMessages,db:Session):
    db_msg = ChatMessagesDB(
        sender=message.sender,
        content=message.content
    )

    db.add(db_msg)

    db.commit()
    db.refresh(db_msg)
    return db_msg