import os
import toml


class Config:
    def __init__(self):
        config = toml.load('config/config.toml')
        self.chat_db = f'postgresql+asyncpg://{config['chat-db']['username']}:{config['chat-db']['passwd']}@{config['chat-db']['host']}:{config['chat-db']['port']}/{config['chat-db']['db_name']}'
        self.llms = config['llms']
        os.environ['OPENAI_API_KEY'] = self.llms['api_key']



config = Config()