
import json
import os
from functools import lru_cache

from fastapi import APIRouter

from app.core.exceptions import NotFoundError

router = APIRouter(tags=["locations"], prefix="/locations")

_HERE = os.path.dirname(os.path.abspath(__file__))
_REF = os.path.join(_HERE, "..", "..", "reference", "india_locations.json")


@lru_cache
def _load() -> dict:
    with open(_REF) as f:
        return json.load(f)


@router.get("/states")
async def list_states() -> list[dict]:
    """Returns [{code, name_en, name_hi}] for every state we ship dropdown data for.

    Auth-free on purpose — reference data is safe to serve pre-login (used
    by the setup wizard before a session exists).
    """
    data = _load()
    return [
        {"code": s["code"], "name_en": s["name_en"], "name_hi": s["name_hi"]}
        for s in data["states"]
    ]


@router.get("/states/{state_code}/districts")
async def list_districts(state_code: str) -> list[dict]:
    """Returns the districts we bundled for a state (English names only).

    Callers pass the two-letter state code from `/states` (case-insensitive).
    """
    data = _load()
    code = state_code.upper()
    for s in data["states"]:
        if s["code"] == code:
            return [{"name_en": d} for d in s["districts"]]
    raise NotFoundError(f"Unknown state code: {state_code}")
