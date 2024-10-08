# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from fastapi import APIRouter

from app.commons.kafka_producer import get_kafka_producer
from app.config import ConfigClass

router = APIRouter()


@router.get('/')
async def root():
    """Healthcheck route."""

    return {
        'status': 'OK',
        'name': ConfigClass.APP_NAME,
        'version': ConfigClass.VERSION,
    }


@router.on_event('shutdown')
async def shutdown_event():
    """
    Summary:
        the shutdown event to gracefully close the
        kafka producer.
    """

    kp = await get_kafka_producer()
    await kp.close_connection()

    return
