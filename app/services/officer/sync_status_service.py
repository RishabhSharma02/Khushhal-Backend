"""Officer portal "data sync" triage — device sync/entry freshness derived
from the existing `sync_events` and `ledger_entries` tables (read-only, no
new table). No signal exists anywhere upstream for entries an app has saved
offline but not yet uploaded, so `pending_estimate_label` is honestly
"unknown" rather than a fabricated number.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import Business
from app.models.user import User
from app.repositories.officer import assignments as assignments_repo
from app.repositories.officer import enterprises as enterprises_repo
from app.repositories.officer import sync_events as sync_events_repo
from app.schemas.officer.sync_status import DeviceSyncStatusRead, SyncStatusSummary


def _days_since(dt: datetime | None, fallback_date: date) -> int:
    if dt is None:
        return max((datetime.now(timezone.utc).date() - fallback_date).days, 0)
    return max((datetime.now(timezone.utc) - dt).days, 0)


def _sync_hours(last_sync: datetime | None, fallback_date: date) -> float:
    if last_sync is None:
        return _days_since(None, fallback_date) * 24.0
    return (datetime.now(timezone.utc) - last_sync).total_seconds() / 3600


def _derive_cause(*, has_synced: bool, sync_days: int, entry_days: int) -> tuple[str, str, str]:
    if not has_synced:
        return "No sync recorded yet — check the device is logged in", "resendLogin", "📩 Re-login link"
    if sync_days <= 1 and entry_days >= 5:
        return "Syncing but not entering — re-train entry habit", "addToRoute", "🗓 Add to visit"
    if sync_days >= 7:
        return "No recent activity — device may be offline or unused", "call", "📞 Call"
    return "Entries slowing down — worth a check-in", "addToRoute", "🗓 Add to visit"


async def get_sync_status(db: AsyncSession, officer_id: int) -> SyncStatusSummary:
    business_ids = await assignments_repo.list_assigned_business_ids(db, officer_id)

    under_24h = one_to_seven = stale_7_plus = entry_gap_5_plus = 0
    rows: list[DeviceSyncStatusRead] = []

    for business_id in business_ids:
        pair = await enterprises_repo.get_business_with_owner(db, business_id)
        if pair is None:
            continue
        business: Business
        user: User
        business, user = pair

        last_sync = await sync_events_repo.last_sync_at(db, user.id)
        last_entry = await enterprises_repo.last_entry_at(db, business_id)

        sync_hours = _sync_hours(last_sync, business.creation_date.date())
        sync_days = int(sync_hours // 24)
        entry_days = _days_since(last_entry, business.creation_date.date())

        if sync_hours < 24:
            under_24h += 1
        elif sync_hours < 24 * 7:
            one_to_seven += 1
        else:
            stale_7_plus += 1
        if entry_days >= 5:
            entry_gap_5_plus += 1

        if sync_days >= 7 or entry_days >= 5:
            cause, action_kind, action_label = _derive_cause(
                has_synced=last_sync is not None, sync_days=sync_days, entry_days=entry_days,
            )
            rows.append(
                DeviceSyncStatusRead(
                    enterprise_id=str(business.id),
                    enterprise_name=business.name,
                    village=user.village or "",
                    last_sync_days=sync_days,
                    last_entry_days=entry_days,
                    pending_estimate_label="unknown",
                    likely_cause=cause,
                    action_kind=action_kind,
                    action_label=action_label,
                )
            )

    rows.sort(key=lambda r: (-r.last_sync_days, -r.last_entry_days))

    return SyncStatusSummary(
        synced_under_24h_count=under_24h,
        synced_1_to_7_days_count=one_to_seven,
        synced_stale_7_plus_count=stale_7_plus,
        entry_gap_5_plus_count=entry_gap_5_plus,
        rows=rows,
    )
