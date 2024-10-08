# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import time

import jwt
import pytest

from app.resources.download_token_manager import InvalidToken
from app.resources.download_token_manager import generate_token
from app.resources.download_token_manager import verify_download_token


@pytest.mark.asyncio
async def test_token_flow():
    """
    Summary:
        the test will use encode and decode at same time to make sure
        the hash code is properly generated and no data loss
    """

    container_code = 'test_container'
    container_type = 'test_type'
    file_path = 'tests/routers/v1/empty.txt'
    operator = 'test_user'
    session_id = 'test_session_id'
    job_id = 'test_job_id'
    payload = {'test_payload': 'test_value'}

    hash_code = await generate_token(container_code, container_type, file_path, operator, session_id, job_id, payload)

    decoded_payload = await verify_download_token(hash_code)

    assert decoded_payload.get('container_code') == container_code
    assert decoded_payload.get('container_type') == container_type
    assert decoded_payload.get('file_path') == file_path
    assert decoded_payload.get('operator') == operator
    assert decoded_payload.get('session_id') == session_id
    assert decoded_payload.get('job_id') == job_id
    assert decoded_payload.get('payload') == payload


@pytest.mark.asyncio
async def test_token_expired():
    hash_token_dict = {
        'file_path': 'test/folder/file',
        'issuer': 'SERVICE DATA DOWNLOAD',
        'operator': 'test_user',
        'session_id': 'test_session_id',
        'job_id': 'test_job_id',
        'container_code': 'test_container',
        'container_type': 'test_type',
        'payload': {},
        'iat': int(time.time()) - 100,
        'exp': int(time.time()) - 100,
    }

    hash_code = jwt.encode(hash_token_dict, key='test_key', algorithm='HS256')

    try:
        verify_download_token(hash_code)
    except Exception as e:
        assert type(e) == jwt.ExpiredSignatureError


@pytest.mark.asyncio
async def test_token_invalid():
    hash_token_dict = {
        'issuer': 'SERVICE DATA DOWNLOAD',
        'operator': 'test_user',
        'session_id': 'test_session_id',
        'job_id': 'test_job_id',
        'container_code': 'test_container',
        'container_type': 'test_type',
        'payload': {},
        'iat': int(time.time()),
        'exp': int(time.time()) + 100,
    }

    hash_code = jwt.encode(hash_token_dict, key='test_key', algorithm='HS256')

    try:
        verify_download_token(hash_code)
    except Exception as e:
        assert type(e) == InvalidToken


@pytest.mark.asyncio
async def test_token_wrong_key():
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
        'exp': int(time.time()) + 100,
    }

    hash_code = jwt.encode(hash_token_dict, key='test_key', algorithm='HS256')

    try:
        verify_download_token(hash_code)
    except Exception as e:
        assert type(e) == InvalidToken
