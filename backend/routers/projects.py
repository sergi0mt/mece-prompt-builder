"""Projects CRUD router."""
import uuid
from fastapi import APIRouter, HTTPException
from ..database import get_db
from ..models.api_models import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def list_projects() -> list[ProjectResponse]:
    db = await get_db()
    try:
        cursor = await db.execute("""
            SELECT p.*,
                   (SELECT COUNT(*) FROM uploads WHERE project_id = p.id) as upload_count,
                   (SELECT COUNT(*) FROM slides WHERE project_id = p.id) as slide_count,
                   COALESCE((SELECT current_stage FROM sessions WHERE project_id = p.id
                             ORDER BY created_at DESC LIMIT 1), 0) as current_stage
            FROM projects p ORDER BY p.updated_at DESC
        """)
        rows = await cursor.fetchall()
        return [ProjectResponse(**dict(r)) for r in rows]
    finally:
        await db.close()


@router.post("", status_code=201)
async def create_project(body: ProjectCreate) -> ProjectResponse:
    db = await get_db()
    try:
        project_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO projects (id, name, description, audience, deck_type, engagement_type) VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, body.name, body.description, body.audience, body.deck_type, body.engagement_type),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = await cursor.fetchone()
        return ProjectResponse(**dict(row), upload_count=0, slide_count=0, current_stage=0)
    finally:
        await db.close()


@router.get("/{project_id}")
async def get_project(project_id: str) -> ProjectResponse:
    db = await get_db()
    try:
        cursor = await db.execute("""
            SELECT p.*,
                   (SELECT COUNT(*) FROM uploads WHERE project_id = p.id) as upload_count,
                   (SELECT COUNT(*) FROM slides WHERE project_id = p.id) as slide_count,
                   COALESCE((SELECT current_stage FROM sessions WHERE project_id = p.id
                             ORDER BY created_at DESC LIMIT 1), 0) as current_stage
            FROM projects p WHERE p.id = ?
        """, (project_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        return ProjectResponse(**dict(row))
    finally:
        await db.close()


@router.put("/{project_id}")
async def update_project(project_id: str, body: ProjectUpdate) -> ProjectResponse:
    db = await get_db()
    try:
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [project_id]
        await db.execute(
            f"UPDATE projects SET {set_clause}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        await db.commit()
        return await get_project(project_id)
    finally:
        await db.close()


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str):
    db = await get_db()
    try:
        await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        await db.commit()
    finally:
        await db.close()
