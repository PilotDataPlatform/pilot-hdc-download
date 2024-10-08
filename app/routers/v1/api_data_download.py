# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import os

from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi.responses import RedirectResponse
from fastapi_utils import cbv
from jwt import ExpiredSignatureError
from jwt.exceptions import DecodeError

from app.config import ConfigClass
from app.logger import logger
from app.models.base_models import APIResponse
from app.models.base_models import EAPIResponseCode
from app.models.models_data_download import EFileStatus
from app.models.models_data_download import GetDataDownloadStatusResponse
from app.resources.download_token_manager import InvalidToken
from app.resources.download_token_manager import verify_download_token
from app.resources.error_handler import ECustomizedError
from app.resources.error_handler import catch_internal
from app.resources.error_handler import customized_error_template
from app.resources.helpers import get_status
from app.resources.helpers import set_status

router = APIRouter()

_API_TAG = 'v1/data-download'
_API_NAMESPACE = 'api_data_download'


@cbv.cbv(router)
class APIDataDownload:
    """API Data Download Class."""

    @router.get(
        '/download/status/{hash_code}',
        tags=[_API_TAG],
        response_model=GetDataDownloadStatusResponse,
        summary='Check download status',
    )
    @catch_internal(_API_NAMESPACE)
    async def data_download_status(self, hash_code):
        """
        Summary:
            The API is to return the download status by the hashcode

        Parameter:
            - hash_code(str): hashcode return from /v1/download/pre

        Return:
            - 200
        """

        response = APIResponse()

        logger.info('Recieving request on /download/status/{hash_code}')
        try:
            res_verify_token = await verify_download_token(hash_code)
        except ExpiredSignatureError as e:
            response.code = EAPIResponseCode.unauthorized
            response.error_msg = str(e)
            return response.json_response()
        except (DecodeError, InvalidToken) as e:
            response.code = EAPIResponseCode.bad_request
            response.error_msg = str(e)
            return response.json_response()
        except Exception as e:
            response.code = EAPIResponseCode.internal_error
            response.error_msg = str(e)
            return response.json_response()

        session_id = res_verify_token.get('session_id')
        job_id = res_verify_token.get('job_id')
        container_code = res_verify_token.get('container_code')
        container_type = res_verify_token.get('container_type')
        job_fetched = await get_status(
            session_id=session_id,
            container_code=container_code,
            container_type=container_type,
            job_id=job_id,
        )
        logger.info(f'job_fetched list: {job_fetched}')

        if len(job_fetched):
            response.code = EAPIResponseCode.success
            response.result = job_fetched[-1]
        else:
            logger.error(f'Status not found {res_verify_token} in namespace {ConfigClass.namespace}')
            response.code = EAPIResponseCode.not_found
            response.error_msg = customized_error_template(ECustomizedError.JOB_NOT_FOUND)

        return response.json_response()

    @router.get(
        '/download/{hash_code}',
        tags=[_API_TAG],
        summary='Download the data, asynchronously streams a file as the response.',
    )
    @catch_internal(_API_NAMESPACE)
    async def data_download(self, hash_code: str):
        """
        Summary:
            The API is the actual download api to send file to the frontend
            specified by hashcode

        Parameter:
            - hash_code(str): hashcode return from /v1/download/pre

        Return:
            - file response
        """

        logger.info('Recieving request on /download/{hash_code}')
        response = APIResponse()

        try:
            res_verify_token = await verify_download_token(hash_code)
        except ExpiredSignatureError as e:
            response.code = EAPIResponseCode.unauthorized
            response.error_msg = str(e)
            return response.json_response()
        except (DecodeError, InvalidToken) as e:
            response.code = EAPIResponseCode.bad_request
            response.error_msg = str(e)
            return response.json_response()
        except Exception as e:
            response.code = EAPIResponseCode.internal_error
            response.error_msg = str(e)
            return response.json_response()

        file_path = res_verify_token.get('file_path')
        if file_path.startswith('http'):
            response = RedirectResponse(file_path)
        else:
            if not os.path.exists(file_path):
                logger.error(f'File not found {file_path} in namespace {ConfigClass.namespace}')
                response.code = EAPIResponseCode.not_found
                response.error_msg = customized_error_template(ECustomizedError.FILE_NOT_FOUND) % file_path
                return response.json_response()

            filename = os.path.basename(file_path)
            response = FileResponse(path=file_path, filename=filename)

        target_name = file_path.split('/')[-1]
        if res_verify_token.get('container_code'):
            target_name = f'{res_verify_token.get("container_code")}/{target_name}'
        if res_verify_token.get('operator'):
            target_name = f'{res_verify_token.get("operator")}/{target_name}'
        _ = await set_status(
            session_id=res_verify_token.get('session_id'),
            target_names=[target_name],
            container_code=res_verify_token.get('container_code'),
            container_type=res_verify_token.get('container_type'),
            status=EFileStatus.SUCCEED,
            job_id=res_verify_token.get('job_id'),
        )

        logger.debug('Set the job status')

        return response
