import datetime
import uuid
from fastapi import HTTPException,status

from fastapi.params import Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import create_engine,Column,Integer,String,DateTime,ForeignKey,select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel, EmailStr, field_validator, validators
#使用UUID
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import re
#密码加密
from passlib.context import CryptContext
from sqlalchemy.sql.functions import user
from jose import jwt,JWTError
from database.database import get_db

#数据表模型基类
BASE = declarative_base()
#JWT相关
SECRET_KEY = ''
ALGORITHM = 'HS256'


#密码加密
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
def get_password_hash(password:str):
    return pwd_context.hash(password)

#验证用户名和密码
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

#JWT token 生成
def create_access_token(data: dict):
    to_encode = data.copy()
    expire_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))) + datetime.timedelta(minutes=15)
    to_encode.update({"exp": expire_time})
    encoded_jwt = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return encoded_jwt

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
    created_at = Column(DateTime,default=datetime.datetime.now)

#用户登录时候的验证模型
class UserLoginModel(BaseModel):
    username:str
    password:str
    @field_validator('username',mode='before')
    def validate_username(cls, v:str):
        if len(user.strip()) == 0:
            return {'msg':"无效的用户名或者密码"}
        return None


#用户创建时使用Pydantic进行数据验证
class UserModel(BaseModel):
    username:str
    password:str
    email:EmailStr

    #用户名必须由6-10位英文组成，只能是英文字母
    @field_validator("username",mode='before')
    def validate_username(cls, v:str):
        if len(v.strip()) <6 or len(v.strip()) > 10:
            return {'msg':'无效的用户名,用户名必须由6-10为大小写字母和数字组成'}
        if not re.match(r"^[a-zA-Z0-9]{6,10}$", v):
            return {'msg':"无效的用户名,用户名必须由6-10为大小写字母和数字组成"}
        return None

    @field_validator('password',mode='before')
    def validate_password(cls, v:str):
        if not v:
            return {'msg':'密码不能为空'}
        return None


#创建用户
async def create_user(user:UserModel,db:AsyncSession = Depends(get_db())):
    #查重
    exists = await db.execute(select(UserDB).filter(UserDB.username==user.username))
    if exists.scalar():
        return {"msg":"用户名已存在"}
    hashed_password = get_password_hash(user.password)
    db_user = UserModel(
        username=user.username,
        password=hashed_password,
        email=user.email,
    )
    #添加用户表
    db.add(db_user)
    #提交事务
    await db.commit()
    #刷新数据库
    await db.refresh(db_user)
    return {"msg":"注册成功",'username':user.username}

#用户登录
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(),db:AsyncSession = Depends(get_db())):
    #查询用户
    result = await db.execute(select(UserDB).filter(UserDB.username==form_data.username))
    user = result.scalar_one_or_none()
    #校验用户密码
    if not user or not verify_password(form_data.password,user.password):
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail='用户名或者密码错误'
        )

    access_token =create_access_token(data={"sub":user.username})
    return {"access_token":access_token,"token_type":"bearer"}


