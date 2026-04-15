import uuid
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime,timedelta,timezone
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, ForeignKey, String,DateTime
Base = declarative_base()

class Session(Base):
    __tablename__ = 'session'
    session_id:UUID = Column(UUID(as_uuid=True),default=lambda:uuid.uuid4(),primary_key=True)
    user_id =  Column(UUID(as_uuid=True),ForeignKey('users.id'),nullable=False)
    session_name = Column(String,default="")
    created_at = Column(DateTime(timezone=True),default=lambda:datetime.now(timezone(timedelta(hours=8))))
    user = relationship('User',back_populates='sessions')