# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import asyncio
import os
import shutil
import time
from io import BytesIO

import jwt
import pytest
from async_asgi_testclient import TestClient
from httpx import Response
from starlette.config import environ
from urllib3 import HTTPResponse

environ['namespace'] = 'greenroom'
environ['CONFIG_CENTER_ENABLED'] = 'false'
environ['CORE_ZONE_LABEL'] = 'Core'
environ['GREEN_ZONE_LABEL'] = 'Greenroom'

environ['METADATA_SERVICE'] = 'http://METADATA_SERVICE'
environ['DATASET_SERVICE'] = 'http://DATASET_SERVICE'
environ['DATAOPS_SERVICE'] = 'http://DATAOPS_SERVICE'
environ['PROJECT_SERVICE'] = 'http://PROJECT_SERVICE'

environ['KAFKA_URL'] = 'http://KAFKA_URL'

environ['S3_PUBLIC'] = 'S3_PUBLIC'
environ['S3_INTERNAL'] = 'S3_INTERNAL'
environ['S3_INTERNAL_HTTPS'] = 'false'
environ['S3_ACCESS_KEY'] = 'S3_ACCESS_KEY'
environ['S3_SECRET_KEY'] = 'S3_SECRET_KEY'

environ['DOWNLOAD_KEY'] = 'DOWNLOAD_KEY'

environ['REDIS_HOST'] = 'localhost'
environ['REDIS_PORT'] = '6379'
environ['REDIS_DB'] = '0'
environ['REDIS_PASSWORD'] = ''

environ['RDS_HOST'] = 'localhost'
environ['RDS_PORT'] = '6379'
environ['RDS_USER'] = 'test'
environ['RDS_PWD'] = 'test'
environ['RDS_SCHEMA_DEFAULT'] = 'INDOC_TEST'
environ['RDS_DBNAME'] = 'INDOC_TEST'

environ['ROOT_PATH'] = './tests/'

environ['OPEN_TELEMETRY_ENABLED'] = 'false'


@pytest.fixture(scope='session')
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
    asyncio.set_event_loop_policy(None)


@pytest.fixture(scope='session', autouse=True)
def create_folders():
    folder_path = './tests/tmp/'
    os.makedirs(folder_path + 'any_id_1')
    yield
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    from app.config import ConfigClass

    monkeypatch.setattr(ConfigClass, 'MINIO_TMP_PATH', './tests/tmp/')


@pytest.fixture
def file_folder_jwt_token():
    hash_token_dict = {
        'file_path': 'test/folder/file',
        'issuer': 'SERVICE DATA DOWNLOAD',
        'operator': 'test_user',
        'session_id': 'test_session_id',
        'job_id': 'test_job_id',
        'container_code': 'test_container',
        'container_type': 'test_type',
        'payload': {},
        'iat': int(time.time()),
        'exp': int(time.time()) + 10,
    }

    hash_code = jwt.encode(hash_token_dict, key=environ['DOWNLOAD_KEY'], algorithm='HS256')
    return hash_code


@pytest.fixture
def file_folder_jwt_token_expired():
    hash_token_dict = {
        'file_path': 'test/folder/file',
        'issuer': 'SERVICE DATA DOWNLOAD',
        'operator': 'test_user',
        'session_id': 'test_session_id',
        'job_id': 'test_job_id',
        'container_code': 'test_container',
        'container_type': 'test_type',
        'payload': {},
        'iat': int(time.time()),
        'exp': int(time.time()) - 10,
    }

    hash_code = jwt.encode(hash_token_dict, key=environ['DOWNLOAD_KEY'], algorithm='HS256')
    return hash_code


@pytest.fixture
def file_folder_jwt_token_invalid():
    hash_token_dict = {
        'issuer': 'SERVICE DATA DOWNLOAD',
        'operator': 'test_user',
        'session_id': 'test_session_id',
        'job_id': 'test_job_id',
        'container_code': 'test_container',
        'container_type': 'test_type',
        'payload': {},
        'iat': int(time.time()),
        'exp': int(time.time()) + 10,
    }

    hash_code = jwt.encode(hash_token_dict, key=environ['DOWNLOAD_KEY'], algorithm='HS256')
    return hash_code


@pytest.fixture
def dataset_download_jwt_token():
    hash_token_dict = {
        'location': 'test/folder/file',
        'iat': int(time.time()),
        'exp': int(time.time()) + 10,
    }

    hash_code = jwt.encode(hash_token_dict, key=environ['DOWNLOAD_KEY'], algorithm='HS256')
    return hash_code


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def app(anyio_backend):
    from app.main import create_app

    app = create_app()
    yield app


@pytest.fixture
async def client(app):
    return TestClient(app)


@pytest.fixture
def mock_boto3(monkeypatch):
    from common.object_storage_adaptor.boto3_client import Boto3Client

    class FakeObject:
        size = b'a'

    http_response = HTTPResponse()
    response = Response(status_code=200)
    response.raw = http_response
    response.raw._fp = BytesIO(b'File like object')

    async def fake_init_connection():
        pass

    async def fake_download_object(x, y, z, z1):
        return response

    async def fake_get_download_presigned_url(x, y, z):
        return f'http://minio.minio:9000/{y}/{z}'

    monkeypatch.setattr(Boto3Client, 'init_connection', lambda x: fake_init_connection())
    monkeypatch.setattr(Boto3Client, 'download_object', lambda x, y, z, z1: fake_download_object(x, y, z, z1))
    monkeypatch.setattr(
        Boto3Client, 'get_download_presigned_url', lambda x, y, z: fake_get_download_presigned_url(x, y, z)
    )


@pytest.fixture
def mock_boto3_clients():
    from common.object_storage_adaptor.boto3_client import Boto3Client

    boto3_internal = Boto3Client('test_connection', access_key='test', secret_key='test')
    boto3_public = Boto3Client('test_connection', access_key='test', secret_key='test')

    return {'boto3_internal': boto3_internal, 'boto3_public': boto3_public}


@pytest.fixture
def mock_kafka_producer(monkeypatch):
    from app.commons.kafka_producer import KakfaProducer

    async def fake_init_connection():
        pass

    async def fake_send_message(x, y, z):
        pass

    async def fake_validate_message(x, y, z):
        pass

    async def fake_create_activity_log(x, y, z, z1):
        pass

    monkeypatch.setattr(KakfaProducer, 'init_connection', lambda x: fake_init_connection())
    monkeypatch.setattr(KakfaProducer, '_send_message', lambda x, y, z: fake_send_message(x, y, z))
    monkeypatch.setattr(KakfaProducer, '_validate_message', lambda x, y, z: fake_validate_message(x, y, z))
    monkeypatch.setattr(KakfaProducer, 'create_activity_log', lambda x, y, z, z1: fake_create_activity_log(x, y, z, z1))
