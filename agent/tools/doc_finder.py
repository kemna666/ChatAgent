

from typing import List
from langchain.tools import tool
from services.doc_spilt import doc_handler

@tool

async def doc_searcher(query:str,top_k:int = 3) -> str:
    '''
    find query in local doc

    Args:
    query: the content you want to search
    top_k: the number of the most relavent paras

    Return:
    str: the content of result
    '''
    result = await doc_handler.retrive_document(query=query,top_k = top_k)

    formatted_result = []

    for i,doc in enumerate(result,1):
        formatted_result.append(
            f'results:{i}\n'
            f'source:{doc.metadata['filename']}\n'
            f'chunk:{doc.page_content[:300]}'
        )
    
    return '\n'.join(formatted_result) if formatted_result else 'no relavent content'