from pydantic import BaseModel, ValidationError, field_validator

class ChatMessage(BaseModel):
    content:str
    recevier_id:str

    @field_validator('content')
    def content(cls, v):
        if len(v.strip()) == 0:
            raise ValueError('Content cannot be empty')
        return v
    

class ChatMessageResponse(BaseModel):
    pass