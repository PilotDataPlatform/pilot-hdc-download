# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import logging
from functools import lru_cache

from pydantic import BaseSettings
from pydantic import Extra


class Settings(BaseSettings):
    """Store service configuration settings."""

    APP_NAME: str = 'service_download'
    VERSION: str = '2.2.16'
    HOST: str = '127.0.0.1'
    PORT: int = 5077
    WORKERS: int = 1
    RELOAD: bool = False
    namespace: str

    LOGGING_LEVEL: int = logging.INFO
    LOGGING_FORMAT: str = 'json'

    # disk mounts
    ROOT_PATH: str
    CORE_ZONE_LABEL: str
    GREEN_ZONE_LABEL: str

    # services
    DATAOPS_SERVICE: str
    DATASET_SERVICE: str
    METADATA_SERVICE: str
    PROJECT_SERVICE: str

    # minio
    # this endpoint is internal communication
    S3_INTERNAL: str
    S3_INTERNAL_HTTPS: bool = False
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    # this is for presigned url
    S3_PUBLIC: str
    # by default the minio public will be https
    # for local testing add the one to .env as False
    S3_PUBLIC_HTTPS: bool = True

    # download secret
    DOWNLOAD_KEY: str
    DOWNLOAD_TOKEN_EXPIRE_AT: int = 86400

    # Redis Service
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_USER: str = 'default'
    REDIS_DB: int
    REDIS_PASSWORD: str

    # kafka
    KAFKA_URL: str
    KAFKA_ITEM_ACTIVITY_TOPIC: str = 'metadata.items.activity'
    KAFKA_DATASET_ACTIVITY_TOPIC: str = 'dataset.activity'

    OPEN_TELEMETRY_ENABLED: bool = False
    OPEN_TELEMETRY_HOST: str = '127.0.0.1'
    OPEN_TELEMETRY_PORT: int = 6831

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = Extra.allow

    def __init__(self) -> None:
        super().__init__()

        # services
        self.DATAOPS_SERVICE_V2 = self.DATAOPS_SERVICE + '/v2/'
        self.DATAOPS_SERVICE = self.DATAOPS_SERVICE + '/v1/'
        self.DATASET_SERVICE = self.DATASET_SERVICE + '/v1/'
        self.METADATA_SERVICE = self.METADATA_SERVICE + '/v1/'

        # minio
        self.MINIO_TMP_PATH = self.ROOT_PATH + '/tmp/'

        # redis
        self.REDIS_URL = (
            f'redis://{self.REDIS_USER}:{self.REDIS_PASSWORD}@{self.REDIS_HOST}' + f':{self.REDIS_PORT}/{self.REDIS_DB}'
        )


@lru_cache(1)
def get_settings() -> Settings:
    settings = Settings()
    return settings


ConfigClass = get_settings()
