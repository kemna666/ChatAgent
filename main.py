from datetime import timedelta,datetime,timezone
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request,status
from grpc import Status
from loguru import logger
from services.databaseservice import database_service
from api.v1.api import api_router
from api.v1.chat import close
from config.config import config
from services.doc_spilt import doc_handler
from services.cache_redis import cache_service

# initialize env before app start
async def lifespan(app:FastAPI):
    # if tables don't exist,create it
    await database_service.create_table()
    logger.add(
    "logs/app_{time}.log",   # 文件路径（自动带时间）
    rotation="10 MB",        # 单个文件最大10MB自动切分
    retention="7 days",      # 保留7天
    compression="zip",       # 自动压缩旧日志
    level="INFO",            # 日志等级
    encoding="utf-8",
    enqueue=True             # 多进程/异步安全（非常重要）
)
    logger.info('database has been initizlized')
    logger.info('application startup')
    await cache_service.get_redis_client()
    if config.doc_version == 1:
        await doc_handler.store_doc()
    yield
    await close()
    logger.info('app closed')

app = FastAPI(
    title= 'ChatAgent',
    version='0.0.1',
    lifespan=lifespan
)

6
# inculude apis in api/v1
app.include_router(api_router, prefix='/api/v1')

@app.get('/',summary='main entry point')
async def root(request:Request):
    logger.info('root called')
    return {
        'name':'ChatAgent'
    }

@app.get('/health',summary='check if database healthy')
async def health(reauest:Request):
    logger.info('health check')
    db_health = await database_service.check_health()
    response = {
        "status": "healthy" if db_health else "degraded",
        "components": {"api": "healthy", "database": "healthy" if db_health else "unhealthy"},
        "timestamp": datetime.now(timezone(timedelta(hours=8))).isoformat(),
    }
    status_code = status.HTTP_200_OK if db_health else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=response, status_code=status_code)

