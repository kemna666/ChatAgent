from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import FastAPI
from fastapi.params import Depends
from models.usermodel import UserDB
from models.chatmodel import ChatMessagesDB
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import create_tables, get_db
from schemas.userschema import UserModel
from services.userservice import create_user, login_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    #在应用启动时创建数据库表
    await create_tables()
    yield
    #在应用关闭时执行清理操作（如果需要）
    print("应用正在关闭...")




app = FastAPI(lifespan=lifespan)

#注册用户
@app.post("/register",summary="注册接口")
async def register_user(user: UserModel,db: AsyncSession = Depends(get_db)):
    return await create_user(user,db)

@app.post("/login",summary="登录接口")
async def login(
    user: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db)
):
    return await login_user(user, db)
