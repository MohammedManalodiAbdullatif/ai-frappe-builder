"""
routers/export.py — Export endpoint. No approval needed — fully automatic.
"""
from __future__ import annotations

import json
from pathlib import Path

from database import get_current_spec, get_db, get_session
from exporter import export_app
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from models import AppSpec
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class ExportRequest(BaseModel):
    output_dir: str = "/tmp/frappe_exports"
    git_remote: str | None = None  # e.g. "https://github.com/user/repo.git"


class ExportResponse(BaseModel):
    app_path: str
    app_name: str
    zip_path: str | None = None
    download_url: str | None = None
    files_created: list[str]
    git_initialized: bool
    git_remote: str | None
    errors: list[str]


@router.post("/{session_id}", response_model=ExportResponse)
async def export(
    session_id: str,
    body: ExportRequest = ExportRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Export the built app to a real Frappe app directory structure.
    Automatically commits to git and packages into a .zip file.
    """
    sess = await get_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    spec_row = await get_current_spec(db, session_id)
    if not spec_row:
        raise HTTPException(status_code=404, detail="No spec found for this session")

    spec_dict = json.loads(spec_row.spec_json) if isinstance(spec_row.spec_json, str) else spec_row.spec_json
    spec = AppSpec(**spec_dict)

    result = await export_app(spec, body.output_dir, body.git_remote)

    if "app_path" not in result:
        raise HTTPException(status_code=422, detail=result.get("errors", ["Export failed"]))

    result["download_url"] = f"http://localhost:8000/export/{session_id}/download"
    return ExportResponse(**result)


@router.get("/{session_id}/download")
async def download_app_zip(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Download the generated Frappe app as a .zip archive.
    """
    spec_row = await get_current_spec(db, session_id)
    if not spec_row:
        raise HTTPException(status_code=404, detail="No spec found for this session")

    spec_dict = json.loads(spec_row.spec_json) if isinstance(spec_row.spec_json, str) else spec_row.spec_json
    spec = AppSpec(**spec_dict)
    app_name = spec.app.get("app_name", "frappe_app") if spec.app else "frappe_app"

    # Ensure export exists or export now
    zip_path = Path("/tmp/frappe_exports") / f"{app_name}.zip"
    if not zip_path.exists():
        res = await export_app(spec, "/tmp/frappe_exports")
        if res.get("zip_path"):
            zip_path = Path(res["zip_path"])

    if not zip_path.exists():
        raise HTTPException(status_code=500, detail="Could not locate or generate app zip")

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"{app_name}.zip",
    )


@router.get("/{session_id}/tree")
async def get_exported_tree(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the directory and file tree of the exported application.
    """
    spec_row = await get_current_spec(db, session_id)
    if not spec_row:
        raise HTTPException(status_code=404, detail="No spec found for this session")

    spec_dict = json.loads(spec_row.spec_json) if isinstance(spec_row.spec_json, str) else spec_row.spec_json
    app_name = spec_dict.get("app", {}).get("app_name", "custom_app")

    from ai_frappe_builder.services.exporter import FrappeAppExporter

    exporter = FrappeAppExporter()
    try:
        return exporter.get_file_tree(app_name)
    except FileNotFoundError:
        # Generate export if not already on disk
        await export_app(spec_dict)
        return exporter.get_file_tree(app_name)


@router.get("/{session_id}/file")
async def get_exported_file_content(
    session_id: str,
    path: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve raw file content for a given path inside the exported app.
    """
    spec_row = await get_current_spec(db, session_id)
    if not spec_row:
        raise HTTPException(status_code=404, detail="No spec found for this session")

    spec_dict = json.loads(spec_row.spec_json) if isinstance(spec_row.spec_json, str) else spec_row.spec_json
    app_name = spec_dict.get("app", {}).get("app_name", "custom_app")

    from ai_frappe_builder.services.exporter import FrappeAppExporter

    exporter = FrappeAppExporter()
    try:
        content = exporter.read_exported_file(app_name, path)
        return {"path": path, "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File '{path}' not found.")
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
