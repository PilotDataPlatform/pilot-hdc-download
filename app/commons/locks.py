# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import httpx

from app.config import ConfigClass


class ResourceAlreadyInUsed(Exception):
    pass


async def bulk_lock_operation(resource_key: list, operation: str, lock: bool = True) -> dict:
    """
    Summary:
        The function will perform batch lock/unlock operation based
        on the parameters.

    Parameter:
        - resource_key(list): list of minio path will be locked, formating
            as <bucket>/path/to/file
        - operation(string): can be either read or write operation
        - lock(bool): True indicate lock operation, False indicates unlock operation

    Return:
        - dict: the node which will be locked
    """

    method = 'POST' if lock else 'DELETE'

    url = ConfigClass.DATAOPS_SERVICE_V2 + 'resource/lock/bulk'
    post_json = {'resource_keys': resource_key, 'operation': operation}
    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, json=post_json, timeout=3600)
    if response.status_code != 200:
        raise ResourceAlreadyInUsed(f'resource {resource_key} already in used')

    return response.json()
