# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import asyncio
import os
import shutil
import time
import uuid
from datetime import datetime
from datetime import timezone
from typing import Any

from common.object_storage_adaptor.boto3_client import Boto3Client
from starlette.concurrency import run_in_threadpool

from app.commons.kafka_producer import get_kafka_producer
from app.commons.locks import bulk_lock_operation
from app.config import ConfigClass
from app.logger import logger
from app.models.models_data_download import EFileStatus
from app.resources.download_token_manager import generate_token
from app.resources.helpers import get_files_folder_by_id
from app.resources.helpers import get_files_folder_recursive
from app.resources.helpers import set_status

ITEM_MESSAGE_SCHEMA = 'metadata.items.activity.avsc'


class EmptyFolderError(Exception):
    pass


class InvalidEntityType(Exception):
    pass


async def create_file_download_client(
    files: list[dict[str, Any]],
    boto3_clients: dict[str, Boto3Client],
    operator: str,
    container_code: str,
    container_type: str,
    session_id: str,
    auth_token: str,
    network_origin: str,
):
    """
    Summary:
        The function will create the FileDownloadClient object asynchronously.
        also it will call the FileDownloadClient.add_files_to_list to prepare
        the info for downloading.

        If there is no file to be added (some empty forlder). The function will
        raise error.

    Parameter:
        - files(list): the list of file will be added into object
        - boto3_clients(dict of Boto3Client):
            - boto3_internal: the instance of boto3client with private domain
            - boto3_public: the instance of boto3client with public domain
        - operator(string): the user who takes the operation
        - container_code(string): the unique code for project/dataset
        - container_type(string): the type will be dataset or project
        - session_id(string): the unique id to track the user login session
        - auth_token(string): the jwt token from keycloak
        - network_origin(string): the network origin of the request

    Return:
        - FileDownloadClient
    """
    download_client = FileDownloadClient(
        operator=operator,
        container_code=container_code,
        container_type=container_type,
        session_id=session_id,
        auth_token=auth_token,
        network_origin=network_origin,
    )

    for file in files:
        await download_client.add_files_to_list(file['id'])

    await download_client._set_connection(boto3_clients)

    if len(download_client.files_to_zip) < 1:
        error_msg = 'Invalid file amount: number of file must greater than 0'
        logger.error(error_msg)
        raise EmptyFolderError(error_msg)

    return download_client


class FileDownloadClient:
    def __init__(
        self,
        operator: str,
        container_code: str,
        container_type: str,
        session_id: str,
        auth_token: str,
        network_origin: str,
    ):
        self.job_id = str(uuid.uuid4())
        self.job_status = EFileStatus.WAITING
        self.files_to_zip = []
        self.operator = operator
        self.container_code = container_code
        self.tmp_folder = ConfigClass.MINIO_TMP_PATH + container_type + container_code + '_' + str(time.time())
        self.result_file_name = ''
        self.auth_token = auth_token
        self.session_id = session_id
        self.container_type = container_type
        self.network_origin = network_origin

        self.folder_download = False

        self.boto3_client = None

    async def _set_connection(self, boto3_clients: dict[str, Boto3Client]):
        """
        Summary:
            if number of file is 1 without any folder, the boto3_client
            will use the instance with private domain. Otherwise, it will
            use the public domain
        Parameter:
            - boto3_clients(dict of Boto3Client):
                - boto3_internal: the instance of boto3client with private domain
                - boto3_public: the instance of boto3client with public domain
        """

        if self.folder_download or len(self.files_to_zip) > 1:
            self.boto3_client = boto3_clients.get('boto3_internal')
        else:
            self.boto3_client = boto3_clients.get('boto3_public')

        return

    async def _parse_object_location(self, location: str) -> tuple[str, str]:
        """
        Summary:
            The function will parse out the object location and return
            the bucket & object path

        Parameter:
            - location(str): the object location from metadata. The format
            of location will be:
                <http or https>://<storage_endpoint>/<bucket>/<object_path>

        Return:
            - bucket: the bucket in the storage
            - object_path: the path for the object
        """
        object_path = location.split('//')[-1]
        _, bucket, obj_path = tuple(object_path.split('/', 2))

        return bucket, obj_path

    async def set_status(self, status: EFileStatus, payload: dict):
        """
        Summary:
            The function will set the job status for current object in
            redis

        Parameter:
            - status(EFileStatus): the job status
            - payload(dict): the extra infomation
                - hash_code: the jwt token that contains download info

        Return:
            - dict: detail job info
        """
        if len(self.files_to_zip) > 0:
            download_file = self.files_to_zip[0]
            payload.update({'zone': download_file.get('zone')})

        target_name = self.result_file_name.split('/')[-1]
        if self.container_code:
            target_name = f'{self.container_code}/{target_name}'
        if self.operator:
            target_name = f'{self.operator}/{target_name}'
        job_status = await set_status(
            session_id=self.session_id,
            target_names=[target_name],
            container_code=self.container_code,
            container_type=self.container_type,
            status=status,
            job_id=self.job_id,
        )
        job_status.update({'payload': payload})

        return job_status

    async def add_files_to_list(self, _id: str) -> None:
        """
        Summary:
            The function will add the file/folder with input _id into list.
            if input _id points to a folder then it will call the metadata
            api to get ALL files under it and its subfolders

        Parameter:
            - _id(str): the uuid of file/folder

        Return:
            - None
        """
        ff_object = await get_files_folder_by_id(_id)
        ff_type = ff_object.get('type')

        file_list = []
        if 'folder' == ff_type:
            logger.info(f'Getting folder from geid: {_id}')

            self.folder_download = True

            if ff_object.get('parent_path'):
                parent_path = ff_object.get('parent_path') + '/' + ff_object.get('name')
            else:
                parent_path = ff_object.get('name')

            folder_tree = await get_files_folder_recursive(
                self.container_code,
                self.container_type,
                ff_object.get('owner'),
                self.auth_token,
                zone=ff_object.get('zone'),
                parent_path=parent_path,
            )

            file_list = folder_tree

        elif 'file' == ff_type:
            file_list = [ff_object]
        else:
            raise InvalidEntityType(f'Cannot download entity with type {ff_type}')

        for file in file_list:
            file.update({'location': file.get('storage', {}).get('location_uri')})
            if file.get('parent_path') is None:
                file.update({'parent_path': ''})
            self.files_to_zip.append(file)

        return None

    async def generate_hash_code(self) -> str:
        """
        Summary:
            The function will create the hashcode for download api.
            In the funtion will check if user download single file
            OR multiple files to generate the file_path differently

        Return:
            - str: hash code
        """

        if self.folder_download or len(self.files_to_zip) > 1:
            download_file = self.tmp_folder + '.zip'
            self.result_file_name = self.tmp_folder + '.zip'
        else:
            bucket, file_path = await self._parse_object_location(self.files_to_zip[0].get('location'))
            download_file = await self.boto3_client.get_download_presigned_url(bucket, file_path)
            self.result_file_name = file_path

        return await generate_token(
            self.container_code,
            self.container_type,
            download_file,
            self.operator,
            self.session_id,
            self.job_id,
        )

    async def _file_download_worker(self, hash_code: str) -> None:
        """
        Summary:
            The function will download all the file that has been added
            into the list to tmp folder. Before downloading the file, the
            function will lock ALL of them. After downloading, it will
            set the job status to finish.

        Parameter:
            - hash_code(str): the hashcode

        Return:
            - None
        """

        lock_keys = []
        try:
            bucket_prefix = 'gr-' if ConfigClass.namespace == 'greenroom' else 'core-'
            for nodes in self.files_to_zip:
                if self.container_type == 'project':
                    bucket = bucket_prefix + nodes.get('container_code')
                else:
                    bucket = nodes.get('container_code')
                lock_keys.append(f'{bucket}/{nodes.get("parent_path")}/{nodes.get("name")}')
            await bulk_lock_operation(lock_keys, 'read')

            for obj in self.files_to_zip:
                bucket, obj_path = await self._parse_object_location(obj.get('location'))
                await self.boto3_client.download_object(bucket, obj_path, self.tmp_folder + '/' + obj_path)

        except Exception as e:
            logger.error(f'Error in background job: {e}')
            payload = {'error_msg': str(e)}
            await self.set_status(EFileStatus.FAILED, payload=payload)
            raise Exception(str(e))
        finally:
            logger.info('Start to unlock the nodes')
            await bulk_lock_operation(lock_keys, 'read', lock=False)

        logger.info('BACKGROUND TASK DONE')

        return None

    async def update_activity_log(self) -> dict:
        """
        Summary:
            The function will create activity log for dataset file download
            ONLY. this file download will send to item activity log index

        Return:
            - dict: http reponse
        """

        kp = await get_kafka_producer()

        source_node = self.files_to_zip[0]
        if len(self.files_to_zip) != 1:
            source_node.update({'id': None, 'name': os.path.basename(self.result_file_name)})

        message = {
            'activity_type': 'download',
            'activity_time': datetime.now(tz=timezone.utc),
            'item_id': source_node.get('id'),
            'item_type': source_node.get('type'),
            'item_name': source_node.get('name'),
            'item_parent_path': source_node.get('parent_path'),
            'container_code': source_node.get('container_code'),
            'container_type': source_node.get('container_type'),
            'zone': source_node.get('zone'),
            'user': self.operator,
            'imported_from': '',
            'changes': [],
            'network_origin': self.network_origin,
        }

        await kp.create_activity_log(
            message,
            ITEM_MESSAGE_SCHEMA,
            ConfigClass.KAFKA_ITEM_ACTIVITY_TOPIC,
        )

        return

    async def _zip_worker(self):
        """
        Summary:
            The function will zip the files under the tmp folder.

        Return:
            - None
        """

        logger.info('Start to ZIP files')
        await run_in_threadpool(shutil.make_archive, self.tmp_folder, 'zip', self.tmp_folder)

        return None

    async def background_worker(self, hash_code: str) -> None:
        """
        Summary:
            The function is the core of the object. this is a background job and
            will be trigger by api. Funtion will download all file in the file_to_zip
            list and zip them together

        Parameter:
            - hash_code(str): the hash code for downloading

        Return:
            - None
        """

        logger.info(f'Starting background worker for file download with job id {self.job_id}.')

        await self.set_status(EFileStatus.RUNNING, payload={'hash_code': hash_code})

        if self.folder_download or len(self.files_to_zip) > 1:
            await self._file_download_worker(hash_code)
            await self._zip_worker()
        else:
            await asyncio.sleep(2)  # simulate some delay for single file for debugging purpose

        await self.set_status(EFileStatus.SUCCEED, payload={'hash_code': hash_code})

        await self.update_activity_log()

        logger.info(f'Finished background worker for file download with job id {self.job_id}.')

        return None
