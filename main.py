from datetime import timedelta,datetime,timezone
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request,status
from grpc import Status
from loguru import logger
from services.databaseservice import database_service
from api.v1.api import api_router




# initialize env before app start
async def lifespan(app:FastAPI):
    # if tables don't exist,create it
    await database_service.create_table()
    logger.info('database has been initizlized')
    logger.info('application startup')
    yield
    logger.info('app closed')

app = FastAPI(
    title= 'ChatAgent',
    version='0.0.1',
    lifespan=lifespan
)


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