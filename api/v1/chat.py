import json
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Depends, HTTPException, Request
from langgraph.graph import MessagesState, StateGraph
from sqlalchemy import UUID
from agent.langgraph import LangGraphAgent
from api.v1.auth import get_current_session
from models.session import Session
from schemas.llm import ChatRequest, ChatResponse, StreamResponse
from loguru import logger

from utils.sanitization import sanitize_string

router = APIRouter()
agent = LangGraphAgent()

@router.post('/chat',response_model=ChatResponse)
async def chat(request:Request,chat_request:ChatRequest,session_id:str,current_user = Depends(get_current_session)) -> ChatResponse:

    # process a chat
    try:
        session_id = sanitize_string(session_id)
        logger.info(
            f'received a chat request,session id = {session_id},message count = {len(chat_request.messages)}'
        )

        result = await agent.get_response(chat_request.messages,session_id=session_id)
        
        return ChatResponse(messages=result)
    except Exception as e:
        logger.warning(f'chat request failed, error = {str(e)}')
        raise HTTPException(status_code=500,detail=str(e))
    

@router.post('/chat/stream',summary='process a chat request using langgraph with streaming response')
async def chat_stream(
    request:Request,
    chat_request:ChatRequest,
    session_id:str,
    current_session = Depends(get_current_session)
):
    session_id = sanitize_string(session_id)
    
    logger.info(f'stream chat request received,session id = {session_id}')
    
    return StreamingResponse(
        event_generator(chat_request=chat_request,session_id=session_id),     
        media_type = "text/event-stream"
    )


async def event_generator(chat_request:ChatRequest,session_id:str):
    # generate streaming events
    try:
        session_id = sanitize_string(session_id)
        # link response
        async for chunk in agent.get_stream_response(chat_request.messages,session_id=session_id):
            response = StreamResponse(content=chunk,done= False)
            yield f'data:{json.dumps(response.model_dump())}\n\n'

        messages = await agent.get_chat_history(session_id=session_id)
        final_assistant = next((msg for msg in reversed(messages) if msg.role == 'assistant'), None)
        if final_assistant:
            final_response = StreamResponse(
                content=final_assistant.content,
                done=True,
                message_id=final_assistant.id,
            )
            yield f'data:{json.dumps(final_response.model_dump())}\n\n'

    except Exception as e:
                logger.exception(
                    f"stream_chat_request_failed,session_id={str(session_id)},error={str(e)},"
                )
                error_response = StreamResponse(content=str(e), done=True)
                yield f"data: {json.dumps(error_response.model_dump())}\n\n"


@router.get('/messages',response_model = ChatResponse,summary = 'get session message')
async def get_messages_in_session(request:Request,session_id:str,current_session = Depends(get_current_session)) -> ChatResponse:
    try:
        session_id = sanitize_string(session_id)
        logger.info(f'get messages in session,session id = {session_id}')
        messages = await agent.get_chat_history(session_id=session_id)
        return ChatResponse(messages=messages)
    
    except Exception as e:
        logger.error(f"get_messages_failed, session_id={str(session_id)}, error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete('/messages',summary='clear chat history')
async def clear_history(request:Request,session_id:str,current_session = Depends(get_current_session)):
    try:
        session_id = sanitize_string(session_id)
        await agent.clear_history(session_id)
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        logger.error(f'clear_chat_history_failed, session_id={str(session_id)}, error={str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.delete('/memory', summary='clear session memory only')
async def clear_session_memory(request: Request, session_id: str, current_session = Depends(get_current_session)):
    try:
        session_id = sanitize_string(session_id)
        await agent.clear_memory(session_id)
        return {"message": "Session memory cleared successfully"}
    except Exception as e:
        logger.error(f'clear_session_memory_failed, session_id={str(session_id)}, error={str(e)}')
        raise HTTPException(status_code=500, detail=str(e))

@router.delete('/message', summary='delete single message and linked memory')
async def delete_single_message(
    request: Request,
    session_id: str,
    message_id: str,
    current_session = Depends(get_current_session),
):
    try:
        session_id = sanitize_string(session_id)
        message_id = sanitize_string(message_id)
        await agent.delete_message(session_id=session_id, message_id=message_id)
        return {"message": "Message deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f'delete_single_message_failed, session_id={str(session_id)}, message_id={str(message_id)}, error={str(e)}')
        raise HTTPException(status_code=500, detail=str(e))
    
async def close():
    await agent.close_ckpt()
