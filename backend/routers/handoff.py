"""Handoff router — returns the deepresearch-ready markdown prompt."""
import json
from fastapi import APIRouter, HTTPException
from ..database import get_db
from ..services.handoff_builder import build_handoff_prompt

router = APIRouter(tags=["handoff"])


@router.get("/projects/{project_id}/handoff")
async def get_handoff_prompt(project_id: str):
    """Return the deepresearch-ready markdown prompt for a completed Stage 2 engagement."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM sessions WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
            (project_id,),
        )
        session = await cursor.fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        cursor = await db.execute("SELECT name FROM projects WHERE id = ?", (project_id,))
        project = await cursor.fetchone()
        project_name = project["name"] if project else "Engagement"

        stage_data = json.loads(session["stage_data"] or "{}")

        # Allow generating the prompt even if stage < 2, but flag it as incomplete
        branches = stage_data.get("branches", "")
        if isinstance(branches, str) and branches:
            try:
                branches = json.loads(branches)
            except Exception:
                branches = []
        if not branches:
            raise HTTPException(
                status_code=400,
                detail="MECE branches not yet generated. Complete Stage 2 first.",
            )

        prompt, truncated = build_handoff_prompt(stage_data, project_name)
        return {"prompt": prompt, "char_count": len(prompt), "truncated": truncated}
    finally:
        await db.close()
