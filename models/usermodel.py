import datetime
import uuid

from sqlalchemy import Column,String,DateTime
from sqlalchemy.orm import declarative_base
#使用UUID
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from database.database import Base as BASE

#数据表模型基类
#用户的数据库模型
class UserDB(BASE):
    __tablename__ = "users"
    #user ID使用UUID标识，作为主键且唯一
    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True,
    )
    username = Column(String(15),nullable=False)
    email = Column(String(255),nullable=False)
    password = Column(String(255),nullable=False)
    #创建时间
    created_at = Column(DateTime,default=datetime.datetime.now)
    #权限
    permission = Column(String(10),default='user')


