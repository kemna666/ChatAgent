from sqlalchemy.orm import Session

from models.chatmodel import ChatMessagesDB
from schemas.chatschema import ChatMessages
from langchain.chat_models import OpenAI

def save_chat(message:ChatMessages,db:Session):
    db_msg = ChatMessagesDB(
        sender=message.sender,
        content=message.content
    )

    db.add(db_msg)

    db.commit()
    db.refresh(db_msg)
    return db_msg
