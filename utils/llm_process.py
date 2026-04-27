import tiktoken
from typing import List, Union, Dict, Any

from schemas.llm import Message
from langchain_core.language_models.chat_models import BaseChatModel
from loguru import logger
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage, trim_messages as _trim_message

def dump_messages(messages: list[Message]) -> list[dict]:
    """Dump the messages to a list of dictionaries.

    Args:
        messages (list[Message]): The messages to dump.

    Returns:
        list[dict]: The dumped messages.
    """
    return [message.model_dump() for message in messages]

def handle_response(message:Union[Message,List[Message]]) -> Message:
    text_part = []    
    if isinstance(message.content,list):
        # extract text parts
        for block in message.content:
            if isinstance(block,dict):
                if block.get('type') == 'text' and 'text' in block:
                    text_part.append(block['text'])
                elif block.get('type') == 'reasoning':
                # log reasoning blocks
                    logger.debug('received reasoning block')
                else:
                    logger.warning(f'unknown content block type = {block.get("type")}')
                    text_part.append(block)
            elif isinstance(block,str):
                text_part.append(block)
    else:
        text_part.append(message.content)
    message.content = ''.join(text_part)
    return message

def prepare_message(messages:List[Message],llm:BaseChatModel,system_prompt:str) -> List[Message]:
    # prepare messages for llm
    original_messages = messages
    try:
        messages = dump_messages(messages)
        trimmed_message = _trim_message(
            messages,
            strategy='last',
            max_tokens= 10000,
            start_on='human',
            include_system=False,
            allow_partial= False,
            token_counter=count_token_in_messages
        )
        result = conver_message(trimmed_message)
    except ValueError as e:
        if 'Unrecognized content block type' in str(e):
            logger.warning(
                f'token_counting_failed_skipping_trim,error = {str(e)},message count = {len(messages)}'
            )
            trimmed_message = original_messages
            result = conver_message(trimmed_message)
        
        else: 
            raise
    
    return [Message(role='system',content=system_prompt)] + result


def conver_message(messages:List[BaseMessage]) -> List[Message]:
        result = []
        for lc_msg in messages:
            if isinstance(lc_msg, HumanMessage):
                role = "user"
            elif isinstance(lc_msg, AIMessage):
                role = "assistant"
            elif isinstance(lc_msg, SystemMessage):
                role = "system"
            elif isinstance(lc_msg, ToolMessage):
                role = "tool"
            else:
                role = "unknown"
            if role == 'tool':
                logger.warning(f'detected tool msg , converting...')
                role = "system"
                lc_msg = tool_to_system_message(lc_msg)
            
            result.append(Message(role=role, content=lc_msg.content))
        return result


def tool_to_system_message(tool_msg: ToolMessage) -> SystemMessage:
    # convert tool output into hidden context for the next model turn
    return SystemMessage(
        content=(
            f"Tool `{tool_msg.name}` returned the following context.\n"
            "Use it to answer the user completely. Do not expose raw tool dumps, "
            "result indexes, or the literal retrieval transcript unless the user asks for it.\n"
            f"{tool_msg.content}"
        )
    )


def _extract_message_content_and_role(message: Any) -> tuple[str, str]:
    if isinstance(message, dict):
        role = str(message.get("role") or message.get("type") or "")
        content = message.get("content", "")
    else:
        role = str(getattr(message, "type", getattr(message, "role", "")))
        content = getattr(message, "content", "")

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    text_parts.append(str(item.get("text", "")))
                elif "content" in item:
                    text_parts.append(str(item["content"]))
            else:
                text_parts.append(str(item))
        content = "".join(text_parts)

    return str(content), role


def count_token_in_messages(messages:List[Any]) -> int:
    # count token in messages
    encoding = tiktoken.get_encoding("cl100k_base")  
    tokens_per_message = 4  

    num_tokens = 0
    for message in messages:
        content, role = _extract_message_content_and_role(message)
        num_tokens += tokens_per_message
        num_tokens += len(encoding.encode(content))
        num_tokens += len(encoding.encode(role))  # 'system', 'user', 'assistant'
    num_tokens += 3  # 每轮对话的额外开销（如 <|im_start|> 等）
    return num_tokens
