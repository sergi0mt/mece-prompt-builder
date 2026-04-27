"""File upload, PDF text extraction, and URL ingestion router."""
import uuid
import shutil
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from ..database import get_db
from ..config import get_settings
from ..models.api_models import UploadResponse
from ..services.pdf_ingestion import extract_pdf_content

router = APIRouter(tags=["uploads"])
settings = get_settings()


@router.post("/projects/{project_id}/uploads", status_code=201)
async def upload_file(project_id: str, file: UploadFile = File(...)) -> UploadResponse:
    # Verify project exists
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

        # Save file to disk
        upload_id = str(uuid.uuid4())
        project_dir = Path(settings.upload_dir) / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        filepath = project_dir / f"{upload_id}_{file.filename}"

        with open(filepath, "wb") as f:
            shutil.copyfileobj(file.file, f)

        file_size = filepath.stat().st_size

        # Extract text if PDF
        extracted_text = None
        extracted_at = None
        if file.filename and file.filename.lower().endswith(".pdf"):
            try:
                extracted_text = extract_pdf_content(filepath)
                extracted_at = datetime.utcnow().isoformat()
            except Exception as e:
                print(f"PDF extraction failed: {e}")

        # Save to database
        await db.execute(
            """INSERT INTO uploads (id, project_id, filename, filepath, file_size, content_type, extracted_text, extracted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (upload_id, project_id, file.filename, str(filepath), file_size,
             file.content_type, extracted_text, extracted_at),
        )
        await db.commit()

        return UploadResponse(
            id=upload_id,
            project_id=project_id,
            filename=file.filename or "unknown",
            file_size=file_size,
            content_type=file.content_type,
            has_extracted_text=extracted_text is not None,
            created_at=datetime.utcnow().isoformat(),
        )
    finally:
        await db.close()


@router.get("/projects/{project_id}/uploads")
async def list_uploads(project_id: str) -> list[UploadResponse]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM uploads WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [
            UploadResponse(
                id=r["id"],
                project_id=r["project_id"],
                filename=r["filename"],
                file_size=r["file_size"],
                content_type=r["content_type"],
                has_extracted_text=r["extracted_text"] is not None,
                created_at=r["created_at"],
            )
            for r in rows
        ]
    finally:
        await db.close()


@router.get("/uploads/{upload_id}/content")
async def get_upload_content(upload_id: str) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT filename, extracted_text FROM uploads WHERE id = ?", (upload_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Upload not found")
        return {
            "filename": row["filename"],
            "text": row["extracted_text"] or "",
            "has_text": row["extracted_text"] is not None,
        }
    finally:
        await db.close()


@router.delete("/uploads/{upload_id}", status_code=204)
async def delete_upload(upload_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT filepath FROM uploads WHERE id = ?", (upload_id,))
        row = await cursor.fetchone()
        if row:
            filepath = Path(row["filepath"])
            if filepath.exists():
                filepath.unlink()
        await db.execute("DELETE FROM uploads WHERE id = ?", (upload_id,))
        await db.commit()
    finally:
        await db.close()


class UrlIngestRequest(BaseModel):
    url: str


@router.post("/projects/{project_id}/uploads/url", status_code=201)
async def ingest_url(project_id: str, body: UrlIngestRequest) -> UploadResponse:
    """Ingest a URL — extract text from the web page."""
    import httpx
    from bs4 import BeautifulSoup

    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

        # Fetch URL content
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(body.url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; McKinseyDeckBuilder/1.0)"
            })
            resp.raise_for_status()

        # Extract text
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove scripts and styles
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Trim to reasonable length
        text = text[:20000]

        title = soup.title.string if soup.title else body.url
        upload_id = str(uuid.uuid4())

        await db.execute(
            """INSERT INTO uploads (id, project_id, filename, filepath, file_size, content_type, extracted_text, extracted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (upload_id, project_id, title[:200], body.url, len(text), "text/html",
             text, datetime.utcnow().isoformat()),
        )
        await db.commit()

        return UploadResponse(
            id=upload_id, project_id=project_id,
            filename=title[:200] if title else body.url[:50],
            file_size=len(text), content_type="text/html",
            has_extracted_text=True,
            created_at=datetime.utcnow().isoformat(),
        )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}")
    finally:
        await db.close()
