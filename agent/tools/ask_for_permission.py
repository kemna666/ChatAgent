

from langgraph.types import interrupt
from langchain_core.tools import tool

@tool
def ask_for_permission(question:str) -> str:
    '''ask human for a question or premission before preceedion
        use the tool whenever you need clarification,confirmation or additional input from the user before taking a significant action
        Args:
        question:the question to ask
        Returns:
        str:the human's response
    '''
    user_response = interrupt(question)
    return str(user_response)