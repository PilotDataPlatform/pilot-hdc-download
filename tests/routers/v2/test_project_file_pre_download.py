# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import pytest
from common import ProjectNotFoundException

pytestmark = pytest.mark.asyncio


async def test_v2_download_pre_return_422_when_container_code_and_type_are_missing(client):
    resp = await client.post('/v2/download/pre/', json={'session_id': '123', 'operator': 'me', 'files': [{}]})

    assert resp.status_code == 422


async def test_v2_download_pre_return_404_when_project_not_exist(
    client,
    httpx_mock,
    mocker,
):

    m = mocker.patch('common.ProjectClient.get', return_value={})
    m.side_effect = ProjectNotFoundException

    resp = await client.post(
        '/v2/download/pre/',
        headers={'Session-Id': 'me-13404d2e-e0a7-46cb-861e-df786a3923a8', 'Authorization': 'Bearer fake_token'},
        json={
            'session_id': '123',
            'operator': 'me',
            'project_id': 'any',
            'container_code': 'fake_geid',
            'container_type': 'project',
            'files': [{'id': 'fake_geid'}],
        },
    )

    assert resp.status_code == 404
    assert resp.json() == {
        'code': 404,
        'error_msg': 'Project not found',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


async def test_v2_download_pre_return_404_when_fail_to_add_files_to_zip(
    client,
    httpx_mock,
    mocker,
):

    mocker.patch('common.ProjectClient.get', return_value={'any': 'any', 'global_entity_id': 'fake_global_entity_id'})

    httpx_mock.add_response(
        method='GET',
        url='http://metadata_service/v1/item/fake_geid/',
        json={},
        status_code=404,
    )

    resp = await client.post(
        '/v2/download/pre/',
        headers={'Session-Id': 'me-13404d2e-e0a7-46cb-861e-df786a3923a8', 'Authorization': 'Bearer fake_token'},
        json={
            'session_id': '123',
            'operator': 'me',
            'project_id': 'any',
            'container_code': 'fake_geid',
            'container_type': 'project',
            'files': [{'id': 'fake_geid'}],
        },
    )
    assert resp.status_code == 404
    assert resp.json() == {
        'code': 404,
        'error_msg': 'resource fake_geid does not exist',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


async def test_v2_download_pre_return_400_when_download_name_folder(
    client,
    httpx_mock,
    mocker,
):

    mocker.patch('common.ProjectClient.get', return_value={'any': 'any', 'global_entity_id': 'fake_global_entity_id'})

    httpx_mock.add_response(
        method='GET',
        url='http://metadata_service/v1/item/fake_geid/',
        json={
            'result': {
                'code': 'any_code',
                'labels': 'any_label',
                'storage': {'location_uri': 'http://anything.com/bucket/obj_path'},
                'id': 'fake_geid',
                'operator': 'me',
                'parent_path': 'admin',
                'type': 'name_folder',
                'container_code': 'fake_project_code',
                'container_type': 'project',
                'zone': 0,
                'name': 'test_item',
            }
        },
    )

    resp = await client.post(
        '/v2/download/pre/',
        headers={'Session-Id': 'me-13404d2e-e0a7-46cb-861e-df786a3923a8', 'Authorization': 'Bearer fake_token'},
        json={
            'session_id': '123',
            'operator': 'me',
            'project_id': 'any',
            'container_code': 'fake_global_entity_id',
            'container_type': 'project',
            'files': [{'id': 'fake_geid'}],
        },
    )

    assert resp.status_code == 400
    assert resp.json() == {
        'code': 400,
        'error_msg': 'Cannot download entity with type name_folder',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


async def test_v2_download_pre_return_200_when_approval_request_id(
    client,
    httpx_mock,
    mock_boto3,
    mocker,
    mock_kafka_producer,
):

    mocker.patch('common.ProjectClient.get', return_value={'any': 'any', 'global_entity_id': 'fake_global_entity_id'})

    httpx_mock.add_response(
        method='GET',
        url='http://metadata_service/v1/item/fake_geid/',
        json={
            'result': {
                'code': 'any_code',
                'labels': 'any_label',
                'storage': {'location_uri': 'http://anything.com/bucket/obj_path'},
                'id': 'fake_geid',
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

    resp = await client.post(
        '/v2/download/pre/',
        headers={'Session-Id': 'me-13404d2e-e0a7-46cb-861e-df786a3923a8', 'Authorization': 'Bearer fake_token'},
        json={
            'operator': 'me',
            'project_id': 'any',
            'container_code': 'fake_code',
            'container_type': 'project',
            'files': [{'id': 'fake_geid'}],
            'approval_request_id': '67e6bf62-be82-4401-9ec0-7d49ee047fe7',
        },
    )

    assert resp.status_code == 200
    result = resp.json()['result']
    assert result['session_id'] == 'me-13404d2e-e0a7-46cb-861e-df786a3923a8'
    assert 'obj_path' in result['target_names'][0]
    assert result['target_type'] == 'file'
    assert result['container_code'] == 'fake_code'
    assert result['container_type'] == 'project'
    assert result['action_type'] == 'data_download'
    assert result['status'] == 'WAITING'
    assert result['job_id']
    assert result['payload']['hash_code']


async def test_v2_download_pre_return_200_when_label_is_not_Folder(
    client,
    httpx_mock,
    mock_boto3,
    mocker,
    mock_kafka_producer,
):

    mocker.patch('common.ProjectClient.get', return_value={'any': 'any', 'global_entity_id': 'fake_global_entity_id'})

    httpx_mock.add_response(
        method='GET',
        url='http://metadata_service/v1/item/fake_geid/',
        json={
            'result': {
                'code': 'any_code',
                'labels': 'any_label',
                'storage': {'location_uri': 'http://anything.com/bucket/obj_path'},
                'id': 'fake_geid',
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

    resp = await client.post(
        '/v2/download/pre/',
        headers={'Session-Id': 'me-13404d2e-e0a7-46cb-861e-df786a3923a8', 'Authorization': 'Bearer fake_token'},
        json={
            'operator': 'me',
            'container_code': 'any_project_code',
            'container_type': 'project',
            'files': [{'id': 'fake_geid'}],
        },
    )

    assert resp.status_code == 200
    result = resp.json()['result']
    assert result['session_id'] == 'me-13404d2e-e0a7-46cb-861e-df786a3923a8'
    assert 'obj_path' in result['target_names'][0]
    assert result['target_type'] == 'file'
    assert result['container_code'] == 'any_project_code'
    assert result['container_type'] == 'project'
    assert result['action_type'] == 'data_download'
    assert result['status'] == 'WAITING'
    assert result['job_id']
    assert result['payload']['hash_code']


async def test_v2_download_pre_return_200_when_type_is_Folder(
    client,
    httpx_mock,
    mock_boto3,
    mocker,
    mock_kafka_producer,
):

    mocker.patch('common.ProjectClient.get', return_value={'any': 'any', 'global_entity_id': 'fake_global_entity_id'})

    httpx_mock.add_response(
        method='GET',
        url='http://metadata_service/v1/item/fake_geid/',
        json={
            'result': {
                'storage': {'location_uri': 'http://anything.com/bucket/obj_path'},
                'id': 'fake_geid',
                'type': 'folder',
                'owner': 'me',
                'parent_path': 'admin',
                'container_code': 'fake_project_code',
                'zone': 0,
                'name': 'fake_file',
            }
        },
    )

    container_code = 'fake_project_code'
    httpx_mock.add_response(
        method='GET',
        url='http://metadata_service/v1/items/search/?container_code=fake_project_code'
        '&container_type=project&zone=0&recursive=true&status=ACTIVE&parent_path=admi'
        'n%2Ffake_file&owner=me&type=file&page_size=100000',
        json={
            'result': [
                {
                    'storage': {'location_uri': f'http://anything.com/{container_code}/obj_path'},
                    'id': 'fake_geid',
                    'type': 'file',
                    'owner': 'me',
                    'parent_path': 'admin',
                    'container_code': container_code,
                    'container_type': 'project',
                    'zone': 0,
                    'name': 'test_item_2',
                }
            ]
        },
    )

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

    mocker.patch('app.commons.download_manager.file_download_manager.FileDownloadClient._zip_worker', return_value={})

    httpx_mock.add_response(method='POST', url='http://dataops_service/v2/resource/lock/bulk', json={}, status_code=200)
    httpx_mock.add_response(
        method='DELETE', url='http://dataops_service/v2/resource/lock/bulk', json={}, status_code=200
    )

    resp = await client.post(
        '/v2/download/pre/',
        headers={'Session-Id': 'me-13404d2e-e0a7-46cb-861e-df786a3923a8', 'Authorization': 'Bearer fake_token'},
        json={
            'operator': 'me',
            'project_id': 'any',
            'container_code': container_code,
            'container_type': 'project',
            'files': [{'id': 'fake_geid'}],
        },
    )

    assert resp.status_code == 200
    result = resp.json()['result']
    assert result['session_id'] == 'me-13404d2e-e0a7-46cb-861e-df786a3923a8'
    assert result['target_type'] == 'file'
    assert result['container_code'] == container_code
    assert result['container_type'] == 'project'
    assert result['action_type'] == 'data_download'
    assert result['status'] == 'WAITING'
    assert result['job_id']
    assert result['payload']['hash_code']
