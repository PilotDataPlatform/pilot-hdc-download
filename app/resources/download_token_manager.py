# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import time

import jwt

from app.config import ConfigClass


class InvalidToken(Exception):
    pass


async def verify_download_token(token: str) -> dict:
    """
    Summary:
        The function will decode the input token to retrieve the payload
        of file_path and return for download api. There will be two exception:
            - InvalidToken: missing the `file_path` field in payload.
            - jwt.ExpiredSignatureError: token expired

    Parameter:
        - token(string): the HS256 generate by `generate_token` function

    Return:
        - dict: the hash code
    """

    res = jwt.decode(token, ConfigClass.DOWNLOAD_KEY, algorithms=['HS256'])
    if 'file_path' not in res:
        raise InvalidToken('Invalid download token')

    return res


async def generate_token(
    container_code: str,
    container_type: str,
    file_path: str,
    operator: str,
    session_id: str,
    job_id: str,
    payload: dict = None,
) -> str:
    """
    Summary:
        The function will generate the hash code with specific download key
        by using HS256 encoding. All the parameter will be embedded into hash
        code for future verification

    Parameter:
        - container_code(string): the unique code of the container
        - container_type(string): the type of container can be project or
            dataset for now
        - file_path(string): the location of the file which will be downloaded
        - operator(string): the user who takes the operation
        - session_id(string): the unique id to track the user login session
        - job_id(string): the unique id for the job,
        - payload(dict) default=None: some of the extra infomation saved in dict

    Return:
        - str: the hash code
    """

    if not payload:
        payload = {}

    hash_token_dict = {
        'file_path': file_path,
        'issuer': 'SERVICE DATA DOWNLOAD',
        'operator': operator,
        'session_id': session_id,
        'job_id': job_id,
        'container_code': container_code,
        'container_type': container_type,
        'payload': payload,
        'iat': int(time.time()),
        'exp': int(time.time()) + (ConfigClass.DOWNLOAD_TOKEN_EXPIRE_AT * 60),
    }

    return jwt.encode(hash_token_dict, key=ConfigClass.DOWNLOAD_KEY, algorithm='HS256')
