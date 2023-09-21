# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from fastapi import APIRouter
from fastapi import Depends
from fastapi import FastAPI
from fastapi.responses import Response

from app.resources.health_check import check_kafka
from app.resources.health_check import check_minio
from app.routers import api_root
from app.routers.v1 import api_data_download
from app.routers.v2 import api_data_download as api_data_download_v2

router = APIRouter()


@router.get('/v1/health', summary='Health check for RDS, Redis and Kafka')
async def check_db_connection(
    check_kafka: bool = Depends(check_kafka),
    check_minio: bool = Depends(check_minio),
) -> Response:
    if check_kafka and check_minio:
        return Response(status_code=204)
    return Response(status_code=503)


def api_registry(app: FastAPI):
    app.include_router(router)
    app.include_router(api_root.router)
    app.include_router(api_data_download.router, prefix='/v1')
    app.include_router(api_data_download_v2.router, prefix='/v2')
