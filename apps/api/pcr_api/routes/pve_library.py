from __future__ import annotations

from fastapi import APIRouter, Query, Request, Response

from ..pve_library import (
    PveLibraryNotFound,
    PveLibraryRuntime,
    available_stage_filters,
    filter_stages,
    pve_meta,
    stage_detail_view,
    stage_summary_view,
)
from ..pve_library_schemas import (
    PveLibraryErrorResponse,
    PveLibraryEnvelope,
    PveStageDetail,
    PveStageListData,
)


router = APIRouter(prefix="/api/v1/pve-library", tags=["pve-library"])

UNAVAILABLE_RESPONSE = {
    503: {
        "model": PveLibraryErrorResponse,
        "description": "Local PVE library is disabled, unavailable, invalid, or drifted.",
    }
}
NOT_FOUND_RESPONSE = {
    404: {
        "model": PveLibraryErrorResponse,
        "description": "The requested local PVE stage or asset is not in the catalog.",
    }
}


def _runtime(request: Request) -> PveLibraryRuntime:
    return request.app.state.pve_library_runtime


@router.get(
    "/stages",
    response_model=PveLibraryEnvelope[PveStageListData],
    responses=UNAVAILABLE_RESPONSE,
)
def list_pve_stages(
    request: Request,
    mode: str | None = Query(default=None, min_length=1, max_length=64, pattern=r"\S"),
    element: str | None = Query(default=None, min_length=1, max_length=64, pattern=r"\S"),
    area: int | None = Query(default=None, ge=1),
    stage: int | None = Query(default=None, ge=1),
) -> PveLibraryEnvelope[PveStageListData]:
    normalized_mode = mode.strip().upper() if mode is not None else None
    normalized_element = element.strip().upper() if element is not None else None
    snapshot = _runtime(request).snapshot()
    matches = filter_stages(
        snapshot,
        mode=normalized_mode,
        element=normalized_element,
        area=area,
        stage=stage,
    )
    return PveLibraryEnvelope[PveStageListData](
        data={
            "items": [stage_summary_view(record) for record in matches],
            "filters": {
                "mode": normalized_mode,
                "element": normalized_element,
                "area": area,
                "stage": stage,
            },
            "available_filters": available_stage_filters(
                snapshot,
                mode=normalized_mode,
                element=normalized_element,
            ),
            "total": len(matches),
        },
        meta=pve_meta(snapshot),
    )


@router.get(
    "/stages/{stage_id}",
    response_model=PveLibraryEnvelope[PveStageDetail],
    responses={**UNAVAILABLE_RESPONSE, **NOT_FOUND_RESPONSE},
)
def get_pve_stage(
    stage_id: str,
    request: Request,
) -> PveLibraryEnvelope[PveStageDetail]:
    snapshot = _runtime(request).snapshot()
    record = snapshot.stages_by_id.get(stage_id)
    if record is None:
        raise PveLibraryNotFound("pve_stage", stage_id)
    return PveLibraryEnvelope[PveStageDetail](
        data=stage_detail_view(
            record,
            external_icons_enabled=(
                request.app.state.settings.pve_library_external_icons_enabled
            ),
        ),
        meta=pve_meta(snapshot),
    )


@router.get(
    "/assets/{sha256}",
    response_class=Response,
    responses={**UNAVAILABLE_RESPONSE, **NOT_FOUND_RESPONSE},
)
def get_pve_asset(sha256: str, request: Request) -> Response:
    data, asset = _runtime(request).read_asset(sha256)
    return Response(
        content=data,
        media_type=asset.mime_type,
        headers={
            "Cache-Control": "private, max-age=31536000, immutable",
            "Content-Disposition": f'inline; filename="{asset.filename}"',
            "ETag": f'"{asset.sha256}"',
        },
    )
