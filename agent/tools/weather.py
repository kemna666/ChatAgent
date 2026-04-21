import json

from langchain_core.tools import tool
import httpx
from loguru import logger
# the api addr
api_addr = 'http://t.weather.itboy.net/api/weather/city/'

@tool
async def weather(city:str) -> dict:
    '''
    get the weather of a city

    Args: 
        city:str

    Returns :
        dict:
            the weather of the city
    '''
    
    
    city_code = await get_citycode(city)
    logger.debug(f'wetacher tool called,city code = {str(city_code)}')
    async with httpx.AsyncClient() as client:
        resp = await client.get(api_addr + '/' + city_code)
        resp.raise_for_status()
        data = resp.json()
    today = data["data"]["forecast"][0]
    current_wendu = data["data"]["wendu"]
    shidu = data["data"]["shidu"]
    quality = data["data"]["quality"]

    # 拼接成自然语言
    result = (
        f"【{city}今日天气】\n"
        f"日期：{today['ymd']} {today['week']}\n"
        f"天气：{today['type']}\n"
        f"温度：{today['low']} ~ {today['high']}\n"
        f"当前温度：{current_wendu}℃\n"
        f"湿度：{shidu}\n"
        f"空气质量：{quality}（AQI：{today['aqi']}）\n"
        f"风向：{today['fx']}{today['fl']}\n"
        f"提示：{today['notice']}"
    )
    logger.debug(f'weather result = result')
    return result

async def get_citycode(city_name:str):
    '''
    get city code from api
    '''
    logger.debug(f'get city code,city = {city_name}')
    with open('agent/tools/assets/citycode.json','r') as codefile:
        data = json.load(codefile)
    for province in data["citycode"]:
            for city in province["city"]:
                if city["cityname"] == city_name:
                    logger.debug(f'city code = {city['code']}')
                    return city["code"]
    logger.warning(f'city code undefined')