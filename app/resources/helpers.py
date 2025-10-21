# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from uuid import UUID

import httpx

from app.config import ConfigClass
from app.logger import logger
from app.models.base_models import EAPIResponseCode
from app.models.models_data_download import EFileStatus
from app.models.models_item import ItemStatus


class ResourceNotFound(Exception):
    pass


async def get_files_folder_recursive(
    container_code: str, container_type: str, owner: str, auth_token: str, zone: int = 0, parent_path: str = ''
) -> list[dict]:
    """
    Summary:
        The function will call the api into metadata service and fetch
        the file/folder object match the parameters recursively.

    Parameter:
        - container_code(str): the code of container
        - container_type(string): the type can project or dataset
        - owner(str): the owner of file/object
        - auth_token(string): the jwt token from keycloak to access metadata service
        - zone(int) default=0: 0 for greenroom, 1 for core
        - parent_path(str) default='': the parent folder path of target file/folder

    Return:
        - list: the list of file/folder meatch the searching parameter
    """

    payload = {
        'container_code': container_code,
        'container_type': container_type,
        'zone': zone,
        'recursive': True,
        'status': ItemStatus.ACTIVE,
        'parent_path': parent_path,
        'owner': owner,
        'type': 'file',
        'page_size': 100000,
    }

    url = ConfigClass.METADATA_SERVICE + 'items/search/'
    async with httpx.AsyncClient() as client:
        headers = {'Authorization': f'Bearer {auth_token}'}
        res = await client.get(url, params=payload, headers=headers)
        if res.status_code != 200:
            raise Exception(f'Error when query the folder tree {res.text}')

    return res.json().get('result', [])


async def get_files_folder_by_id(_id: UUID) -> dict:
    """
    Summary:
        The function will call the api into metadata service and fetch
        the file/folder object by item.

    Parameter:
        - _id(str): uuid of the file/folder

    Return:
        - dict: the detail info of item with target id
    """

    url = ConfigClass.METADATA_SERVICE + f'item/{_id}/'
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
    file_folder_object = res.json().get('result', {})

    if len(file_folder_object) == 0 or res.status_code == EAPIResponseCode.not_found:
        raise ResourceNotFound(f'resource {_id} does not exist')
    elif res.status_code != 200:
        raise Exception(f'Error when get resource: {res.text}')

    return file_folder_object


async def set_status(
    session_id: str,
    target_names: list[str],
    container_code: str,
    container_type: str,
    status: EFileStatus,
    job_id: str,
    target_type: str = 'file',
    action_type: str = 'data_download',
) -> dict:
    """
    Summary:
        This function will call the DataOps service and write into
        Redis the inputs as a download job status.

    Parameter:
        - target_names(list[str]): the source file of current action.
            if multiple files are involved in one action, the source
            will be a zip file.
        - container_code(str): the unique code of project/dataset.
        - container_type(str): project/dataset.
        - status(EFileStatus): job status; check EFileStatus object.
        - job_id(str): the job identifier for running action
        - session_id(str): the session id for current user
        - target_type(str): type of item.
        - action_type(str): type of action, in download service this
            will be marked as data_download.

    Return:
        - dict: the detail job info
    """

    task_url = ConfigClass.DATAOPS_SERVICE + 'task-stream/'
    payload = {
        'session_id': session_id,
        'target_names': target_names,
        'target_type': target_type,
        'container_code': container_code,
        'container_type': container_type,
        'action_type': action_type,
        'status': str(status),
        'job_id': job_id,
    }

    logger.info(f'Setting job id {job_id} status to {status}.')

    async with httpx.AsyncClient() as client:
        res = await client.request(method='POST', url=task_url, json=payload)
        if res.status_code != 200:
            raise Exception(f'Failed to write job status: {res.text}')

    logger.info(f'Successfully set job id {job_id} status to {status}.')

    return payload


async def get_status(
    session_id: str,
    container_code: str,
    container_type: str,
    action_type: str = 'data_download',
    target_names: list[str] = None,
    job_id: str = None,
) -> list[dict]:
    """
    Summary:
        The function will fetch the existing job from redis by the input.
        Return empty list if job does not exist

    Parameter:
        - session_id(str): the session id for current user
        - job_id(str): the job identifier for running action
        - project_code(str): the unique code of project
        - action(str): in download service this will be marked as data_download
        - operator(str) default=None: the user who takes current action

    Return:
        - dict: the detail job info
    """

    task_url = ConfigClass.DATAOPS_SERVICE + 'task-stream/static/'
    params = {
        'session_id': session_id,
        'container_code': container_code,
        'container_type': container_type,
        'action_type': action_type,
    }
    if target_names:
        params['target_names'] = target_names
    if job_id:
        params['job_id'] = job_id
    async with httpx.AsyncClient() as client:
        res = await client.get(url=task_url, params=params)

    if res.status_code == 404:
        return []
    elif res.status_code != 200:
        raise Exception(f'Fail to get job status: {res.text}')

    return res.json().get('stream_info')
