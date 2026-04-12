from schemas.llm import Message
from typing import List
from langchain_core.messages.base import BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
from loguru import logger
from langchain_core.messages import trim_messages as _trim_message


def dump_messages(messages:List[Message]) -> List[dict]:
    # export messages into dict
    return [message.model_dump() for message in messages]

def handle_response(message:BaseMessage) -> BaseMessage:    
    if isinstance(message.content,list):
        # extract text parts
        text_part = []
        for block in message.content:
            if isinstance(block,dict):
                if block.get('type') == 'text' and 'text' in block:
                    text_part.append[block['text']]
                elif block.get('type') == 'reasoning':
                # log reasoning blocks
                    logger.debug('received reasoning block')
            elif isinstance(block,str):
                text_part.append(block)
        message.content = ''.join(text_part)
        logger.debug('processed structured') 
    return message

def prepare_message(messages:List[Message],llm:BaseChatModel,system_prompt:str) -> List[Message]:
    # prepare messages for llm
    try:

        trimmed_message = _trim_message(
            dump_messages(messages),
            strategy='last',
            token_counter=llm,
            max_tokens= 10000,
            start_on='human',
            include_system=False,
            allow_partial= False
        )

    except ValueError as e:
        if 'Unrecognized content block type' in str(e):
            logger.warning(
                f'token_counting_failed_skipping_trim,error = {str(e)},message count = {len(messages)}'
            )
            trimmed_message = messages
        else: 
            raise
    
    return [Message(role='system',content=system_prompt)] + trimmed_message