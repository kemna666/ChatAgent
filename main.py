from logging import exception

import asyncio
from fastapi import FastAPI
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import async_sessionmaker,AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
from sqlalchemy.orm import declarative_base
from models.usermodel import UserModel, UserLoginModel, login_user
from models.usermodel import create_user
app = FastAPI()



#注册用户
@app.post("/register",summary="注册接口")
async def register_user(user: UserModel):
    new_user = create_user(user)

@app.post("/login")
async def login(user:OAuth2PasswordRequestForm = Depends()):
    return login_user(user)