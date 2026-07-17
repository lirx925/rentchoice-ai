"""Supabase-first storage with a safe local CSV fallback."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import os, threading
import pandas as pd

DATA_DIR = Path("data")
FILES = {"participants": DATA_DIR/"local_participants.csv", "choices": DATA_DIR/"local_results.csv", "post_survey": DATA_DIR/"local_post_survey.csv"}
_LOCK = threading.Lock()

def _client():
    """Return a configured Supabase client, or None in demo mode."""
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
    if not url or not key: return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception:
        return None

def storage_mode() -> str:
    """Describe the active persistence backend."""
    return "Supabase" if _client() else "本地演示"

def _local_upsert(table: str, row: dict, keys: list[str]) -> None:
    """Insert or replace a local UTF-8 CSV record by key columns."""
    DATA_DIR.mkdir(exist_ok=True)
    path = FILES[table]
    with _LOCK:
        old = pd.read_csv(path) if path.exists() and path.stat().st_size else pd.DataFrame()
        new = pd.DataFrame([row])
        if not old.empty:
            mask = pd.Series(True, index=old.index)
            for key in keys: mask &= old[key].astype(str).eq(str(row[key]))
            old = old.loc[~mask]
        pd.concat([old, new], ignore_index=True).to_csv(path, index=False, encoding="utf-8-sig")

def _save(table: str, row: dict, keys: list[str]) -> None:
    client = _client()
    if client:
        try:
            client.table(table).upsert(row, on_conflict=",".join(keys)).execute(); return
        except Exception:
            pass
    _local_upsert(table, row, keys)

def save_participant(data: dict) -> None:
    """Persist one anonymized participant record."""
    row = {**data, "created_at": data.get("created_at", datetime.now(timezone.utc).isoformat())}
    _save("participants", row, ["participant_id"])

def save_choice(data: dict) -> None:
    """Persist one participant-round choice idempotently."""
    row = {**data, "created_at": data.get("created_at", datetime.now(timezone.utc).isoformat())}
    _save("choices", row, ["participant_id", "round_number"])

def save_post_survey(data: dict) -> None:
    """Persist one final survey idempotently."""
    row = {**data, "created_at": data.get("created_at", datetime.now(timezone.utc).isoformat())}
    _save("post_survey", row, ["participant_id"])

def load_all_results() -> dict[str, pd.DataFrame]:
    """Load all three experiment tables from Supabase or local CSV files."""
    client = _client()
    if client:
        try: return {t: pd.DataFrame(client.table(t).select("*").execute().data) for t in FILES}
        except Exception: pass
    return {t: pd.read_csv(p) if p.exists() and p.stat().st_size else pd.DataFrame() for t,p in FILES.items()}
