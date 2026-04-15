from typing import List

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials,HTTPBearer, OAuth2PasswordRequestForm
from uuid import UUID
from models.session import Session
from models.usermodel import User
from loguru import logger
from schemas.userschema import SessionResponse, Token, UserCreate, UserResponse
from services.databaseservice import DataBaseService
from utils.auth import create_access_token, verify_token
from utils.sanitization import sanitize_string


router = APIRouter()
security = HTTPBearer()
db_service = DataBaseService()


async def get_current_user(
        credentials:HTTPAuthorizationCredentials = Depends(security)
) -> User:
    #get current user id from token
    try:
        # sanitize string token
        token = sanitize_string(credentials.credentials)
        #verify token
        user_id = verify_token(token)
        if user_id is None:
            logger.error('invalid token')
            raise HTTPException(
                status_code=401,
                detail='invaild authentication credentials',
                headers={"WWW-Authenticate":"Bearer"}
            )
        user_id = UUID(user_id)
        user = await db_service.get_user(user_id)
        if user is None:
            logger.error('user not found')
            raise HTTPException(
                status_code=404,
                detail='user not found',
                headers={"WWW-Authenticate":"Bearer"}
            )
        return user
    except ValueError as ve:
        logger.error(f'token vaildation failed,error:{str(ve)}')
        raise HTTPException(
            status_code=401,
            detail='invaild token',
            headers={"WWW-Authenticate":"Bearer"}
        )
    except Exception as e:
        logger.error(f'token validation failed, error = {str(e)}')
        raise HTTPException(
            status_code=401,
            detail='invaild token',
            headers={"WWW-Authenticate":"Bearer"}
        )


async def get_current_session(session_id:str,credentials:HTTPAuthorizationCredentials = Depends(security)) -> Session:
    # get current session Id from token
    try:

        token = sanitize_string(credentials.credentials)

        user_id = verify_token(token)

        if session_id is None:
            logger.error('session id not found')
            raise HTTPException(
                status_code=401,
                detail='invaild session',
                headers={"WWW-Authenticate":"Bearer"}
            )
        user_id = UUID(user_id) 

        session = await db_service.get_session(session_id)
        if session is None:
            logger.error('session_not_found')
            raise HTTPException(
                status_code=404,
                detail='session not found',
                headers = {"WWW-Authenticate":"Bearer"}
            )
        if session.user_id != user_id:
            logger.error('session not belong to user')
            raise HTTPException(
                status_code=401,
                detail='session not belong to user',
                headers={"WWW-Authenticate":"Bearer"}
            )

        return session
    
    except ValueError as e:
        logger.error(f'token vaildation failed,error = {str(e)}')
        raise HTTPException(
            status_code=401,
            detail='invaild token',
            headers={"WWW-Authenticate":"Bearer"})
    except Exception as e:
        logger.error(f'token validation failed, error = {str(e)}')
        raise HTTPException(
            status_code=401,
            detail='invaild token',
            headers={"WWW-Authenticate":"Bearer"})
    
@router.post('/register',summary='register')
async def register_user(request:Request,user_data:UserCreate):
    # register a new user

    try:
        email = sanitize_string(user_data.email)
        passwd = user_data.passwd.get_secret_value()
        

        if await db_service.get_user_by_email(email):
            raise HTTPException(status_code=400,detail='you are already registered')
        
        user:User = await db_service.create_user(email=email,passwd=User.hash_passwd(passwd),username=user_data.username)

        token = create_access_token(str(user.id))

        return UserResponse(id = user.id,email=user.email,token = token)
    
    except ValueError as e:
        logger.error(f'user regiseration failed,error = {e}')
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )
    


@router.post('/login',summary='login')
async def login(
    form_data:OAuth2PasswordRequestForm = Depends()
    ):
    try:
        user = await db_service.get_user_by_email(form_data.username) 
        if user is None:
            raise HTTPException(
                    status_code=401,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        logger.info(f'{str(user.username)} logging')
        token = create_access_token(str(user.id))
        return Token(access_token=token.access_token,token_type='bearer',expires_at=token.expires_at)
    except ValueError as e:
        logger.error(f'login verfication failed,error = {str(e)}')
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )

@router.post('/session',summary='create a new session',response_model=SessionResponse)
async def create_session(
      session_name:str,
    user:User = Depends(get_current_user),
):
    # create a new chat session  
    try:
      session:Session = await db_service.create_session(user.id,session_name)

      token = create_access_token(str(session.session_id))

      logger.info('session created')

      return SessionResponse(
          session_id=session.session_id,
          name = session_name,
          token=token.access_token
      )
    except ValueError as ve:
        logger.error("session_creation_validation_failed", error=str(ve), user_id=user.id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
    
@router.patch('/session/{session_id}/name',response_model=SessionResponse,summary='update the name of session')
async def update_session_name(session_id:str,name:str = Form(...)):
    try:
        name = sanitize_string(name)
        current_session = await get_current_session()
        if session_id != current_session.session_id:
            raise HTTPException(status_code=403,detail='can not modify other session')
        
        session = await db_service.update_session_name(session_id,name)

        token = create_access_token(session)

        return SessionResponse(session.session_id,name,token)
    except ValueError as ve:
        logger.error('unable to update session name')
        raise HTTPException(status_code=422,detail=str(ve))
    

@router.delete('/session/{session_id}',summary='delete a session')
async def delete_session(session_id:str,user:User = Depends(get_current_user)):
    try:
        session_id = sanitize_string(session_id)
        current_session = await get_current_session(session_id=session_id)
        if current_session is None:
            raise HTTPException(status_code=404,detail='session not found')
        
        if current_session.user_id != user.id:
            raise HTTPException(status_code=403,detail='can not delete other sessions')
        
        await db_service.delete_session(session_id)

        logger.info('successful deleted a session')

    except ValueError as ve:

        logger.error(f'failed to delete session,because:{str(ve)}')
        raise HTTPException(
            status_code=422,detail=str(ve)
        )
        
@router.get('/sessions',summary='get sessions of current user',response_model=List[SessionResponse])
async def get_sessions(user:User = Depends(get_current_user)):

    try:
        sessions = await db_service.get_chat_sessions(user.id)

        return [
            SessionResponse(
                session_id= str(session.session_id),
                name= session.session_name,
                token= create_access_token(str(session.session_id)).access_token
            )
            for session in sessions
        ]
    except ValueError as ve:
        logger.error(f'failed to get sessions,because:{str(ve)}')
        raise HTTPException(
            status_code=422,detail=str(ve)
        )