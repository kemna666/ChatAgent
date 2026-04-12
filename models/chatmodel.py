from datetime import datetime,timezone,timedelta
from sqlalchemy import Column,Integer,String,DateTime,ForeignKey
from database.database import Base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

class ChatMessageDB(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    sender_id = Column(PGUUID(as_uuid=True),ForeignKey('users.id'),nullable=False)
    sender = relationship('User',foreign_keys=[sender_id])
    create_time = Column(DateTime,default=datetime.now(timezone(timedelta(hours=8))))
    content = Column(String(102400))
    recevier_id = Column(PGUUID(as_uuid=True),ForeignKey('users.id'),nullable=False)
    recevier = relationship('User',foreign_keys=[recevier_id])