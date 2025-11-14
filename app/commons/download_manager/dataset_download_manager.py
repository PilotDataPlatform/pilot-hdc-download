# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import json
from datetime import datetime
from datetime import timezone

import aiofiles.os
import httpx
from common.object_storage_adaptor.boto3_client import Boto3Client

from app.commons.download_manager.file_download_manager import FileDownloadClient
from app.commons.kafka_producer import get_kafka_producer
from app.config import ConfigClass
from app.logger import logger
from app.models.models_data_download import EFileStatus
from app.resources.download_token_manager import generate_token
from app.resources.helpers import get_files_folder_recursive

DATASET_MESSAGE_SCHEMA = 'dataset.activity.avsc'


async def create_dataset_download_client(
    boto3_clients: dict[str, Boto3Client],
    operator: str,
    container_code: str,
    container_id: str,
    container_type: str,
    session_id: str,
    auth_token: str,
    network_origin: str,
):
    """
    Summary:
        The function will create the DatasetDownloadClient object asynchronously.
        also it will call the DatasetDownloadClient.add_files_to_list to prepare
        the files for downloading.

        Note: this class is different with FileDownloadClient, which allows the
        empty file/folder

    Parameter:
        - auth_token(dict of str pairs): the auth/refresh token to access minio
        - operator(string): the user who takes the operation
        - container_code(string): the unique code for project/dataset
        - container_type(string): the type will be dataset or project
        - session_id(string): the unique id to track the user login session
        - auth_token(string): the jwt token from keycloak
        - network_origin(string): the network origin of the request

    Return:
        - DatasetDownloadClient
    """

    download_client = DatasetDownloadClient(
        operator=operator,
        container_code=container_code,
        container_id=container_id,
        container_type=container_type,
        session_id=session_id,
        auth_token=auth_token,
        network_origin=network_origin,
    )

    await download_client.add_files_to_list(container_code)
    await download_client._set_connection(boto3_clients.get('boto3_internal'))

    return download_client


class DatasetDownloadClient(FileDownloadClient):
    def __init__(
        self,
        operator: str,
        container_code: str,
        container_id: str,
        container_type: str,
        session_id: str,
        auth_token: str,
        network_origin: str,
    ):
        super().__init__(
            operator,
            container_code,
            container_type,
            session_id,
            auth_token,
            network_origin,
        )

        self.container_id = container_id

    async def _set_connection(self, boto3_client: Boto3Client):
        """
        Summary:
            The dataset connection will be alway private domain
        """

        self.boto3_client = boto3_client

        return

    async def add_schemas(self, dataset_geid: str) -> None:
        """
        Summary:
            The function will call the dataset shema api to get detail of schemas.
            and then saves schema json files to folder that will zipped.

        Parameter:
            - dataset_geid(str): the identifier of dataset

        Return:
            - None
        """

        try:
            if not await aiofiles.os.path.isdir(self.tmp_folder):
                await aiofiles.os.mkdir(self.tmp_folder)
                await aiofiles.os.mkdir(self.tmp_folder + '/data')

            payload = {
                'dataset_geid': dataset_geid,
                'standard': 'default',
                'is_draft': False,
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(ConfigClass.DATASET_SERVICE + 'schema/list', json=payload)
            for schema in response.json()['result']:
                with open(self.tmp_folder + '/default_' + schema['name'], 'w') as w:
                    w.write(json.dumps(schema['content'], indent=4, ensure_ascii=False))

            payload = {
                'dataset_geid': dataset_geid,
                'standard': 'open_minds',
                'is_draft': False,
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(ConfigClass.DATASET_SERVICE + 'schema/list', json=payload)
            for schema in response.json()['result']:
                with open(self.tmp_folder + '/openMINDS_' + schema['name'], 'w') as w:
                    w.write(json.dumps(schema['content'], indent=4, ensure_ascii=False))
        except Exception:
            logger.exception('Fail to create schemas')
            raise

    async def generate_hash_code(self) -> str:
        """
        Summary:
            The function will create the hashcode for download api.

        Return:
            - str: hash code
        """

        self.result_file_name = self.tmp_folder + '.zip'

        return await generate_token(
            self.container_code,
            self.container_type,
            self.result_file_name,
            self.operator,
            self.session_id,
            self.job_id,
        )

    async def update_activity_log(self) -> None:
        """
        Summary:
            The function will create activity log for dataset file download
            ONLY. this file download will send to item activity log index

        Return:
            - dict: http reponse
        """

        kp = await get_kafka_producer()

        message = {
            'activity_type': 'download',
            'activity_time': datetime.now(tz=timezone.utc),
            'container_code': self.container_code,
            'version': None,
            'target_name': self.result_file_name,
            'user': self.operator,
            'changes': [],
            'network_origin': self.network_origin,
        }

        await kp.create_activity_log(
            message,
            DATASET_MESSAGE_SCHEMA,
            ConfigClass.KAFKA_DATASET_ACTIVITY_TOPIC,
        )

    async def add_files_to_list(self, dataset_code):
        """
        Summary:
            The function will add the file/folder with input geid into list.
            It is slightly different with file download. The dataset download
            will try to query ALL the file/folders under the target dataset.

        Parameter:
            - dataset_code(str): the unique code of dataset

        Return:
            - None
        """

        folder_tree = await get_files_folder_recursive(
            dataset_code,
            'dataset',
            '',
            self.auth_token,
            zone=1,
        )
        for x in folder_tree:
            x.update({'location': x.get('storage', {}).get('location_uri')})
            self.files_to_zip.append(x)

    async def background_worker(self, hash_code: str) -> None:
        """
        Summary:
            The function is the core of the object. this is a background job and
            will be trigger by api. Funtion will make following actions:
                - download all files in the file_to_zip
                - download all schemas under dataset
                - zip files/schemas into a zip file
                - create the activity logs for dataset

        Parameter:
            - hash_code(str): the hash code for downloading

        Return:
            - dict: None
        """

        logger.info(f'Starting background worker for dataset download with job id {self.job_id}.')

        await self.set_status(EFileStatus.RUNNING, payload={'hash_code': hash_code})

        await self._file_download_worker(hash_code)

        await self.add_schemas(self.container_id)

        await self._zip_worker()

        await self.set_status(EFileStatus.SUCCEED, payload={'hash_code': hash_code})

        await self.update_activity_log()

        logger.audit(
            'Successfully prepared dataset files for download.',
            container_code=self.container_code,
            container_type=self.container_type,
            username=self.operator,
            job_id=self.job_id,
        )

        logger.info(f'Finished background worker for dataset download with job id {self.job_id}.')

        return None
