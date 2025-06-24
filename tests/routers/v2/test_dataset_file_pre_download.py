# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.


async def test_v2_dataset_download_pre_return_200_when_success(
    client, httpx_mock, mock_boto3, mocker, mock_kafka_producer
):
    dataset_code = 'fake_project_code'

    httpx_mock.add_response(
        method='GET',
        url='http://dataset_service/v1/datasets/' + dataset_code,
        status_code=200,
        json={'result': {'id': 'fake_id'}},
    )

    httpx_mock.add_response(
        method='GET',
        url='http://metadata_service/v1/items/search/?container_code=fake_project_code&'
        'container_type=dataset&zone=1&recursive=true&status=ACTIVE&parent_path=&owner=&'
        'type=file&page_size=100000',
        json={
            'result': [
                {
                    'storage': {'location_uri': 'http://anything.com/bucket/obj_path'},
                    'id': 'fake_geid',
                    'operator': 'me',
                    'parent_path': 'admin',
                    'type': 'file',
                    'container_code': 'fake_project_code',
                    'container_type': 'dataset',
                    'zone': 0,
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
                'container_code': 'test_dataset',
                'container_type': 'dataset',
                'action_type': 'data_download',
                'status': 'WAITING',
                'job_id': '3fa85f64-5717-4562-b3fc-2c963f66afa6',
            }
        },
        status_code=200,
    )

    httpx_mock.add_response(method='POST', url='http://dataops_service/v2/resource/lock/bulk', json={}, status_code=200)
    httpx_mock.add_response(
        method='DELETE', url='http://dataops_service/v2/resource/lock/bulk', json={}, status_code=200
    )

    mocker.patch(
        'app.commons.download_manager.dataset_download_manager.DatasetDownloadClient.add_schemas', return_value=[]
    )
    mocker.patch(
        'app.commons.download_manager.dataset_download_manager.DatasetDownloadClient._zip_worker', return_value=[]
    )

    resp = await client.post(
        '/v2/dataset/download/pre',
        headers={'Session-Id': 'me-13404d2e-e0a7-46cb-861e-df786a3923a8', 'Authorization': 'Bearer fake_token'},
        json={'operator': 'me', 'dataset_code': dataset_code},
    )

    assert resp.status_code == 200
    result = resp.json()['result']
    assert result['session_id'] == 'me-13404d2e-e0a7-46cb-861e-df786a3923a8'
    assert result['target_type'] == 'file'
    assert result['container_code'] == dataset_code
    assert result['container_type'] == 'dataset'
    assert result['action_type'] == 'data_download'
    assert result['status'] == 'WAITING'
    assert result['job_id']
    assert result['payload']['hash_code']


async def test_v2_dataset_download_pre_empty_dataset_return_200_when_success(
    client, httpx_mock, mock_boto3, mocker, mock_kafka_producer
):
    dataset_code = 'fake_project_code'

    httpx_mock.add_response(
        method='GET',
        url='http://dataset_service/v1/datasets/' + dataset_code,
        status_code=200,
        json={'result': {'id': 'fake_id'}},
    )

    httpx_mock.add_response(
        method='GET',
        url='http://metadata_service/v1/items/search/?container_code=fake_project_code'
        '&container_type=dataset&zone=1&recursive=true&status=ACTIVE&parent_path=&owner=&'
        'type=file&page_size=100000',
        json={'result': []},
    )

    httpx_mock.add_response(
        method='POST',
        url='http://dataops_service/v1/task-stream/',
        json={
            'stream_info': {
                'session_id': 'admin-3fa85f64-5717-4562-b3fc-2c963f66afa6',
                'target_names': ['file_1.txt', 'file_2.txt'],
                'target_type': 'batch',
                'container_code': 'test_dataset',
                'container_type': 'dataset',
                'action_type': 'data_download',
                'status': 'WAITING',
                'job_id': '3fa85f64-5717-4562-b3fc-2c963f66afa6',
            }
        },
        status_code=200,
    )

    httpx_mock.add_response(method='POST', url='http://dataops_service/v2/resource/lock/bulk', json={}, status_code=200)
    httpx_mock.add_response(
        method='DELETE', url='http://dataops_service/v2/resource/lock/bulk', json={}, status_code=200
    )

    mocker.patch(
        'app.commons.download_manager.dataset_download_manager.DatasetDownloadClient.add_schemas', return_value=[]
    )
    mocker.patch(
        'app.commons.download_manager.dataset_download_manager.DatasetDownloadClient._zip_worker', return_value=[]
    )

    resp = await client.post(
        '/v2/dataset/download/pre',
        headers={'Session-Id': 'me-13404d2e-e0a7-46cb-861e-df786a3923a8', 'Authorization': 'Bearer fake_token'},
        json={'operator': 'me', 'dataset_code': dataset_code},
    )

    assert resp.status_code == 200
    result = resp.json()['result']
    assert result['session_id'] == 'me-13404d2e-e0a7-46cb-861e-df786a3923a8'
    assert dataset_code in result['target_names'][0]
    assert result['target_type'] == 'file'
    assert result['container_code'] == dataset_code
    assert result['container_type'] == 'dataset'
    assert result['action_type'] == 'data_download'
    assert result['status'] == 'WAITING'
    assert result['job_id']
    assert result['payload']['hash_code']
