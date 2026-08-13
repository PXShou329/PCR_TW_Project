from __future__ import annotations

from fastapi import APIRouter, Request, Response

from .runtime import (
    GachaLibraryRuntime,
    forecast_list_view,
    gacha_library_meta,
)
from .schemas import (
    GachaForecastListData,
    GachaLibraryEnvelope,
    GachaLibraryErrorResponse,
)


router = APIRouter(prefix="/api/v1/gacha-library", tags=["gacha-library"])

UNAVAILABLE_RESPONSE = {
    503: {
        "model": GachaLibraryErrorResponse,
        "description": "Local Gacha library is disabled, unavailable, invalid, or drifted.",
    }
}
NOT_FOUND_RESPONSE = {
    404: {
        "model": GachaLibraryErrorResponse,
        "description": "The requested local Gacha asset is not in the source DOCX.",
    }
}


def _runtime(request: Request) -> GachaLibraryRuntime:
    return request.app.state.gacha_library_runtime


@router.get(
    "/forecasts",
    response_model=GachaLibraryEnvelope[GachaForecastListData],
    responses=UNAVAILABLE_RESPONSE,
)
def list_gacha_forecasts(
    request: Request,
) -> GachaLibraryEnvelope[GachaForecastListData]:
    snapshot = _runtime(request).snapshot()
    return GachaLibraryEnvelope[GachaForecastListData](
        data=forecast_list_view(snapshot),
        meta=gacha_library_meta(snapshot),
    )


@router.get(
    "/assets/{sha256}",
    response_class=Response,
    responses={**UNAVAILABLE_RESPONSE, **NOT_FOUND_RESPONSE},
)
def get_gacha_asset(sha256: str, request: Request) -> Response:
    asset = _runtime(request).read_asset(sha256)
    extension = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }[asset.mime_type]
    return Response(
        content=asset.data,
        media_type=asset.mime_type,
        headers={
            "Cache-Control": "private, max-age=31536000, immutable",
            "Content-Disposition": (
                f'inline; filename="{asset.sha256}.{extension}"'
            ),
            "ETag": f'"{asset.sha256}"',
        },
    )
