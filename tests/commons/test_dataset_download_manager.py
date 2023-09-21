# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import pytest

from app.commons.download_manager.dataset_download_manager import create_dataset_download_client

pytestmark = pytest.mark.asyncio


async def test_download_client_without_files(httpx_mock, mock_boto3, mock_kafka_producer, mock_boto3_clients):
    httpx_mock.add_response(
        method='GET',
        url='http://metadata_service/v1/items/search/?container_code=any_code'
        '&container_type=dataset&zone=1&recursive=true&status=ACTIVE&parent_'
        'path=&owner=me&type=file&page_size=100000',
        json={'result': []},
    )

    download_client = await create_dataset_download_client(
        boto3_clients=mock_boto3_clients,
        operator='me',
        container_code='any_code',
        container_id='fake_id',
        container_type='project',
        session_id='1234',
        auth_token='fake_token',
    )

    assert len(download_client.files_to_zip) == 0


async def test_download_client_add_file(httpx_mock, mock_boto3, mock_kafka_producer, mock_boto3_clients):
    httpx_mock.add_response(
        method='GET',
        url='http://metadata_service/v1/items/search/?container_code=any_code'
        '&container_type=dataset&zone=1&recursive=true&status=ACTIVE&parent_'
        'path=&owner=me&type=file&page_size=100000',
        json={
            'result': [
                {
                    'code': 'any_code',
                    'labels': 'any_label',
                    'storage': {'location_uri': 'http://anything.com/bucket/obj_path'},
                    'id': 'geid_1',
                    'operator': 'me',
                    'parent_path': 'admin',
                    'type': 'file',
                    'container_code': 'fake_project_code',
                    'zone': 1,
                }
            ]
        },
    )

    download_client = await create_dataset_download_client(
        boto3_clients=mock_boto3_clients,
        operator='me',
        container_code='any_code',
        container_id='fake_id',
        container_type='project',
        session_id='1234',
        auth_token='fake_token',
    )

    assert len(download_client.files_to_zip) == 1
    assert download_client.files_to_zip[0].get('id') == 'geid_1'


async def test_download_dataset_add_schemas(httpx_mock, mock_boto3, mock_kafka_producer, mock_boto3_clients):
    httpx_mock.add_response(
        method='GET',
        url='http://metadata_service/v1/items/search/?container_code=any_code'
        '&container_type=dataset&zone=1&recursive=true&status=ACTIVE&parent_'
        'path=&owner=me&type=file&page_size=100000',
        json={'result': []},
    )

    download_client = await create_dataset_download_client(
        boto3_clients=mock_boto3_clients,
        operator='me',
        container_code='any_code',
        container_id='fake_id',
        container_type='project',
        session_id='1234',
        auth_token='fake_token',
    )

    httpx_mock.add_response(
        method='POST',
        url='http://dataset_service/v1/schema/list',
        json={'result': [{'name': 'test_schema_1', 'content': {}}]},
        status_code=200,
    )

    httpx_mock.add_response(
        method='POST',
        url='http://dataset_service/v1/schema/list',
        json={'result': [{'name': 'test_schema_2', 'content': {}}]},
        status_code=200,
    )

    await download_client.add_schemas('test_id')
