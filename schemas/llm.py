from typing import Annotated, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator
from langgraph.graph.message import add_messages
import re

class GraphState(BaseModel):
    # the state definition of Langchain Agent

    messages:Annotated[list, add_messages] = Field(
        default_factory=list, description="The messages in the conversation"
    )

    session_memory:str = Field(default='',description='memory scoped to the current conversation')





class Message(BaseModel):
    # the message endpoint

    model_config = {
        'extra':'ignore'
    }

    role:Literal['user','assistant','system'] = Field(...,description='the role of the message sender')

    content:str

    id:Optional[str] = Field(default=None,description='message id used for state reconciliation')

    @field_validator('content')
    @classmethod
    def validate(cls, value:str) -> str:
        # vaildate the message content
        if re.search(r"<script.*?>.*?</script>", value, re.IGNORECASE | re.DOTALL):
             raise ValueError("Content contains potentially harmful script tags")
        if "\0" in value:
            raise ValueError("Content contains null bytes")
        return value

class ChatRequest(BaseModel):
    # request model for chat endpoint

    messages:List[Message] = Field(...,description='list of messages',min_length=1)

class ChatResponse(BaseModel):

    messages:list[Message] = Field(...,description='the response')

class StreamResponse(BaseModel):
    # response model for streaming chat endpoint

    content:str = Field(default= '',description='the content of current chunk')

    done:bool = Field(default=False,description='whether the stream is complete')

    message_id:Optional[str] = Field(default=None,description='assistant message id when available')
