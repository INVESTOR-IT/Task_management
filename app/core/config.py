from pydantic_settings import BaseSettings, SettingsConfigDict
from loguru import logger

import sys


class Settings(BaseSettings):
    API_V1_STR: str = '/api/v1'

    DATABASE_URL: str
    AMQP_URL: str

    LOG_LEVEL: str = 'INFO'

    WORKER_PREFETCH_COUNT: int = 1
    WORKER_MAX_CONCURRENT_TASKS: int = 5

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


settings = Settings()

logger.remove()
logger.add(sys.stderr, level=settings.LOG_LEVEL)
