"""Dev-only: provision a test officer so Phase 0 can be exercised end-to-end
before a real Firebase project (and admin-provisioning tool) exists.

Usage:
    .venv/bin/python -m scripts.seed_officer \
        --firebase-uid dev-officer-1 --employee-id EMP001 \
        --full-name "Ramesh Verma" --mobile +919876543210

Refuses to run unless DEV_TOOLS_ENABLED=true, mirroring the rest of the
codebase's dev-tool gating.
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.officer import Officer
from app.repositories.officer import officers as officers_repo


async def _seed(args: argparse.Namespace) -> None:
    settings = get_settings()
    if not settings.dev_tools_enabled:
        print("Refusing to seed: DEV_TOOLS_ENABLED is not true.", file=sys.stderr)
        raise SystemExit(1)

    async with SessionLocal() as db:
        existing = await officers_repo.get_by_firebase_uid(db, args.firebase_uid)
        if existing is not None:
            print(f"Officer already exists: id={existing.id} employee_id={existing.employee_id}")
            return

        officer = Officer(
            firebase_uid=args.firebase_uid,
            employee_id=args.employee_id,
            employee_id_verified=True,
            mobile_e164=args.mobile,
            full_name=args.full_name,
            pincode=args.pincode,
            block=args.block,
            state=args.state,
        )
        db.add(officer)
        await db.flush()
        officer.created_by = officer.id
        officer.updated_by = officer.id
        await db.commit()
        print(f"Seeded officer: id={officer.id} employee_id={officer.employee_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firebase-uid", required=True)
    parser.add_argument("--employee-id", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--mobile", required=True, help="E.164 format, e.g. +919876543210")
    parser.add_argument("--pincode", default=None)
    parser.add_argument("--block", default=None)
    parser.add_argument("--state", default=None)
    args = parser.parse_args()
    asyncio.run(_seed(args))


if __name__ == "__main__":
    main()
