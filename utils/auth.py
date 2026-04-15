from datetime import timedelta,datetime,timezone
from typing import Optional
from jose import jwt,JWTError
from loguru import logger
import re
from schemas.userschema import Token
from utils.sanitization import sanitize_string

JWT_SECRET_KEY = ''
JWT_ALGORITHM = "HS256"

def verify_token(token:str) -> Optional[str]:
    #verify token and return JWT ID
    if not token or not isinstance(token,str):
        logger.warning('token is invaild')
        raise ValueError('token must be uempty string')
    if not re.match(r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$", token):
        logger.warning('invaild token format')
        raise ValueError('token must be JWT format')
    
    try:
        payload = jwt.decode(token,JWT_SECRET_KEY,JWT_ALGORITHM)
        thread_id:str = payload.get('sub')
        if thread_id is None:
            logger.warning('token missing thread ID')
            return None
        
        logger.info('token verified',thread_id=thread_id)
        return thread_id
    except JWTError as e:
        logger.error(f'token verification failed,error = {str(e)}')
        return None
    
def create_access_token(thread_id:str,expires_delta:Optional[timedelta] = timedelta(hours=10)) -> Token:
    #create a new access token for a thread
    expire = datetime.now(timezone(timedelta(hours=8))) + expires_delta
    to_encode = {
        'sub':thread_id,
        'exp':expire,
        'iat':datetime.now(timezone(timedelta(hours=8))),
        'jti':sanitize_string(f'{thread_id}-{datetime.now(timezone(timedelta(hours = 8)))}')
    }

    encoded_jwt = jwt.encode(to_encode,JWT_SECRET_KEY,JWT_ALGORITHM)
    logger.info(f'token created,thread_id = {thread_id},expired_at = {expire.isoformat()}')

    return Token(access_token=encoded_jwt,expires_at=expire)
