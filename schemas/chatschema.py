

from pydantic import BaseModel, ValidationError, field_validator


class ChatMessages(BaseModel):
    sender: str
    content:str

    @field_validator('content')
    def content(cls, v):
        if len(v.strip()) == 0:
            raise ValueError('Content cannot be empty')
        return v