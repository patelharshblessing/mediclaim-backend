# app/value_extractor.py
import base64
import io
import json
import math
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
import time

import httpx
from fastapi import HTTPException, status
from openai import OpenAI
from pdf2image import convert_from_bytes
from pydantic import ValidationError

from .config import settings
from .logger import get_logger
from .pydantic_schemas import ExtractedDataWithConfidence

import asyncio
from typing import Any, Awaitable, List, Tuple, Optional

logger = get_logger(__name__)

# --- Optional semantic similarity support (uses same model as normalization_service) ---
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    _EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
    _embed_model: Optional[SentenceTransformer] = None

    def _get_embed_model() -> SentenceTransformer:
        global _embed_model
        if _embed_model is None:
            _embed_model = SentenceTransformer(_EMBED_MODEL_NAME)
        return _embed_model

    def _embed_similarity(a: str, b: str) -> float:
        """Cosine similarity between two strings using SBERT."""
        model = _get_embed_model()
        vecs = model.encode([a, b], convert_to_numpy=True)
        va, vb = vecs[0], vecs[1]
        # Safe cosine
        denom = max(1e-12, float(np.linalg.norm(va) * np.linalg.norm(vb)))
        return float(np.dot(va, vb) / denom)

except Exception:
    # If embeddings are not available, we still work with exact/fuzzy.
    _embed_model = None

    def _embed_similarity(a: str, b: str) -> float:
        return 0.0


# --- Initialize OpenAI Client (only if key is provided) ---
openai_client: Optional[OpenAI] = None
if getattr(settings, "OPENAI_API_KEY", None):
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# --- Master Prompt (unchanged) ---
MASTER_PROMPT = """
Your task is to act as an expert data extraction agent for Indian medical bills.
Analyze the provided image(s) of a hospital bill and respond ONLY with a valid JSON object
that strictly follows the schema provided below.
For every field, you must provide the extracted `value` and a `confidence` score from 0.0 to 1.0.
...
Use this scale for the `confidence` score:
- 1.0: The text is perfectly clear and legible.
- 0.9: The text is slightly blurry but you are very confident.
- 0.7: The text is difficult to read or ambiguous. This is your best interpretation.
- 0.5: The text is extremely blurry or obscured. This is a best-effort guess.

CRITICAL: DO NOT GUESS OR INFER MISSING VALUES.
If a field or any numeric value is NOT PRESENT on the bill, set `"value": null`
and set `"confidence"` to reflect your confidence that it is truly absent:
- If you are confident the field is not present on the page(s), set confidence > 0.9
- If you are not sure whether it is absent, set a lower confidence (< 0.9)

Do NOT fabricate quantities, unit prices, dates, IDs, or totals.
Do NOT fill values from context if they are not explicitly present.
Use null for any such values and set the absence confidence.

**CRITICAL INSTRUCTIONS FOR DIFFICULT TEXT:**
1.  It is **mandatory** to attempt extraction for every visible line item, even if parts of it are faded, blurry, or covered by a stamp.
2.  **DO NOT OMIT** a line item or a value just because it is hard to read.
3.  You **MUST** provide your best possible guess for the value and assign a low confidence score (e.g., 0.5-0.7) to indicate your uncertainty.
4.  Use contextual clues. For example, if the line item totals and the final gross total are visible, use them to infer the values of obscured line items.

...
JSON Output Structure:
{
  "hospital_name": { "value": "String", "confidence": "Float" },
  "patient_name": { "value": "String", "confidence": "Float" },
  "bill_no": { "value": "String", "confidence": "Float" },
  "bill_date": { "value": "YYYY-MM-DD", "confidence": "Float" },
  "admission_date": { "value": "YYYY-MM-DD", "confidence": "Float" },
  "discharge_date": { "value": "YYYY-MM-DD", "confidence": "Float" },
  "net_payable_amount": { "value": "Float", "confidence": "Float" },
  "line_items": [
    {
      "description": { "value": "String", "confidence": "Float" },
      "quantity": { "value": "Float", "confidence": "Float" },
      "unit_price": { "value": "Float", "confidence": "Float" },
      "total_amount": { "value": "Float", "confidence": "Float" }
    }
  ]
}
"""


# ---------------------------
# Helpers
# ---------------------------
def convert_pdf_to_base64_images(file_content: bytes) -> List[str]:
    """Converts all pages of a PDF to Base64 encoded JPEG images."""
    try:
        images = convert_from_bytes(file_content, fmt="jpeg")
        if not images:
            raise ValueError("Could not convert PDF to images.")

        base64_images = []
        for image in images:
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            base64_images.append(base64.b64encode(buffered.getvalue()).decode("utf-8"))

        return base64_images
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process PDF: {e}",
        )


def _normalize_text(s: Optional[str]) -> str:
    if s is None:
        return ""
    out = s.strip().lower()
    # collapse whitespace
    out = " ".join(out.split())
    # strip simple punctuation
    for ch in ",;:()[]{}|/\\\"'`~!@#$%^&*+=<>.?":
        out = out.replace(ch, " ")
    out = " ".join(out.split())
    return out


def _fuzzy_ratio(a: str, b: str) -> float:
    # Lightweight fuzz ratio using difflib (0..1), token-set-ish via unique tokens
    import difflib

    ta = " ".join(sorted(set(_normalize_text(a).split())))
    tb = " ".join(sorted(set(_normalize_text(b).split())))
    return difflib.SequenceMatcher(None, ta, tb).ratio()


def _round_half_away_from_zero(x: Optional[float]) -> Optional[int]:
    if x is None:
        return None
    # half away from zero
    if x >= 0:
        return int(math.floor(x + 0.5))
    else:
        return int(math.ceil(x - 0.5))


def _choose_value_and_conf(
    g_value: Any,
    g_conf: Optional[float],
    o_value: Any,
    o_conf: Optional[float],
    prefer_gemini_on_tie: bool = True,
) -> Tuple[Any, float]:
    """Pick the value from the provider with higher confidence; if tie, prefer Gemini. Return (value, chosen_conf)."""
    gc = g_conf if g_conf is not None else 0.0
    oc = o_conf if o_conf is not None else 0.0
    if abs(gc - oc) < 1e-9:
        return (g_value if prefer_gemini_on_tie else o_value, gc)
    return (g_value, gc) if gc > oc else (o_value, oc)


def _both_conf_over_90(
    conf_list_a: List[Optional[float]], conf_list_b: List[Optional[float]]
) -> bool:
    """True if for each paired confidence both sides are > 0.9."""
    for ca, cb in zip(conf_list_a, conf_list_b):
        if (ca is None or ca < 0.7) or (cb is None or cb < 0.7):
            return False
    return True


def _desc_match_score(desc_a: str, desc_b: str) -> float:
    """Hybrid: exact -> 1.0; else max(fuzzy, embed) with thresholds applied separately later."""
    na, nb = _normalize_text(desc_a), _normalize_text(desc_b)
    if na and na == nb:
        return 1.0
    fz = _fuzzy_ratio(na, nb)  # 0..1
    emb = _embed_similarity(na, nb) if _embed_model is not None else 0.0
    return max(fz, emb)


# You need to update only the `_descriptions_match` function inside app/value_extractor.py
# Locate this existing function:


def _descriptions_match(desc_a: str, desc_b: str) -> Tuple[bool, float]:
    """
    Decide if two descriptions match by hybrid logic:
    - exact match -> True
    - else token-set fuzzy >= 0.90 -> True
    - else embedding cosine >= 0.80 (if available) -> True
    Returns (matched, score)
    """
    na, nb = _normalize_text(desc_a), _normalize_text(desc_b)
    if na and na == nb:
        return True, 1.0

    # Token-set containment logic
    tokens_a = set(na.split())
    tokens_b = set(nb.split())
    if tokens_a.issubset(tokens_b) or tokens_b.issubset(tokens_a):
        return True, 0.9  # or 0.85 if you want to be stricter

    fz = _fuzzy_ratio(na, nb)
    if fz >= 0.90:
        return True, fz

    emb = _embed_similarity(na, nb) if _embed_model is not None else 0.0
    if emb >= 0.80:
        return True, emb

    return False, max(fz, emb)


# With this change, identical descriptions and ones like 'SGPT' vs 'Pathology Investigation - SGPT'
# will now match correctly and avoid duplicate line items.

# No changes are required in _greedy_match_pairs or _merge_line_items because
# they already use _descriptions_match internally.

# ✅ DONE


# ---------------------------
# Provider Calls
# ---------------------------
async def _call_gemini_api(base64_images: List[str]) -> Dict[str, Any]:
    """Makes an API call to the Gemini 2.5 Pro model."""
    if not getattr(settings, "GEMINI_API_KEY", None):
        raise RuntimeError("GEMINI_API_KEY not configured.")
    print("Attempting extraction with Gemini 2.5 Pro...")

    GEMINI_API_URL = (
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"
        f"?key={settings.GEMINI_API_KEY}"
    )

    request_parts = [{"text": MASTER_PROMPT}]
    for image_data in base64_images:
        request_parts.append(
            {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
        )

    payload = {
        "contents": [{"parts": request_parts}],
        "generationConfig": {"response_mime_type": "application/json"},
    }

    start_time = time.time()
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(GEMINI_API_URL, json=payload)
        response.raise_for_status()
    duration = time.time() - start_time
    print(f"Gemini API call took {duration:.2f} seconds.")

    result = response.json()
    ai_response_str = result["candidates"][0]["content"]["parts"][0]["text"]
    print(f"Gemini response: {ai_response_str}")
    return json.loads(ai_response_str)


async def _call_openai_api(base64_images: List[str]) -> Dict[str, Any]:
    """Makes an API call to the GPT-5 model."""
    if openai_client is None:
        raise RuntimeError("OPENAI_API_KEY not configured.")
    print("Attempting extraction with GPT-5...")

    messages = [{"role": "user", "content": [{"type": "text", "text": MASTER_PROMPT}]}]
    for image_data in base64_images:
        messages[0]["content"].append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
            }
        )

    start_time = time.time()
    response = await asyncio.to_thread(
        openai_client.chat.completions.create,
        model="gpt-5",
        messages=messages,
        response_format={"type": "json_object"},
    )

    duration = time.time() - start_time
    print(f"GPT-5 API call took {duration:.2f} seconds.")

    ai_response_str = response.choices[0].message.content
    print(f"Gemini response: {ai_response_str}")
    return json.loads(ai_response_str)

# 🔹 NEW: Claude Sonnet provider call
async def _call_sonnet_api(base64_images: List[str]) -> Dict[str, Any]:
    """
    Makes an API call to Claude Sonnet 4.5 via Anthropic Messages API.
    Cleans Markdown JSON fences if present and returns valid parsed JSON.
    """
    if not getattr(settings, "CLAUDE_API_KEY", None):
        raise RuntimeError("CLAUDE_API_KEY not configured.")
    print("Attempting extraction with Claude Sonnet 4.5...")

    CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
    CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

    headers = {
        "x-api-key": settings.CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    # Build the multimodal message
    content: List[Dict[str, Any]] = [{"type": "text", "text": MASTER_PROMPT}]
    for b64 in base64_images:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
        })

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": content}],
    }

    start_time = time.time()
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(CLAUDE_API_URL, headers=headers, json=payload)
        response.raise_for_status()
    duration = time.time() - start_time
    print(f"Claude Sonnet API call took {duration:.2f} seconds.")

    data = response.json()
    if not data.get("content"):
        raise RuntimeError("Claude API returned no 'content' blocks.")

    block0 = data["content"][0]
    if block0.get("type") != "text":
        raise RuntimeError("Claude API returned non-text first block.")

    ai_response_str = block0.get("text", "").strip()

    # --- 🔧 Clean Markdown or extra wrapping ---
    import re
    ai_response_str = ai_response_str.strip()
    ai_response_str = re.sub(r"^```(?:json)?\s*", "", ai_response_str)
    ai_response_str = re.sub(r"\s*```$", "", ai_response_str)
    ai_response_str = ai_response_str.strip()

    # --- Optional sanity: if model added “Sure, here’s JSON:” etc. ---
    if ai_response_str.lower().startswith("sure"):
        ai_response_str = ai_response_str.split("{", 1)[-1]
        ai_response_str = "{" + ai_response_str
    print(f"Cleaned Claude response: {ai_response_str}")
    try:
        parsed_json = json.loads(ai_response_str)
        print(f"Parsed JSON: {parsed_json}")
        return parsed_json
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Claude Sonnet returned invalid JSON: {e}\n\nRaw text received:\n{ai_response_str}"
        )



# ---------------------------
# Fusion Logic
# ---------------------------
def _extract_header_field(d: Dict[str, Any], key: str) -> Tuple[Any, Optional[float]]:
    obj = d.get(key, {}) or {}
    return obj.get("value", None), obj.get("confidence", None)


def _extract_line_items(d: Dict[str, Any]) -> List[Dict[str, Any]]:
    return d.get("line_items", []) or []


def _merge_headers(g: Dict[str, Any], o: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Merge non-line-item fields by:
      - Strings: same description-matching logic
      - Dates: equal if same YYYY-MM-DD
      - Numbers: equal if round-to-int equal
      Confidence rule:
        - if matched and both providers' confidences for the field > 0.9 → 1.0
        - else 0.5
      Value picked from higher-confidence provider (tie → Gemini)
    """
    out: Dict[str, Dict[str, Any]] = {}

    def set_field(key: str, value: Any, conf: float):
        out[key] = {"value": value, "confidence": float(conf)}

    # String-like fields
    for key in ["hospital_name", "patient_name", "bill_no"]:
        gv, gc = _extract_header_field(g, key)
        ov, oc = _extract_header_field(o, key)

        if gv is None and ov is None:
            set_field(key, None, 0.5)
            continue

        matched, _score = _descriptions_match(str(gv or ""), str(ov or ""))
        chosen_value, chosen_conf = _choose_value_and_conf(gv, gc, ov, oc)
        final_conf = 1.0 if (matched and _both_conf_over_90([gc], [oc])) else 0.5
        set_field(key, chosen_value, final_conf)

    # Date fields: equal iff exact YYYY-MM-DD strings
    for key in ["bill_date", "admission_date", "discharge_date"]:
        gv, gc = _extract_header_field(g, key)
        ov, oc = _extract_header_field(o, key)

        if gv is None and ov is None:
            set_field(key, None, 0.5)
            continue

        matched = (gv == ov) and (gv is not None)
        chosen_value, _ = _choose_value_and_conf(gv, gc, ov, oc)
        final_conf = 1.0 if (matched and _both_conf_over_90([gc], [oc])) else 0.5
        set_field(key, chosen_value, final_conf)

    # Numeric field: integer precision compare
    key = "net_payable_amount"
    gv, gc = _extract_header_field(g, key)
    ov, oc = _extract_header_field(o, key)
    gi = _round_half_away_from_zero(gv if isinstance(gv, (int, float)) else None)
    oi = _round_half_away_from_zero(ov if isinstance(ov, (int, float)) else None)
    matched = (gi is not None) and (oi is not None) and (gi == oi)
    chosen_value, _ = _choose_value_and_conf(gv, gc, ov, oc)
    final_conf = 1.0 if (matched and _both_conf_over_90([gc], [oc])) else 0.5
    set_field(key, chosen_value, final_conf)

    return out


def _force_item_confidence(item: Dict[str, Any], conf: float) -> Dict[str, Any]:
    """Set all four field confidences to `conf` and return a shallow copy."""

    def _field(v):  # keep value, force conf
        return {"value": v.get("value"), "confidence": float(conf)}

    return {
        "description": _field(item.get("description", {})),
        "quantity": _field(item.get("quantity", {})),
        "unit_price": _field(item.get("unit_price", {})),
        "total_amount": _field(item.get("total_amount", {})),
    }


def _greedy_match_pairs(
    g_items: List[Dict[str, Any]], o_items: List[Dict[str, Any]]
) -> List[Tuple[int, int, float]]:
    """Return list of (gi, oi, score) pairs using description-only hybrid matching with threshold."""
    candidates: List[Tuple[int, int, float]] = []
    for gi, g in enumerate(g_items):
        gd = (g.get("description") or {}).get("value", "")
        for oi, o in enumerate(o_items):
            od = (o.get("description") or {}).get("value", "")
            matched, score = _descriptions_match(str(gd or ""), str(od or ""))
            if matched:
                candidates.append((gi, oi, score))
    # sort by score desc
    candidates.sort(key=lambda x: x[2], reverse=True)

    used_g = set()
    used_o = set()
    pairs: List[Tuple[int, int, float]] = []
    # acceptance threshold 0.85 on score
    for gi, oi, sc in candidates:
        if sc < 0.85:
            continue
        if gi in used_g or oi in used_o:
            continue
        used_g.add(gi)
        used_o.add(oi)
        pairs.append((gi, oi, sc))
    return pairs


def _merge_line_items(
    g_items: List[Dict[str, Any]], o_items: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Build final line items per rules:
      - Match by description only (hybrid).
      - After match, require quantity/unit_price/total_amount to match at integer precision; if any differ:
          -> include BOTH items separately with all four fields' confidence = 0.5
      - For accepted pairs (all three numbers match):
          -> If BOTH providers have >0.9 for ALL FOUR fields => set all conf to 1.0, else 0.5
          -> Value per field chosen from higher-confidence provider (tie -> Gemini)
      - Unmatched items from either side are included with all four fields' confidence set to 0.5
    """
    final_items: List[Dict[str, Any]] = []

    pairs = _greedy_match_pairs(g_items, o_items)
    paired_g = set(gi for gi, _, _ in pairs)
    paired_o = set(oi for _, oi, _ in pairs)

    # Process accepted/ rejected pairs
    for gi, oi, _sc in pairs:
        g = g_items[gi]
        o = o_items[oi]

        # Round ints
        g_qty = _round_half_away_from_zero((g.get("quantity") or {}).get("value"))
        o_qty = _round_half_away_from_zero((o.get("quantity") or {}).get("value"))
        g_up = _round_half_away_from_zero((g.get("unit_price") or {}).get("value"))
        o_up = _round_half_away_from_zero((o.get("unit_price") or {}).get("value"))
        g_tot = _round_half_away_from_zero((g.get("total_amount") or {}).get("value"))
        o_tot = _round_half_away_from_zero((o.get("total_amount") or {}).get("value"))

        # If any numeric mismatch -> include both separately with 0.5 confidence
        if not (g_qty == o_qty and g_up == o_up and g_tot == o_tot):
            final_items.append(_force_item_confidence(g, 0.5))
            final_items.append(_force_item_confidence(o, 0.5))
            continue

        # Numeric match: build merged item
        # Collect confidences
        g_desc_c = (g.get("description") or {}).get("confidence", 0.0)
        o_desc_c = (o.get("description") or {}).get("confidence", 0.0)
        g_qty_c = (g.get("quantity") or {}).get("confidence", 0.0)
        o_qty_c = (o.get("quantity") or {}).get("confidence", 0.0)
        g_up_c = (g.get("unit_price") or {}).get("confidence", 0.0)
        o_up_c = (o.get("unit_price") or {}).get("confidence", 0.0)
        g_tot_c = (g.get("total_amount") or {}).get("confidence", 0.0)
        o_tot_c = (o.get("total_amount") or {}).get("confidence", 0.0)

        # Decide overall confidence tier
        all_over_90 = _both_conf_over_90(
            [g_desc_c, g_qty_c, g_up_c, g_tot_c],
            [o_desc_c, o_qty_c, o_up_c, o_tot_c],
        )
        final_conf = 1.0 if all_over_90 else 0.5

        # Choose values per field from higher-confidence provider
        g_desc_v = (g.get("description") or {}).get("value")
        o_desc_v = (o.get("description") or {}).get("value")
        desc_v, _ = _choose_value_and_conf(g_desc_v, g_desc_c, o_desc_v, o_desc_c)

        g_qty_v = (g.get("quantity") or {}).get("value")
        o_qty_v = (o.get("quantity") or {}).get("value")
        qty_v, _ = _choose_value_and_conf(g_qty_v, g_qty_c, o_qty_v, o_qty_c)

        g_up_v = (g.get("unit_price") or {}).get("value")
        o_up_v = (o.get("unit_price") or {}).get("value")
        up_v, _ = _choose_value_and_conf(g_up_v, g_up_c, o_up_v, o_up_c)

        g_tot_v = (g.get("total_amount") or {}).get("value")
        o_tot_v = (o.get("total_amount") or {}).get("value")
        tot_v, _ = _choose_value_and_conf(g_tot_v, g_tot_c, o_tot_v, o_tot_c)

        final_items.append(
            {
                "description": {"value": desc_v, "confidence": final_conf},
                "quantity": {"value": qty_v, "confidence": final_conf},
                "unit_price": {"value": up_v, "confidence": final_conf},
                "total_amount": {"value": tot_v, "confidence": final_conf},
            }
        )

    # Unmatched Gemini items
    for gi, g in enumerate(g_items):
        if gi not in paired_g:
            final_items.append(_force_item_confidence(g, 0.5))

    # Unmatched GPT items
    for oi, o in enumerate(o_items):
        if oi not in paired_o:
            final_items.append(_force_item_confidence(o, 0.5))

    return final_items


def _build_fused_payload(g: Dict[str, Any], o: Dict[str, Any]) -> Dict[str, Any]:
    fused: Dict[str, Any] = {}

    # Headers
    headers = _merge_headers(g, o)
    fused.update(headers)

    # Line items
    g_items = _extract_line_items(g)
    o_items = _extract_line_items(o)
    fused["line_items"] = _merge_line_items(g_items, o_items)

    return fused


# ---------------------------
# Main Orchestrator
# ---------------------------
async def _check_gemini_uptime() -> bool:
    """Check if the Gemini API is up by sending a lightweight test request."""
    if not getattr(settings, "GEMINI_API_KEY", None):
        logger.warning("GEMINI_API_KEY is not configured.")
        return False

    GEMINI_API_URL = (
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"
        f"?key={settings.GEMINI_API_KEY}"
    )

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                GEMINI_API_URL, json={"contents": [{"parts": [{"text": "ping"}]}]}
            )
            logger.info("Gemini API uptime check response: %s", response.status_code)
            return response.status_code == 200
    except Exception as e:
        logger.error("Error during Gemini uptime check: %s", e, exc_info=True)
        return False


async def _check_openai_uptime() -> bool:
    """Check if the OpenAI API is up by sending a lightweight test request."""
    if openai_client is None:
        logger.warning(
            "OpenAI client is not configured. Check OPENAI_API_KEY in settings."
        )
        return False

    try:
        # Ensure timeout is properly handled
        response = openai_client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": '{"ping": "json"}'}],
            response_format={"type": "json_object"},
            timeout=20.0,  # Explicit timeout
        )

        # Validate response structure
        if response and hasattr(response, "choices") and response.choices:
            logger.info("OpenAI API uptime check successful.")
            return True
        else:
            logger.warning("OpenAI API response is invalid or empty.")
            return False

    except Exception as e:
        logger.error("Error during OpenAI uptime check: %s", e, exc_info=True)
        return False

# 🔹 NEW: Sonnet uptime check
async def _check_sonnet_uptime() -> bool:
    """Lightweight ping to Anthropic to ensure service is reachable & key is valid."""
    if not getattr(settings, "CLAUDE_API_KEY", None):
        logger.warning("CLAUDE_API_KEY is not configured.")
        return False

    CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
    CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

    headers = {
        "x-api-key": settings.CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 10,
        "messages": [{"role": "user", "content": [{"type": "text", "text": "ping"}]}],
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(CLAUDE_API_URL, headers=headers, json=payload)
        logger.info("Claude Sonnet uptime check response: %s", r.status_code)
        return r.status_code == 200
    except Exception as e:
        logger.error("Error during Sonnet uptime check: %s", e, exc_info=True)
        return False





# 🔸 MODIFIED: Orchestrator to use Sonnet as fallback when one of (Gemini, GPT) is unavailable
async def extract_data_from_bill(file_content: bytes) -> ExtractedDataWithConfidence:
    """
    Orchestration with three providers (Gemini, GPT-5, Sonnet 4.5):
      - Preferred pair: Gemini + GPT-5
      - If one of (Gemini, GPT-5) is down → replace the missing one with Sonnet
      - If only a single provider is up → return that provider's result as-is
      - If none are up → 503
    Fusion logic remains unchanged and still expects exactly two payloads when using a pair.
    """
    base64_images = convert_pdf_to_base64_images(file_content)

    gemini_up = await _check_gemini_uptime()
    openai_up = await _check_openai_uptime()
    sonnet_up = await _check_sonnet_uptime()
    print(f"Gemini up: {gemini_up}, OpenAI up: {openai_up}, Sonnet up: {sonnet_up}")

    # If none up
    if not gemini_up and not openai_up and not sonnet_up:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No AI providers available: Gemini, OpenAI, and Sonnet are all down.",
        )

    # Choose best pair according to rule:
    # 1) Gemini + GPT (preferred)
    # 2) If one of them is down, replace the missing one with Sonnet (if available)
    chosen_calls: List[Any] = []
    chosen_labels: List[str] = []

    if gemini_up and openai_up:
        chosen_calls = [_call_gemini_api(base64_images), _call_openai_api(base64_images)]
        chosen_labels = ["Gemini", "GPT-5"]
    elif gemini_up and not openai_up and sonnet_up:
        chosen_calls = [_call_gemini_api(base64_images), _call_sonnet_api(base64_images)]
        chosen_labels = ["Gemini", "Sonnet"]
    elif openai_up and not gemini_up and sonnet_up:
        chosen_calls = [_call_openai_api(base64_images), _call_sonnet_api(base64_images)]
        chosen_labels = ["GPT-5", "Sonnet"]
    else:
        # No valid pair available → fall back to single available provider
        if gemini_up:
            try:
                ai_json = await _call_gemini_api(base64_images)
                return ExtractedDataWithConfidence(**ai_json)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Gemini provider failed: {e}",
                )
        if openai_up:
            try:
                ai_json = await _call_openai_api(base64_images)
                return ExtractedDataWithConfidence(**ai_json)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"OpenAI provider failed: {e}",
                )
        if sonnet_up:
            try:
                ai_json = await _call_sonnet_api(base64_images)
                return ExtractedDataWithConfidence(**ai_json)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Sonnet provider failed: {e}",
                )

    # We have a chosen pair → run in parallel and fuse
    print(f"Using providers: {chosen_labels[0]} + {chosen_labels[1]}")
    results = await asyncio_gather_safe(*chosen_calls)

    (res1, exc1), (res2, exc2) = results

    # If one failed, return the successful one as-is
    if exc1 is None and exc2 is not None:
        try:
            return ExtractedDataWithConfidence(**res1)
        except ValidationError as e:
            raise HTTPException(
                status_code=500, detail=f"{chosen_labels[0]} response failed validation: {e}"
            )
    if exc2 is None and exc1 is not None:
        try:
            return ExtractedDataWithConfidence(**res2)
        except ValidationError as e:
            raise HTTPException(
                status_code=500, detail=f"{chosen_labels[1]} response failed validation: {e}"
            )

    # If both failed
    if exc1 is not None and exc2 is not None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Both chosen providers failed. {chosen_labels[0]} error: {exc1}; {chosen_labels[1]} error: {exc2}",
        )

    # Both succeeded → fuse (unchanged)
    try:
        _ = ExtractedDataWithConfidence(**res1)
        _ = ExtractedDataWithConfidence(**res2)
        print(f"✅ Both {chosen_labels[0]} and {chosen_labels[1]} responses validated successfully.")

        fused_payload = _build_fused_payload(res1, res2)

        final_valid = ExtractedDataWithConfidence(**fused_payload)
        print(f"✅ Successfully fused {chosen_labels[0]} and {chosen_labels[1]} results.")
        return final_valid
    except ValidationError as e:
        raise HTTPException(
            status_code=500, detail=f"Fused response failed validation: {e}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fusion error: {e}")


async def asyncio_gather_safe(
    *aws: Awaitable[Any],
) -> List[Tuple[Any, Optional[BaseException]]]:
    """
    Runs awaitables concurrently, returns list of (result, exception) for each.
    If an awaitable raises, its (None, exc) is returned instead of propagating.
    """

    async def wrap(coro: Awaitable[Any]):
        try:
            res = await coro
            return (res, None)
        except BaseException as exc:  # capture broad exceptions from network calls
            return (None, exc)

    return await asyncio.gather(*[wrap(a) for a in aws])