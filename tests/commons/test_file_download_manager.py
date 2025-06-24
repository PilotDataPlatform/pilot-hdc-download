# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from unittest import mock

import minio
import pytest

from app.commons.download_manager.file_download_manager import EmptyFolderError
from app.commons.download_manager.file_download_manager import FileDownloadClient
from app.commons.download_manager.file_download_manager import InvalidEntityType
from app.commons.download_manager.file_download_manager import create_file_download_client
from app.models.models_data_download import EFileStatus


async def test_download_client_without_files_should_raise_exception(httpx_mock, mock_boto3, mock_boto3_clients):
    for container_type in ['project', 'dataset']:
        with pytest.raises(EmptyFolderError):
            await create_file_download_client(
                files=[],
                boto3_clients=mock_boto3_clients,
                operator='me',
                container_code='any_code',
                container_type=container_type,
                session_id='1234',
                auth_token='fake_token',
                network_origin='unknown',
            )


async def test_download_client_add_file(httpx_mock, mock_boto3_clients):
    httpx_mock.add_response(
        method='GET',
        url='http://metadata_service/v1/item/geid_1/',
        json={
            'result': {
                'code': 'any_code',
                'labels': 'any_label',
                'storage': {'location_uri': 'http://anything.com/bucket/obj_path'},
                'id': 'geid_1',
                'operator': 'me',
                'parent_path': 'admin',
                'type': 'file',
                'container_code': 'fake_project_code',
                'zone': 0,
            }
        },
    )

    download_client = await create_file_download_client(
        files=[{'id': 'geid_1'}],
        boto3_clients=mock_boto3_clients,
        operator='me',
        container_code='any_code',
        container_type='project',
        session_id='1234',
        auth_token='fake_token',
        network_origin='unknown',
    )

    assert len(download_client.files_to_zip) == 1
    assert download_client.files_to_zip[0].get('id') == 'geid_1'


async def test_download_client_add_file_fail_with_name_folder(httpx_mock, mock_boto3_clients):
    httpx_mock.add_response(
        method='GET',
        url='http://metadata_service/v1/item/geid_1/',
        json={
            'result': {
                'code': 'any_code',
                'labels': 'any_label',
                'storage': {'location_uri': 'http://anything.com/bucket/obj_path'},
                'id': 'geid_1',
                'operator': 'me',
                'parent_path': 'admin',
                'type': 'name_folder',
                'container_code': 'fake_project_code',
                'zone': 0,
            }
        },
    )

    try:
        _ = await create_file_download_client(
            files=[{'id': 'geid_1'}],
            boto3_clients=mock_boto3_clients,
            operator='me',
            container_code='any_code',
            container_type='project',
            session_id='1234',
            auth_token='fake_token',
            network_origin='unknown',
        )
    except InvalidEntityType:
        assert True


async def test_one_file_set_status_SUCCEED_when_success(
    httpx_mock, mock_boto3, mock_kafka_producer, mock_boto3_clients
):
    httpx_mock.add_response(
        method='GET',
        url='http://metadata_service/v1/item/geid_1/',
        json={
            'result': {
                'code': 'any_code',
                'labels': 'any_label',
                'storage': {'location_uri': 'http://anything.com/bucket/obj_path'},
                'id': 'geid_1',
                'operator': 'me',
                'parent_path': 'admin',
                'type': 'file',
                'container_code': 'fake_project_code',
                'container_type': 'project',
                'zone': 0,
                'name': 'test_item',
            }
        },
    )

    download_client = await create_file_download_client(
        files=[{'id': 'geid_1'}],
        boto3_clients=mock_boto3_clients,
        operator='me',
        container_code='any_code',
        container_type='project',
        session_id='1234',
        auth_token='fake_token',
        network_origin='unknown',
    )
    with mock.patch.object(FileDownloadClient, 'set_status') as fake_set:
        await download_client.background_worker('fake_hash')
    fake_set.assert_called_with(EFileStatus.SUCCEED, payload={'hash_code': 'fake_hash'})


async def test_zip_worker_set_status_SUCCEED_when_success(
    httpx_mock, mock_boto3, mock_kafka_producer, mock_boto3_clients
):
    for x in ['geid_1']:
        httpx_mock.add_response(
            method='GET',
            url=f'http://metadata_service/v1/item/{x}/',
            json={
                'result': {
                    'code': 'any_code',
                    'labels': 'any_label',
                    'storage': {'location_uri': 'http://anything.com/bucket/obj_path'},
                    'id': x,
                    'operator': 'me',
                    'parent_path': 'admin',
                    'type': 'file',
                    'container_code': 'fake_project_code',
                    'container_type': 'project',
                    'zone': 0,
                    'name': x,
                }
            },
        )

    download_client = await create_file_download_client(
        files=[{'id': 'geid_1'}],
        boto3_clients=mock_boto3_clients,
        operator='me',
        container_code='any_code',
        container_type='project',
        session_id='1234',
        auth_token='fake_token',
        network_origin='unknown',
    )
    with mock.patch.object(FileDownloadClient, 'set_status') as fake_set:
        await download_client.background_worker('fake_hash')
    fake_set.assert_called_with(EFileStatus.SUCCEED, payload={'hash_code': 'fake_hash'})


async def test_zip_worker_set_status_FAILED_when_success(
    httpx_mock, mock_boto3, mock_kafka_producer, mock_boto3_clients, mocker
):
    for x in ['geid_1', 'geid_2']:
        httpx_mock.add_response(
            method='GET',
            url=f'http://metadata_service/v1/item/{x}/',
            json={
                'result': {
                    'code': 'any_code',
                    'labels': 'any_label',
                    'storage': {'location_uri': 'http://anything.com/bucket/obj_path'},
                    'id': x,
                    'operator': 'me',
                    'parent_path': 'admin',
                    'type': 'file',
                    'container_code': 'fake_project_code',
                    'container_type': 'project',
                    'zone': 0,
                    'name': x,
                }
            },
        )

    m = mocker.patch(
        'common.object_storage_adaptor.boto3_client.Boto3Client.download_object',
        return_value={},
    )
    m.side_effect = Exception('fail to download')

    httpx_mock.add_response(method='POST', url='http://dataops_service/v2/resource/lock/bulk', json={}, status_code=200)
    httpx_mock.add_response(
        method='DELETE', url='http://dataops_service/v2/resource/lock/bulk', json={}, status_code=200
    )

    download_client = await create_file_download_client(
        files=[{'id': 'geid_1'}, {'id': 'geid_2'}],
        boto3_clients=mock_boto3_clients,
        operator='me',
        container_code='any_code',
        container_type='project',
        session_id='1234',
        auth_token='fake_token',
        network_origin='unknown',
    )

    try:
        with mock.patch.object(FileDownloadClient, 'set_status') as fake_set:
            await download_client.background_worker('fake_hash')
    except Exception as e:
        assert str(e) == 'fail to download'

    fake_set.assert_called_with(EFileStatus.FAILED, payload={'error_msg': 'fail to download'})


@pytest.mark.parametrize(
    'exception_code,result',
    [
        (
            'any',
            {
                'status': EFileStatus.FAILED,
                'payload': {
                    'error_msg': (
                        'S3 operation failed; code: any, message: any msg'
                        ', resource: any, request_id: any, host_id: any'
                    )
                },
            },
        ),
        (
            'NoSuchKey',
            {
                'status': EFileStatus.FAILED,
                'payload': {
                    'error_msg': (
                        'S3 operation failed; code: NoSuchKey, message: any msg'
                        ', resource: any, request_id: any, host_id: any'
                    )
                },
            },
        ),
    ],
)
async def test_zip_worker_raise_exception_when_minio_return_error(
    mock_boto3, httpx_mock, exception_code, result, mocker, mock_boto3_clients
):
    for x in ['geid_1', 'geid_2']:
        httpx_mock.add_response(
            method='GET',
            url=f'http://metadata_service/v1/item/{x}/',
            json={
                'result': {
                    'code': 'any_code',
                    'labels': 'any_label',
                    'storage': {'location_uri': 'http://anything.com/bucket/obj_path'},
                    'id': x,
                    'operator': 'me',
                    'parent_path': 'admin',
                    'type': 'file',
                    'container_code': 'fake_project_code',
                    'container_type': 'project',
                    'zone': 0,
                    'name': x,
                }
            },
        )

    m = mocker.patch('common.object_storage_adaptor.boto3_client.Boto3Client.download_object', return_value=[])
    m.side_effect = minio.error.S3Error(
        code=exception_code, message='any msg', resource='any', request_id='any', host_id='any', response='error'
    )

    httpx_mock.add_response(method='POST', url='http://dataops_service/v2/resource/lock/bulk', json={}, status_code=200)
    httpx_mock.add_response(
        method='DELETE', url='http://dataops_service/v2/resource/lock/bulk', json={}, status_code=200
    )

    download_client = await create_file_download_client(
        files=[{'id': 'geid_1'}, {'id': 'geid_2'}],
        boto3_clients=mock_boto3_clients,
        operator='me',
        container_code='any_code',
        container_type='project',
        session_id='1234',
        auth_token='fake_token',
        network_origin='unknown',
    )

    try:
        with mock.patch.object(FileDownloadClient, 'set_status') as fake_set:
            await download_client.background_worker('fake_hash')
    except Exception as e:
        assert str(e) == result['payload']['error_msg']

    fake_set.assert_called_with(result['status'], payload=result['payload'])
