# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import enum
import traceback
from functools import wraps

from common import LoggerFactory

from app.config import ConfigClass
from app.models.base_models import APIResponse
from app.models.base_models import EAPIResponseCode

_logger = LoggerFactory(
    'internal_error',
    level_default=ConfigClass.LEVEL_DEFAULT,
    level_file=ConfigClass.LEVEL_FILE,
    level_stdout=ConfigClass.LEVEL_STDOUT,
    level_stderr=ConfigClass.LEVEL_STDERR,
).get_logger()


class APIException(Exception):
    def __init__(self, status_code: int, error_msg: str):
        self.status_code = status_code
        self.content = {
            'code': self.status_code,
            'error_msg': error_msg,
            'result': '',
        }


def catch_internal(api_namespace):
    """decorator to catch internal server error."""

    def decorator(func):
        @wraps(func)
        async def inner(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as exce:
                if type(exce) == APIException:
                    raise exce
                respon = APIResponse()
                respon.code = EAPIResponseCode.internal_error
                respon.result = None
                err = api_namespace + ' ' + str(exce)
                err_msg = customized_error_template(ECustomizedError.INTERNAL) % err
                _logger.error(traceback.format_exc())
                respon.error_msg = err_msg
                return respon.json_response()

        return inner

    return decorator


class ECustomizedError(enum.Enum):
    """Enum of customized errors."""

    FILE_NOT_FOUND = 'FILE_NOT_FOUND'
    INVALID_FILE_AMOUNT = 'INVALID_FILE_AMOUNT'
    JOB_NOT_FOUND = 'JOB_NOT_FOUND'
    FORGED_TOKEN = 'FORGED_TOKEN'
    TOKEN_EXPIRED = 'TOKEN_EXPIRED'
    INVALID_TOKEN = 'INVALID_TOKEN'
    INTERNAL = 'INTERNAL'


def customized_error_template(customized_error: ECustomizedError):
    """get error template."""
    return {
        'FILE_NOT_FOUND': '[File not found] %s.',
        'INVALID_FILE_AMOUNT': '[Invalid file amount] must greater than 0',
        'JOB_NOT_FOUND': '[Invalid Job ID] Not Found',
        'FORGED_TOKEN': '[Invalid Token] System detected forged token, \
                    a report has been submitted.',
        'TOKEN_EXPIRED': '[Invalid Token] Already expired.',
        'INVALID_TOKEN': '[Invalid Token] %s',
        'INTERNAL': '[Internal] %s',
    }.get(customized_error.name, 'Unknown Error')
