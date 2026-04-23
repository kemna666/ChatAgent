import os
import toml


class Config:
    def __init__(self):
        config = toml.load('config/config.toml')
        self.chat_db = f'postgresql+asyncpg://{config['chat-db']['username']}:{config['chat-db']['passwd']}@{config['chat-db']['host']}:{config['chat-db']['port']}/{config['chat-db']['db_name']}'
        self.llms = config['llms']
        self.embedding_api_key = config['embedding']['api_key']
        self.embedding_base_url = config['embedding']['base_url']
        self.doc_version = config['embedding']['version']



config = Config()