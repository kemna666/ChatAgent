from datetime import datetime,timezone,timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException,status
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from database.database import get_db
from models.usermodel import UserDB
from passlib.context import CryptContext
from jose import jwt

from schemas.userschema import UserModel


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
    expire_time = datetime.now(timezone(timedelta(hours=8))) + timedelta(minutes=15)
    to_encode.update({"exp": expire_time})
    encoded_jwt = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return encoded_jwt



#创建用户
async def create_user(user:UserModel,db:AsyncSession):
    #查重
    exists = await db.execute(select(UserDB).filter(UserDB.username==user.username))
    if exists.scalar():
        return {"msg":"用户名已存在"}
    hashed_password = get_password_hash(user.password)
    db_user = UserDB(
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
async def login_user(form_data: OAuth2PasswordRequestForm,db:AsyncSession):
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
