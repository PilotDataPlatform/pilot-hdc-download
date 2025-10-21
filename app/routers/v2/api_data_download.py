# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import asyncio

import httpx
from common import ProjectClient
from common import ProjectNotFoundException
from common import get_boto3_client
from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import Header
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi_utils import cbv

from app.commons.download_manager.dataset_download_manager import create_dataset_download_client
from app.commons.download_manager.file_download_manager import EmptyFolderError
from app.commons.download_manager.file_download_manager import InvalidEntityType
from app.commons.download_manager.file_download_manager import create_file_download_client
from app.components.request.network import Network
from app.config import ConfigClass
from app.logger import logger
from app.models.base_models import APIResponse
from app.models.base_models import EAPIResponseCode
from app.models.models_data_download import DatasetPrePOST
from app.models.models_data_download import EFileStatus
from app.models.models_data_download import PreDataDownloadPOST
from app.models.models_data_download import PreDataDownloadResponse
from app.resources.error_handler import catch_internal
from app.resources.helpers import ResourceNotFound

router = APIRouter()

_API_TAG = 'v2/data-download'
_API_NAMESPACE = 'api_data_download'


def get_network(request: Request) -> Network:
    """Get network from the request headers."""

    return Network.from_headers(request.headers)


@cbv.cbv(router)
class APIDataDownload:
    """API Data Download Class."""

    def __init__(self):
        self.project_client = ProjectClient(ConfigClass.PROJECT_SERVICE, ConfigClass.REDIS_URL)
        self.boto3_clients = self._connect_to_object_storage()

    def _connect_to_object_storage(self):
        """
        Summary:
            Setup the two connection class:
                - boto3_internal: use private domain
                - boto3_public: use public domain
        """
        loop = asyncio.new_event_loop()

        logger.info('Initialize the boto3 clients')
        try:
            boto3_internal = loop.run_until_complete(
                get_boto3_client(
                    ConfigClass.S3_INTERNAL,
                    access_key=ConfigClass.S3_ACCESS_KEY,
                    secret_key=ConfigClass.S3_SECRET_KEY,
                    https=ConfigClass.S3_INTERNAL_HTTPS,
                )
            )

            boto3_public = loop.run_until_complete(
                get_boto3_client(
                    ConfigClass.S3_PUBLIC,
                    access_key=ConfigClass.S3_ACCESS_KEY,
                    secret_key=ConfigClass.S3_SECRET_KEY,
                    https=ConfigClass.S3_PUBLIC_HTTPS,
                )
            )
        except Exception:
            logger.exception('Fail to create connection with boto3')
            raise

        loop.close()
        return {'boto3_internal': boto3_internal, 'boto3_public': boto3_public}

    @router.post(
        '/download/pre/',
        tags=[_API_TAG],
        response_model=PreDataDownloadResponse,
        summary='Pre download process, zip as a package if more than 1 file, '
        'used in project files download and dataset single file download.',
    )
    @catch_internal(_API_NAMESPACE)
    async def data_pre_download(
        self,
        data: PreDataDownloadPOST,
        background_tasks: BackgroundTasks,
        session_id=Header(None),
        Authorization=Header(),
        network: Network = Depends(get_network),
    ) -> JSONResponse:
        """
        Summary:
            The API serves as the pre file download operation. Since the file
            downloading is a background job, this api will download target
            files and zip them under the tmp folder.

            Afterwards, the frontend will all the /v1/downlaod/<hashcode> to
            download the zipped file or a single file

        Payload:
             - files(list): the list of target id file will be
                downloaded (either in project or dataset)
             - operator(str): the user who takes the operation
             - container_code(str): the unique code of project
             - container_type(str): the type of container will be project/dataset
             - approval_request_id(UUID): the unique identifier for approval

        Header:
             - authorization(str): the access token from auth service
             - refresh_token(str): the refresh token from auth service
        Cookies:
             - session_id(str): the session id generate for each user login

        Return:
            - 200
        """

        logger.info('Receiving request on "/download/pre/".')
        response = APIResponse()
        auth_token = Authorization.replace('Bearer ', '')

        logger.info(f'Check container: {data.container_type} {data.container_code}.')
        try:
            if data.container_type == 'project':
                _ = await self.project_client.get(code=data.container_code)
            elif data.container_type == 'dataset':
                node_query_url = ConfigClass.DATASET_SERVICE + 'datasets/' + data.container_code
                with httpx.Client() as client:
                    dataset_response = client.get(node_query_url)
                if dataset_response.status_code != 200:
                    raise Exception('Fetch dataset error: %s', dataset_response.json())

        except ProjectNotFoundException as e:
            response.error_msg = e.error_msg
            response.code = EAPIResponseCode.not_found
            return response.json_response()

        try:
            logger.info('Initialize the data download client')
            download_client = await create_file_download_client(
                data.files,
                self.boto3_clients,
                data.operator,
                data.container_code,
                data.container_type,
                session_id,
                auth_token,
                network.origin,
            )

            logger.info('generate hash token')
            hash_code = await download_client.generate_hash_code()

            logger.info('Init the download job status')
            status_result = await download_client.set_status(EFileStatus.WAITING, payload={'hash_code': hash_code})

            logger.info(
                f'Starting background job for: {data.container_code}.'
                f'number of files {len(download_client.files_to_zip)}'
            )
            background_tasks.add_task(download_client.background_worker, hash_code)

            response.result = status_result
            response.code = EAPIResponseCode.success
        except (EmptyFolderError, InvalidEntityType) as e:
            response.error_msg = str(e)
            response.code = EAPIResponseCode.bad_request
        except ResourceNotFound as e:
            response.error_msg = str(e)
            response.code = EAPIResponseCode.not_found
        except Exception as e:
            response.error_msg = str(e)
            response.code = EAPIResponseCode.internal_error

        logger.info(f'Sending response on "/download/pre/" with code {response.code}.')
        return response.json_response()

    @router.post('/dataset/download/pre', tags=[_API_TAG], summary='Download all files & schemas in a dataset')
    @catch_internal(_API_NAMESPACE)
    async def dataset_pre_download(
        self,
        data: DatasetPrePOST,
        background_tasks: BackgroundTasks,
        session_id=Header(None),
        Authorization=Header(),
        network: Network = Depends(get_network),
    ) -> JSONResponse:
        """
        Summary:
            The API serves as the pre download for whole dataset. All files
            and schemas will be download and packed as zip file under tmp folder.

            Afterwards, the frontend will all the /v1/downlaod/<hashcode> to
            download the zipped file or a single file

        Payload:
            - dataset_code(list): the unique code of dataset
            - operator(str): the user who takes the operation

        Header:
             - authorization(str): the access token from auth service
             - refresh_token(str): the refresh token from auth service
        Cookies:
             - session_id(str): the session id generate for each user login

        Return:
            - 200
        """

        logger.info('Receiving request on "/dataset/download/pre".')
        api_response = APIResponse()
        auth_token = Authorization.replace('Bearer ', '')

        node_query_url = ConfigClass.DATASET_SERVICE + 'datasets/' + data.dataset_code
        with httpx.Client() as client:
            response = client.get(node_query_url)
        dataset_id = response.json().get('id')

        logger.info('Initialize the dataset download client')
        download_client = await create_dataset_download_client(
            self.boto3_clients,
            data.operator,
            data.dataset_code,
            dataset_id,
            'dataset',
            session_id,
            auth_token,
            network.origin,
        )
        hash_code = await download_client.generate_hash_code()
        status_result = await download_client.set_status(EFileStatus.WAITING, payload={'hash_code': hash_code})
        logger.info(
            f'Starting background job for: {data.dataset_code}.' f'number of files {len(download_client.files_to_zip)}'
        )
        background_tasks.add_task(download_client.background_worker, hash_code)

        api_response.result = status_result
        api_response.code = EAPIResponseCode.success

        logger.info(f'Sending response on "/dataset/download/pre" with code {api_response.code}.')
        return api_response.json_response()
