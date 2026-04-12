from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import FastAPI
from fastapi.params import Depends
from sqlalchemy import desc, select
from models.usermodel import UserDB
from models.chatmodel import ChatMessageDB
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import create_tables, get_db
from schemas.chatschema import ChatMessage
from schemas.userschema import UserModel
from services.userservice import create_user, get_current_user, login_user


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

@app.post("/chat_commit",summary="发送聊天消息")
async def chat_commit(
    message:ChatMessage,
    current_user:UserDB=Depends(get_current_user),
    db:AsyncSession = Depends(get_db)
):
    db_msg = ChatMessageDB(
        sender_id =  current_user.id,
        sender = current_user.username,
        content = message.content,
        receiver_id = message.recevier_id,
    )
    db.add(db_msg)

    await db.commit()
    await db.refresh(db_msg)
    return db_msg
    
@app.post('/messages',summary="获取所有聊天消息")
async def getMessages(
    current_user:UserDB = Depends(get_current_user),
    db:AsyncSession = Depends(get_db)
    ):
    results = await db.execute(
        select(ChatMessageDB)
        .fliter(ChatMessageDB.sender_id == current_user.id)
        .order_by(desc(ChatMessageDB.create_time))
    )
    messages = results.scalars().all()
    return {
        'username':current_user.username,
        'num_messages':len(messages),
        'messages':[{
            'id':msg.id,
            'sender':msg.sender,
            "content":msg.content,
            "create_time":msg.create_time,
            "recevier":msg.receiver
        }for msg in messages
        ]
    }