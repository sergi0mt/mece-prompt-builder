"""Chat and SSE streaming router — the core interactive endpoint."""
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..database import get_db
from ..models.api_models import MessageCreate, MessageResponse, SessionResponse
from ..services.orchestrator import get_stage_prompt, extract_structured_data, STAGE_NAMES
from ..services.ai_service import stream_response
from ..services.web_search import search_web, multi_query_search, multi_lang_search, deep_fetch_results, format_web_results
from ..services.json_cleaner import clean_json_response
from ..services.self_refine import self_refine_loop
from ..services.research_agent import run_research_agent, format_research_brief_for_prompt
from ..services.engagement_templates import get_template

router = APIRouter(tags=["chat"])


@router.get("/projects/{project_id}/session")
async def get_or_create_session(project_id: str) -> SessionResponse:
    """Get the active session for a project, or create one."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM sessions WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
            (project_id,),
        )
        row = await cursor.fetchone()

        if row:
            return SessionResponse(
                id=row["id"],
                project_id=row["project_id"],
                current_stage=row["current_stage"],
                stage_data=json.loads(row["stage_data"] or "{}"),
                created_at=row["created_at"],
            )

        # Create new session
        session_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO sessions (id, project_id, current_stage, stage_data) VALUES (?, ?, 1, '{}')",
            (session_id, project_id),
        )
        await db.commit()
        return SessionResponse(
            id=session_id, project_id=project_id, current_stage=1,
            stage_data={}, created_at=datetime.utcnow().isoformat(),
        )
    finally:
        await db.close()


@router.get("/sessions/{session_id}/messages")
async def list_messages(session_id: str) -> list[MessageResponse]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        )
        rows = await cursor.fetchall()
        return [
            MessageResponse(
                id=r["id"], session_id=r["session_id"], role=r["role"],
                content=r["content"], stage=r["stage"],
                metadata=json.loads(r["metadata"] or "{}"), created_at=r["created_at"],
            )
            for r in rows
        ]
    finally:
        await db.close()


@router.post("/sessions/{session_id}/messages")
async def send_message(session_id: str, body: MessageCreate):
    """Send a user message and get an SSE streaming response from the AI orchestrator."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session = await cursor.fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        project_id = session["project_id"]
        current_stage = session["current_stage"]
        stage_data = json.loads(session["stage_data"] or "{}")

        cursor = await db.execute("SELECT engagement_type FROM projects WHERE id = ?", (project_id,))
        proj_row = await cursor.fetchone()
        engagement_type = proj_row["engagement_type"] if proj_row else None
        engagement_template = get_template(engagement_type) if engagement_type else None

        user_msg_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO messages (id, session_id, role, content, stage) VALUES (?, ?, 'user', ?, ?)",
            (user_msg_id, session_id, body.content, current_stage),
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        )
        history = [dict(r) for r in await cursor.fetchall()]

        cursor = await db.execute(
            "SELECT filename, extracted_text FROM uploads WHERE project_id = ? AND extracted_text IS NOT NULL",
            (project_id,),
        )
        pdf_rows = await cursor.fetchall()
        pdf_context = "\n\n".join(
            f"## Document: {r['filename']}\n{r['extracted_text'][:15000]}"
            for r in pdf_rows
        ) if pdf_rows else ""

        cursor = await db.execute(
            "SELECT * FROM storylines WHERE project_id = ?", (project_id,),
        )
        storyline_row = await cursor.fetchone()
        storyline_context = dict(storyline_row) if storyline_row else {}
    finally:
        await db.close()

    auto_refine = body.auto_refine
    output_tone = body.output_tone
    output_audience = body.output_audience
    output_language = body.output_language
    use_web_search = body.use_web_search
    research_depth = body.research_depth

    depth_tokens = {"quick": 1200, "standard": 2500, "detailed": 4096, "comprehensive": 7000}
    max_tok = depth_tokens.get(research_depth, 2500)

    async def event_stream():
        full_response = ""
        web_context = ""

        use_research_agent = (
            use_web_search
            and current_stage >= 2
            and research_depth in ("detailed", "comprehensive")
        )

        if use_research_agent:
            central_q = stage_data.get("central_question", body.content)
            branches_raw = stage_data.get("branches", "")
            if isinstance(branches_raw, str):
                try:
                    branches_parsed = json.loads(branches_raw)
                except (json.JSONDecodeError, TypeError):
                    branches_parsed = branches_raw
            else:
                branches_parsed = branches_raw

            search_langs = [output_language] if output_language and output_language != "en" else None

            yield f"data: {json.dumps({'type': 'text', 'content': ''})}\n\n"
            try:
                research_brief = None
                async for event in run_research_agent(
                    question=central_q,
                    audience=stage_data.get("audience", "client"),
                    deck_type=stage_data.get("deck_type", "strategic"),
                    branches=branches_parsed,
                    known_data=pdf_context[:3000] if pdf_context else "",
                    search_languages=search_langs,
                    max_steps=4 if research_depth == "detailed" else 6,
                    research_checklist=engagement_template.research_checklist if engagement_template else None,
                ):
                    yield f"event: research\ndata: {json.dumps(event)}\n\n"
                    if event.get("type") == "synthesize_done":
                        research_brief = event.get("brief")

                if research_brief:
                    web_context = format_research_brief_for_prompt(research_brief)

            except Exception as e:
                print(f"Research agent failed, falling back to simple search: {e}")
                use_research_agent = False

        if use_web_search and current_stage >= 1 and not use_research_agent:
            central_q = stage_data.get("central_question", body.content)
            try:
                if current_stage >= 2 and stage_data.get("branches"):
                    branches = stage_data["branches"]
                    if isinstance(branches, str):
                        branches = json.loads(branches)
                    queries = [central_q]
                    for b in branches[:4]:
                        q = b.get("question", "") if isinstance(b, dict) else str(b)
                        if q:
                            queries.append(f"{central_q} {q}")
                    web_results = await multi_query_search(queries, max_results_per_query=4)
                else:
                    web_results = await search_web(central_q, max_results=8)

                if output_language and output_language != "en":
                    lang_results = await multi_lang_search(central_q, languages=[output_language], max_results_per_lang=3)
                    existing_urls = {r["url"] for r in web_results}
                    web_results.extend(r for r in lang_results if r["url"] not in existing_urls)

                web_results = await deep_fetch_results(web_results, max_deep=3)
                web_context = format_web_results(web_results)

            except Exception as e:
                print(f"Web search failed: {e}")
                yield f"data: {json.dumps({'type': 'error', 'content': f'Web search failed: {e}. Proceeding without web data.'})}\n\n"

        system_prompt = get_stage_prompt(
            stage=current_stage,
            stage_data=stage_data,
            pdf_context=pdf_context,
            storyline_context=storyline_context,
            web_context=web_context,
            output_tone=output_tone,
            engagement_template=engagement_template,
            output_audience=output_audience,
            output_language=output_language,
        )

        try:
            async for token in stream_response(system_prompt, history, stage=current_stage, max_tokens_override=max_tok):
                full_response += token
                yield f"data: {json.dumps({'type': 'text', 'content': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            return

        structured = extract_structured_data(current_stage, full_response, stage_data)

        db2 = await get_db()
        try:
            asst_msg_id = str(uuid.uuid4())
            await db2.execute(
                "INSERT INTO messages (id, session_id, role, content, stage, metadata) VALUES (?, ?, 'assistant', ?, ?, ?)",
                (asst_msg_id, session_id, full_response, current_stage, json.dumps(structured)),
            )

            new_stage_data = {**stage_data, **structured.get("collected_fields", {})}
            new_stage = structured.get("next_stage", current_stage)

            await db2.execute(
                "UPDATE sessions SET stage_data = ?, current_stage = ?, updated_at = datetime('now') WHERE id = ?",
                (json.dumps(new_stage_data), new_stage, session_id),
            )

            if structured.get("storyline_update"):
                sl = structured["storyline_update"]
                cursor = await db2.execute(
                    "SELECT id FROM storylines WHERE project_id = ?", (project_id,)
                )
                existing = await cursor.fetchone()
                if existing:
                    sets = ", ".join(f"{k} = ?" for k in sl.keys())
                    vals = list(sl.values()) + [project_id]
                    await db2.execute(
                        f"UPDATE storylines SET {sets}, updated_at = datetime('now') WHERE project_id = ?",
                        vals,
                    )
                else:
                    sl_id = str(uuid.uuid4())
                    await db2.execute(
                        "INSERT INTO storylines (id, project_id) VALUES (?, ?)",
                        (sl_id, project_id),
                    )
                    if sl:
                        sets = ", ".join(f"{k} = ?" for k in sl.keys())
                        vals = list(sl.values()) + [project_id]
                        await db2.execute(
                            f"UPDATE storylines SET {sets} WHERE project_id = ?", vals,
                        )

            await db2.commit()

            if structured.get("collected_fields"):
                yield f"event: structured_data\ndata: {json.dumps(structured)}\n\n"

            yield f"event: stage_info\ndata: {json.dumps({'stage': new_stage, 'stage_name': STAGE_NAMES.get(new_stage, ''), 'stage_data': new_stage_data})}\n\n"

        finally:
            await db2.close()

        yield f"event: done\ndata: {{}}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/sessions/{session_id}/stage/advance")
async def advance_stage(session_id: str) -> SessionResponse:
    """Force advance to the next stage (max stage 2)."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session = await cursor.fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        new_stage = min(session["current_stage"] + 1, 2)
        await db.execute(
            "UPDATE sessions SET current_stage = ?, updated_at = datetime('now') WHERE id = ?",
            (new_stage, session_id),
        )
        await db.commit()

        return SessionResponse(
            id=session_id, project_id=session["project_id"],
            current_stage=new_stage,
            stage_data=json.loads(session["stage_data"] or "{}"),
            created_at=session["created_at"],
        )
    finally:
        await db.close()


@router.post("/sessions/{session_id}/stage/set/{stage}")
async def set_stage(session_id: str, stage: int) -> SessionResponse:
    """Set stage to 1 or 2."""
    if stage < 1 or stage > 2:
        raise HTTPException(status_code=400, detail="Stage must be 1-2")
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session = await cursor.fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        await db.execute(
            "UPDATE sessions SET current_stage = ?, updated_at = datetime('now') WHERE id = ?",
            (stage, session_id),
        )
        await db.commit()

        return SessionResponse(
            id=session_id, project_id=session["project_id"],
            current_stage=stage,
            stage_data=json.loads(session["stage_data"] or "{}"),
            created_at=session["created_at"],
        )
    finally:
        await db.close()
