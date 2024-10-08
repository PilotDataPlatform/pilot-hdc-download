# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import httpx

from app.commons.kafka_producer import get_kafka_producer
from app.config import ConfigClass
from app.logger import logger


async def check_minio() -> bool:
    """
    Summary:
        the function is to check if minio is available.
        it uses the minio health check endpoint for cluster.
        For more infomation, check document:
        https://github.com/minio/minio/blob/master/docs/metrics/healthcheck/README.md
    Return:
        - {"Minio": status}
    """

    http_protocal = 'https://' if ConfigClass.S3_INTERNAL_HTTPS else 'http://'
    url = http_protocal + ConfigClass.S3_INTERNAL + '/minio/health/cluster'

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url)

            if res.status_code != 200:
                logger.error('Minio cluster is unavailable')
                return False

            # logger.info('Minio is connected')
    except Exception as e:
        logger.error(f'Fail with error: {e}')
        return False

    return True


async def check_kafka() -> bool:
    """
    Summary:
        the function is to check if kafka is available.
        this will just check if we successfully init the
        kafka producer
    Return:
        - {"Kafka": status}
    """

    kafka_connection = await get_kafka_producer()
    if kafka_connection.connected is False:
        logger.error('Kafka is not connected')
        return False

    # logger.info('Kafka is connected')
    return True
