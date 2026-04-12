from datetime import datetime
import re
from pydantic import BaseModel,EmailStr,Field,field_validator,SecretStr
from uuid import UUID


class UserCreate(BaseModel):
    username:str = Field(...,description='the nickname of a user')
    email:EmailStr = Field(...,description='User email addr')
    passwd:SecretStr = Field(...,description="User's password")

    @field_validator('passwd')
    def validate_passwd(cls,v:SecretStr):
        passwd = v.get_secret_value()

        if len(passwd)<10:
            raise ValueError('密码不能小于10位')
        if not (re.search(r'[A-Z]',passwd) or re.search(r'[a-z]',passwd) or re.search(r'[0-9]',passwd)):
            raise ValueError('密码必须由大小写+数字三者组成！')
        return v
    
class Token(BaseModel):
    access_token:str = Field(...,description='JWT access token')
    token_type:str = Field(default='bearer',description='token type')
    expires_at:datetime = Field(...,description='when token expires')


class UserResponse(BaseModel):
    id:UUID = Field(...,description='user id')
    email:str = Field(...,description='user email')
    token:str = Field(...,description='auth token')


class SessionResponse(BaseModel):

    session_id:UUID = Field(...,description='the id of session')

    name:str = Field(...,description='the name of session')

    token:str = Field(...,description='the token for session')