from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse, Response

from app.common.schemas import DB, Page, Size
from app.modules.auth.dependencies import CurrentUser

from . import schemas as s
from . import service

router = APIRouter(prefix="/imports", tags=["imports"])


@router.get("/adapters")
async def adapters(user: CurrentUser):
    return service.adapters()


@router.get("/template", response_class=Response)
async def template(user: CurrentUser):
    return Response(
        service.template(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="template.csv"'},
    )


@router.post("", status_code=201)
async def upload(
    db: DB,
    user: CurrentUser,
    textbook_id: Annotated[int, Form()],
    adapter: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
):
    return await service.upload(
        db,
        user,
        textbook_id,
        adapter,
        file.filename or "upload",
        await file.read(5 * 1024 * 1024 + 1),
    )


@router.get("/{job_id}")
async def get_job(job_id: int, db: DB, user: CurrentUser):
    return await service.get_job(db, user, job_id)


@router.get("/{job_id}/rows")
async def rows(
    job_id: int,
    db: DB,
    user: CurrentUser,
    match_status: s.MatchStatus | None = None,
    page: Page = 1,
    size: Size = 20,
):
    return await service.list_rows(db, user, job_id, match_status, page, size)


@router.patch("/{job_id}/rows/{row_id}")
async def review(job_id: int, row_id: int, data: s.RowReview, db: DB, user: CurrentUser):
    return await service.review(db, user, job_id, row_id, data)


@router.post("/{job_id}/commit")
async def commit(job_id: int, db: DB, user: CurrentUser, auto_furigana: bool = True):
    result = await service.commit(db, user, job_id, auto_furigana=auto_furigana)
    if result["status"] == "failed":
        error = result["error"]
        error["details"] = {"job_id": job_id, "status": "failed"}
        return JSONResponse(status_code=409, content={"error": error})
    return result
