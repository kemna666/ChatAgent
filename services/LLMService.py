from typing import Any, Dict,List, Optional
from loguru import logger
from langchain_core.language_models.chat_models import BaseChatModel
from langchain.chat_models import init_chat_model
from openai import APIError, APITimeoutError, OpenAIError, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from config.config import config

from schemas.llm import Message



class LLMRegistry:
    _models:List[Dict[str,Any]] =[]
    _instances:Dict[str,BaseChatModel] = {} 
    __api_key__ = config.llms['api_key']
    __base_url__ = config.llms['base_url']
    _max_token = 1000
    @classmethod
    def load_cfg(cls,file_path) -> None:
        #load configs from file
        pass


    @classmethod 
    def register(cls,model_name:str,provider:str,reasoning:Dict[str,str] = {'effort':'low'},**kwargs) -> None:
        # register model in dynamic mode
        cls._models.append({
            'name':model_name,
            'api_key':cls.__api_key__,
            'max_tokens':cls._max_token,
            'reasoning':reasoning,
            'provider':provider,
            **kwargs
        })
        cls.create_llm(model_name,provider)
        logger.info(f'LLM Registered:{model_name}')

    @classmethod
    def get_all_model_names(cls) -> List[str]:
        #get the name of models that has been registerd
        return list(model['name'] for model in cls._models)
    
    @classmethod
    def create_llm(cls,model_name:str,provider:str) -> BaseChatModel:
        # create llm chat session
        model_cfg = next((m for m in cls._models if m["name"] == model_name), None)
        if not model_cfg:
            raise ValueError(f"Model {model_name} not found")
        
        logger.info(f'LLM Creating:{model_name}')
        
        cls._instances[model_name] = init_chat_model(
            model=model_name,
            model_provider=provider,
            api_key = cls.__api_key__,
            base_url = cls.__base_url__,
            max_tokens = cls._max_token,
        )
        logger.info(f'LLM Created:{model_name}')
        return cls._instances[model_name]
    
    @classmethod
    def get(cls,model_name:str)->BaseChatModel:
        return cls._instances[model_name]


class LLMService:

    def __init__(self):
        self.register_models()
        self._llm:Optional[BaseChatModel] = None
        self.all_model_names = LLMRegistry.get_all_model_names()
        self.num_models = len(self.all_model_names)
        self.default_model = config.llms['default_model']

        try:
            self.current_model = self.default_model
            self._llm = LLMRegistry.get(self.default_model)
            logger.info(f'model has been initialized,model name:{self.current_model}')
        except (ValueError,Exception) as e:
            logger.error(f'model has not been initialized successfully,error:{str(e)}')
        

    def register_models(self):
        try:
            if config.llms['models'] is not None:
                for i,model in enumerate(config.llms['models']):
                    provider = model['provider']
                    LLMRegistry.register(model['model'],provider)
                    logger.info(f'model has been registered,model name:{model["model"]},provider:{provider}')
        except Exception as e:
            logger.error(f'model registration failed,error = {str(e)},{config.llms["models"]}')
    
    def switch_model(self,model_name:str) -> bool:
        try:    
            self.model = LLMRegistry.get(model_name)    
            self.current_model = model_name

            logger.info(f'model has been switched to {model_name}')
            return True
        
        except Exception as e:
            logger.warning(f'model switched failed,error = {str(e)}')
            return False
    

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIError)),
        before_sleep=lambda retry_state: logger.warning(f"Retrying LLM call... attempt #{retry_state.attempt_number}; sleep for {retry_state.next_action.sleep} seconds; last exception: {retry_state.outcome.exception() if retry_state.outcome else 'None'}"),
        reraise=True,
    )

    async def _call_llm_with_retry(self, messages: List[Message]) -> Message:
        """Call the LLM with automatic retry logic.        """
        if not self._llm:
            raise RuntimeError("llm not initialized")

        try:
            response = await self._llm.ainvoke(messages)
            logger.debug("llm_call_successful", message_count=len(messages))
            return response
        except (RateLimitError, APITimeoutError, APIError) as e:
            logger.warning(
                "llm_call_failed_retrying",
                error_type=type(e).__name__,
                error=str(e),
                exc_info=True,
            )
            raise
        except OpenAIError as e:
            logger.error(
                "llm_call_failed",
                error_type=type(e).__name__,
                error=str(e),
            )
            raise

    async def call(self,message:List[Message],model_name:Optional[str] = None) -> Message:
        if model_name:
            await self.switch_model(model_name)
        try:  
            response = await self._call_llm_with_retry(message)
            if not response:
                for model in self.all_model_names:
                    self.switch_model(model)
                    response = await self._call_llm_with_retry(message)
                    if response:
                        break
            return response
        except OpenAIError as e:
            logger.error(f'response failed,error = {str(e)}')
            raise                    
    
    def get_llm(self) -> Optional[BaseChatModel]:

        return self._llm
    
    def bind_tools(self,tools:List) -> "LLMService":

        if self._llm:
            self._llm.bind_tools(tools)
            logger.info('llm has bind tools successfully')
        return self
    
llmservice = LLMService()