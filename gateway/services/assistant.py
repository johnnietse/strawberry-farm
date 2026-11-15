"""
Research assistant: turns a researcher's free-text note ("aphids on the plants in row 3,
sprayed neem oil") into a structured research event for the research_events table.

Backends, tried in this order:
  1. "claude" if ANTHROPIC_API_KEY (or another Anthropic credential) is set: the Claude API with
     structured outputs (JSON schema), model ASSISTANT_MODEL (default claude-opus-5-5),
     low effort, server-side refusal fallback. Needs internet.
  2. "ollama" if OLLAMA_URL is set (for example http://ollama:11434): a small local model,
     OLLAMA_MODEL (default qwen2.5:1.5b, about 1 GB, runs on a Raspberry Pi 5 CPU;
     qwen2.5:0.5b was tested and put most notes in the wrong category), with
     Ollama's JSON-schema output. Works offline; nothing leaves the phytotron network.
  3. "rules": keyword rules. Always available.
A backend that fails falls through to the next, so the dashboard never loses the note.
Every result is validated against the same schema before it is used.
"""
from __future__ import annotations

import json
import logging
import os
import re

import requests

logger = logging.getLogger("Assistant")

EVENT_TYPES = ["PEST", "DISEASE", "FERTILIZER", "IRRIGATION", "EQUIPMENT_FAIL", "HARVEST",
               "PRUNING", "CLIMATE", "OBSERVATION"]

SCHEMA = {
    "type": "object",
    "properties": {
        "event_type": {"type": "string", "enum": EVENT_TYPES},
        "severity": {"type": "integer", "minimum": 1, "maximum": 5},
        "sector": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": ["event_type", "severity", "sector", "summary"],
    "additionalProperties": False,
}

SYSTEM = (
    "You file research notes from a strawberry phytotron as structured events. "
    "event_type: PEST (insects, mites), DISEASE (mould, mildew, rot, leaf spot), FERTILIZER "
    "(nutrients, EC/pH changes), IRRIGATION (watering, drippers), EQUIPMENT_FAIL (broken or "
    "offline hardware, sensors, LEDs), HARVEST, PRUNING (runners, leaves), CLIMATE (heat, cold, "
    "humidity, light problems), OBSERVATION (anything else). severity: 1 routine, 2 minor, "
    "3 needs attention, 4 serious, 5 critical (crop or equipment at risk now). sector: the row, "
    "bench, node or area named in the note, or \"unknown\". summary: one short sentence."
)

RULES = [
    ("PEST", 4, r"aphid|mite|thrip|whitefl|pest|insect|larva|caterpillar|slug"),
    ("DISEASE", 4, r"mou?ld|mildew|botrytis|rot\b|rotting|fung|leaf spot|blight|wilt"),
    ("EQUIPMENT_FAIL", 5, r"broken|fail|offline|dead|not working|fault|crash|leak"),
    ("FERTILIZER", 2, r"fertili[sz]|nutrient|\bec\b|\bph\b|feed|calcium|nitrogen|potassium"),
    ("IRRIGATION", 2, r"water|irrigat|dripper|drip line|flood|dry"),
    ("HARVEST", 1, r"harvest|picked|yield|fruit weight|brix"),
    ("PRUNING", 1, r"prun|runner|trim|deleaf|remove(d)? leaves"),
    ("CLIMATE", 3, r"\bhot\b|heat|cold|frost|humid|condensation|temperature|too bright|too dark"),
]
SECTOR = re.compile(r"\b(row|bench|sector|bay|node|table)\s*[-#]?\s*(\w+)", re.I)


def validate(event: dict) -> dict:
    if not isinstance(event, dict):
        raise ValueError("not an object")
    et = str(event.get("event_type", "")).upper()
    if et not in EVENT_TYPES:
        raise ValueError(f"unknown event_type {et!r}")
    sev = int(event.get("severity", 0))
    if not 1 <= sev <= 5:
        raise ValueError("severity must be 1..5")
    return {"event_type": et, "severity": sev,
            "sector": str(event.get("sector") or "unknown")[:40],
            "summary": str(event.get("summary") or "")[:300]}


def parse_rules(text: str) -> dict:
    low = text.lower()
    et, sev = "OBSERVATION", 1
    for name, s, pattern in RULES:
        if re.search(pattern, low):
            et, sev = name, s
            break
    if re.search(r"urgent|critical|everywhere|all plants|spreading|emergency", low):
        sev = min(5, sev + 1)
    m = SECTOR.search(text)
    sector = f"{m.group(1).lower()} {m.group(2)}" if m else "unknown"
    return {"event_type": et, "severity": sev, "sector": sector, "summary": text.strip()[:300]}


def parse_claude(text: str) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=os.getenv("ASSISTANT_MODEL", "claude-opus-5-5"),
        max_tokens=1024,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SYSTEM,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": text}],
    )
    if response.stop_reason == "refusal":
        raise ValueError("declined")
    body = next(b.text for b in response.content if b.type == "text")
    return validate(json.loads(body))


def parse_ollama(text: str) -> dict:
    url = os.environ["OLLAMA_URL"].rstrip("/") + "/api/chat"
    r = requests.post(url, timeout=float(os.getenv("OLLAMA_TIMEOUT_S", "60")), json={
        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"),
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}],
        "format": SCHEMA,
        "stream": False,
        "options": {"temperature": 0},
    })
    r.raise_for_status()
    return validate(json.loads(r.json()["message"]["content"]))


def has_claude_credentials() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def parse_note(text: str) -> tuple[dict, str]:
    """Structured event and the backend that produced it."""
    text = (text or "").strip()
    if not text:
        raise ValueError("empty note")
    backends = []
    if has_claude_credentials():
        backends.append(("claude", parse_claude))
    if os.getenv("OLLAMA_URL"):
        backends.append(("ollama", parse_ollama))
    explicit = SECTOR.search(text)
    for name, fn in backends:
        try:
            event = fn(text)
            if explicit:  # the place written in the note wins over the model's reading of it
                event["sector"] = f"{explicit.group(1).lower()} {explicit.group(2)}"
            return event, name
        except Exception as e:  # network, model, validation: try the next backend
            logger.warning(f"assistant backend {name} failed: {e}")
    return parse_rules(text), "rules"
