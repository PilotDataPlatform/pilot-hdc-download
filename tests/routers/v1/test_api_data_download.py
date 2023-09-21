# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import time

import jwt
import pytest

from app.config import ConfigClass

pytestmark = pytest.mark.asyncio


async def test_v1_download_status_should_return_400_when_when_token_not_verified(client):
    resp = await client.get(
        '/v1/download/status/bad_token',
    )
    assert resp.status_code == 400
    assert resp.json() == {
        'code': 400,
        'error_msg': 'Not enough segments',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


async def test_v1_download_status_should_return_400_when_when_token_is_not_valid(client, file_folder_jwt_token_invalid):
    resp = await client.get(
        f'/v1/download/status/{file_folder_jwt_token_invalid}',
    )
    assert resp.status_code == 400
    assert resp.json() == {
        'code': 400,
        'error_msg': 'Invalid download token',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


async def test_v1_download_status_should_return_401_when_when_token_expired(client, file_folder_jwt_token_expired):
    resp = await client.get(
        f'/v1/download/status/{file_folder_jwt_token_expired}',
    )
    assert resp.status_code == 401
    assert resp.json() == {
        'code': 401,
        'error_msg': 'Signature has expired',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


async def test_v1_download_status_should_return_404_when_job_not_found(client, file_folder_jwt_token, httpx_mock):

    httpx_mock.add_response(
        method='GET',
        url='http://dataops_service/v1/task-stream/static/'
        '?session_id=test_session_id'
        '&container_code=test_container'
        '&container_type=test_type'
        '&action_type=data_download'
        '&job_id=test_job_id',
        json={},
        status_code=404,
    )

    resp = await client.get(
        f'/v1/download/status/{file_folder_jwt_token}',
    )
    assert resp.status_code == 404
    assert resp.json() == {
        'code': 404,
        'error_msg': '[Invalid Job ID] Not Found',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


async def test_v1_download_status_should_return_200_when_success(
    client,
    file_folder_jwt_token,
    httpx_mock,
):

    httpx_mock.add_response(
        method='GET',
        url='http://dataops_service/v1/task-stream/static/'
        '?session_id=test_session_id'
        '&container_code=test_container'
        '&container_type=test_type'
        '&action_type=data_download'
        '&job_id=test_job_id',
        json={
            'stream_info': [
                {
                    'session_id': 'test_session_id',
                    'target_names': ['test/folder/file'],
                    'target_type': 'file',
                    'container_code': 'test_container',
                    'container_type': 'test_type',
                    'action_type': 'data_download',
                    'status': 'RUNNING',
                    'job_id': 'test_job_id',
                }
            ]
        },
        status_code=200,
    )

    resp = await client.get(
        f'/v1/download/status/{file_folder_jwt_token}',
    )

    assert resp.status_code == 200
    result = resp.json()['result']
    assert result['session_id'] == 'test_session_id'
    assert result['job_id'] == 'test_job_id'
    assert result['target_names'][0] == 'test/folder/file'
    assert result['action_type'] == 'data_download'
    assert result['status'] == 'RUNNING'


async def test_v1_download_should_return_400_when_token_segment_missing(client):
    resp = await client.get(
        '/v1/download/bad_token',
    )
    assert resp.status_code == 400
    assert resp.json() == {
        'code': 400,
        'error_msg': 'Not enough segments',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


async def test_v1_download_should_return_400_when_when_token_is_not_valid(client, file_folder_jwt_token_invalid):
    resp = await client.get(
        f'/v1/download/{file_folder_jwt_token_invalid}',
    )
    assert resp.status_code == 400
    assert resp.json() == {
        'code': 400,
        'error_msg': 'Invalid download token',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


async def test_v1_download_should_return_401_when_when_token_expired(client, file_folder_jwt_token_expired):
    resp = await client.get(
        f'/v1/download/{file_folder_jwt_token_expired}',
    )
    assert resp.status_code == 401
    assert resp.json() == {
        'code': 401,
        'error_msg': 'Signature has expired',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


async def test_v1_download_should_return_404_when_path_not_found(client, file_folder_jwt_token):

    resp = await client.get(
        f'/v1/download/{file_folder_jwt_token}',
    )

    assert resp.status_code == 404
    assert resp.json() == {
        'code': 404,
        'error_msg': '[File not found] test/folder/file.',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


async def test_v1_download_should_return_200_when_success(
    client,
    httpx_mock,
    mock_kafka_producer,
):

    httpx_mock.add_response(
        method='POST',
        url='http://dataops_service/v1/task-stream/',
        json={
            'stream_info': {
                'session_id': 'admin-3fa85f64-5717-4562-b3fc-2c963f66afa6',
                'target_names': ['file_1.txt', 'file_2.txt'],
                'target_type': 'batch',
                'container_code': 'test_project',
                'container_type': 'project',
                'action_type': 'data_download',
                'status': 'WAITING',
                'job_id': '3fa85f64-5717-4562-b3fc-2c963f66afa6',
            }
        },
        status_code=200,
    )

    hash_token_dict = {
        'file_path': 'tests/routers/v1/empty.txt',
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

    hash_code = jwt.encode(hash_token_dict, key=ConfigClass.DOWNLOAD_KEY, algorithm='HS256')

    resp = await client.get(
        f'/v1/download/{hash_code}',
    )
    assert resp.status_code == 200
    assert resp.text == 'file content\n'
