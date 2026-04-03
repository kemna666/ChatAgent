import re
from pydantic import BaseModel, EmailStr, field_validator

#用户登录时候的验证模型
class UserLoginModel(BaseModel):
    username:str
    password:str
    @field_validator('username',mode='before')
    def validate_username(cls, v:str):
        if len(v.strip()) == 0:
            raise ValueError("无效的用户名或者密码")
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
            raise ValueError('无效的用户名,用户名必须由6-10为大小写字母和数字组成')
        if not re.match(r"^[a-zA-Z0-9]{6,10}$", v):
            raise ValueError("无效的用户名,用户名必须由6-10为大小写字母和数字组成")
        return v

    @field_validator('password',mode='before')
    def validate_password(cls, v:str):
        if not v:
            raise ValueError('密码不能为空')
        return v