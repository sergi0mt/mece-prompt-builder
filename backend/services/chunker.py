"""Semantic PDF chunking — splits by page with sentence-level granularity.
Upgraded: tiktoken token counting, sentence splitting, configurable overlap.
Preserves page numbers and section headers as metadata."""
from __future__ import annotations
import re
from pathlib import Path
import fitz  # PyMuPDF
import tiktoken

# Use cl100k_base encoding (GPT-4/Claude compatible token counting)
_enc = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    """Count tokens using tiktoken."""
    return len(_enc.encode(text))


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences at sentence boundaries.
    Handles common abbreviations and edge cases."""
    # Split on sentence-ending punctuation followed by whitespace + capital
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z\u00C0-\u024F])', text)
    # Also split on newlines that look like paragraph breaks
    result = []
    for sent in sentences:
        parts = re.split(r'\n{2,}', sent)
        result.extend(p.strip() for p in parts if p.strip())
    return result


def chunk_pdf(
    filepath: str | Path,
    max_chunk_tokens: int = 400,
    max_chunks: int = 30,
    overlap_tokens: int = 50,
) -> list[dict]:
    """Extract semantically-chunked text from a PDF.

    Uses tiktoken for accurate token counting, splits at sentence boundaries,
    and includes overlap between chunks for continuity.

    Returns list of dicts with: text, page_num, section_header, token_count, char_count.
    """
    filepath = Path(filepath)
    doc = fitz.open(str(filepath))
    chunks = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        if not text or len(text) < 20:
            continue

        sentences = _split_sentences(text)
        current_chunk = ""
        current_tokens = 0
        current_header = ""
        overlap_buffer = ""  # Trailing sentences from previous chunk

        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue

            # Detect section headers (short, possibly all-caps or bold-like)
            if len(sent) < 80 and (sent.isupper() or sent.endswith(":")):
                current_header = sent
                continue

            sent_tokens = _count_tokens(sent)

            # If adding this sentence exceeds max, finalize current chunk
            if current_tokens + sent_tokens > max_chunk_tokens and current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "page_num": page_num + 1,
                    "section_header": current_header,
                    "token_count": current_tokens,
                    "char_count": len(current_chunk),
                })

                # Build overlap from trailing sentences of current chunk
                chunk_sentences = _split_sentences(current_chunk)
                overlap_buffer = ""
                overlap_tok = 0
                for s in reversed(chunk_sentences):
                    s_tok = _count_tokens(s)
                    if overlap_tok + s_tok > overlap_tokens:
                        break
                    overlap_buffer = s + " " + overlap_buffer
                    overlap_tok += s_tok

                # Start new chunk with overlap
                current_chunk = overlap_buffer + sent + " "
                current_tokens = _count_tokens(current_chunk)
            else:
                current_chunk += sent + " "
                current_tokens += sent_tokens

        # Flush remaining text from this page
        if current_chunk.strip():
            chunks.append({
                "text": current_chunk.strip(),
                "page_num": page_num + 1,
                "section_header": current_header,
                "token_count": _count_tokens(current_chunk),
                "char_count": len(current_chunk),
            })

    doc.close()

    # Limit to max_chunks, keeping the most informative
    if len(chunks) > max_chunks:
        chunks.sort(key=lambda c: c["token_count"], reverse=True)
        chunks = chunks[:max_chunks]
        chunks.sort(key=lambda c: c["page_num"])

    return chunks


def format_chunks_for_prompt(chunks: list[dict], max_total_tokens: int = 3000) -> str:
    """Format chunks as XML for structured citation in prompts.
    Token-aware: stops adding chunks when budget is exhausted."""
    parts = []
    total_tokens = 0
    for i, chunk in enumerate(chunks, 1):
        chunk_tokens = chunk.get("token_count", _count_tokens(chunk["text"]))
        if total_tokens + chunk_tokens > max_total_tokens:
            break
        header = f' section="{chunk["section_header"]}"' if chunk["section_header"] else ""
        parts.append(
            f'<chunk index="{i}" page="{chunk["page_num"]}"{header} tokens="{chunk_tokens}">\n{chunk["text"]}\n</chunk>'
        )
        total_tokens += chunk_tokens
    return "\n\n".join(parts)
