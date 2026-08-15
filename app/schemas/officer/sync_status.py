from pydantic import BaseModel


class DeviceSyncStatusRead(BaseModel):
    enterprise_id: str
    enterprise_name: str
    village: str
    last_sync_days: int
    last_entry_days: int
    pending_estimate_label: str
    likely_cause: str
    action_kind: str
    action_label: str


class SyncStatusSummary(BaseModel):
    synced_under_24h_count: int
    synced_1_to_7_days_count: int
    synced_stale_7_plus_count: int
    entry_gap_5_plus_count: int
    rows: list[DeviceSyncStatusRead]
