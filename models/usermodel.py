from datetime import datetime,timezone,timedelta
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String,DateTime
from sqlalchemy.orm import relationship
from .session import Base
import bcrypt
import uuid

#this is the table of users
class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True),primary_key=True,index=True,default=lambda:uuid.uuid4())
    email = Column(String,unique=True,nullable=False)
    username = Column(String,nullable=False)
    hashed_passwd = Column(String,nullable=False)
    created_at = Column(DateTime(timezone=True),default=lambda:datetime.now(timezone(timedelta(hours=8))))
    sessions = relationship("Session",back_populates="user")

    def verify_passwd(self, passwd: str) -> bool:
        return bcrypt.checkpw(passwd.encode('utf-8'), self.hashed_passwd.encode('utf-8'))

    @staticmethod
    def hash_passwd(passwd:str) -> str:
        # generate hash
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(passwd.encode('utf-8'),salt).decode('utf-8')

#avoid circular imports eerror
from .session import Session