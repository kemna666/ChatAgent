import datetime
from wsgiref.validate import validator
from pydantic import BaseModel, ValidationError
from sqlalchemy import Column,Integer,String,DateTime,ForeignKey,UniqueConstraint
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.sql.functions import user

Base = declarative_base()

class ChatMessages(BaseModel):
    sender: str
    content:str

    @validator('content')
    def content(cls, v):
        if len(v.strip()) == 0:
            raise ValidationError('Content cannot be empty')

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