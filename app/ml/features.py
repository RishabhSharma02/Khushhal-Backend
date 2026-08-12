"""Turns a Business + its ledger history into a FeatureContext.

Heuristics live here (not in `pipeline.py`) so the ML wrapper stays focused
on inference and the derivations can be revisited without touching the
model surface.
"""
from __future__ import annotations

import calendar
import math
from collections.abc import Iterable
from datetime import date, datetime, timezone

from app.external.feeds import climate_feed, market_feed
from app.ml.pipeline import FeatureContext
from app.models.business import Business, BusinessSector
from app.models.ledger_entry import EntryKind, LedgerEntry
from app.models.monthly_snapshot import MonthlySnapshot
from app.models.user import User


_SECTOR_TO_ML = {
    BusinessSector.dairy: "dairy",
    BusinessSector.poultry: "poultry",
    BusinessSector.food_processing: "food_processing",
    BusinessSector.handicrafts: "handicrafts",
    BusinessSector.rural_retail: "rural_retail",
    # No trained model for "other" — bucket into rural_retail as the closest
    # generic small-business sector.
    BusinessSector.other: "rural_retail",
}


def _first_of_month(d: date) -> date:
    return d.replace(day=1)


def _monthly_bucket(entries: Iterable[LedgerEntry], window_months: int = 6) -> dict[date, tuple[int, int, int]]:
    """Aggregate (money_in, money_out, days_with_activity) per month, keyed by
    first-of-month. Only keeps the trailing `window_months`.
    """
    buckets: dict[date, dict] = {}
    for e in entries:
        d = e.recorded_at.astimezone(timezone.utc).date()
        key = d.replace(day=1)
        b = buckets.setdefault(key, {"in": 0, "out": 0, "days": set()})
        if e.kind == EntryKind.in_:
            b["in"] += e.amount_inr
        else:
            b["out"] += e.amount_inr
        b["days"].add(d)

    out: dict[date, tuple[int, int, int]] = {}
    for k, v in buckets.items():
        out[k] = (v["in"], v["out"], len(v["days"]))
    if not out:
        return out
    latest = max(out.keys())
    cutoff = _first_of_month(date(latest.year, latest.month, 1))
    # keep window_months buckets
    keep = sorted(out.keys())[-window_months:]
    return {k: out[k] for k in keep}


def build_feature_context(
    *,
    business: Business,
    user: User,
    snapshot: MonthlySnapshot | None,
    entries: list[LedgerEntry],
    as_on: date,
) -> FeatureContext:
    """Compose a FeatureContext for `stamp_month(business, as_on=...)`.

    Missing fields fall back to the snapshot (from setup) and then to safe
    zeros — the sector template in `pipeline.py` fills exogenous features
    (rainfall, seasonality, price indices) with neutral defaults.
    """
    # Baseline from setup (design 1m/1n) — represents what the owner said
    # a typical month looks like.
    monthly_income = float(snapshot.money_in) if snapshot else None
    monthly_expenditure = float(snapshot.money_out) if snapshot else None
    emi_amount = float(snapshot.loan_emi) if snapshot else 0.0
    savings_amount = float(user.savings_inr) if user.savings_inr else (float(snapshot.savings) if snapshot else 0.0)
    loan_outstanding = float(user.loan_inr)

    # Recent ledger — if we have data, prefer the observed monthly averages
    # over the setup snapshot.
    buckets = _monthly_bucket(entries)
    days_written = 0
    if buckets:
        current_month = _first_of_month(as_on)
        cur = buckets.get(current_month)
        days_written = cur[2] if cur else 0
        totals_in = [b[0] for b in buckets.values()]
        totals_out = [b[1] for b in buckets.values()]
        avg_in = sum(totals_in) / len(totals_in)
        avg_out = sum(totals_out) / len(totals_out)
        if avg_in > 0:
            monthly_income = avg_in
        if avg_out > 0:
            monthly_expenditure = avg_out

    has_loan = 1 if (loan_outstanding and loan_outstanding > 0) or emi_amount > 0 else 0

    monthly_income = monthly_income or 0.0
    monthly_expenditure = monthly_expenditure or 0.0
    net_cf_now = monthly_income - monthly_expenditure - emi_amount
    margin_now = (net_cf_now / monthly_income) if monthly_income > 0 else 0.0
    expense_ratio = (monthly_expenditure / monthly_income) if monthly_income > 0 else 0.0
    savings_months = (savings_amount / monthly_expenditure) if monthly_expenditure > 0 else 0.0
    debt_to_income = (loan_outstanding / (monthly_income * 12)) if monthly_income > 0 else 0.0
    debt_service_cov = (net_cf_now / emi_amount) if emi_amount > 0 else None
    emi_burden = (emi_amount / monthly_income) if monthly_income > 0 else 0.0
    log_income = math.log(monthly_income + 1.0)

    days_in_month = calendar.monthrange(as_on.year, as_on.month)[1]

    # External feeds — v1 neutral, real feeds swap in via
    # `app.external.feeds.{climate_feed,market_feed}`.
    climate = climate_feed.signal_for(state=user.state, district=user.district)
    market = market_feed.signal_for(sector=_SECTOR_TO_ML[business.sector])

    return FeatureContext(
        business_id=business.id,
        sector=_SECTOR_TO_ML[business.sector],
        assessment_month=_first_of_month(as_on),
        monthly_income=monthly_income,
        monthly_expenditure=monthly_expenditure,
        savings_amount=savings_amount,
        loan_outstanding=loan_outstanding,
        emi_amount=emi_amount,
        has_loan=has_loan,
        is_new_business=int(business.is_new_business),
        years_in_operation=business.years_in_operation,
        net_cf_now=net_cf_now,
        margin_now=margin_now,
        savings_months=savings_months,
        debt_service_cov=debt_service_cov,
        debt_to_income=debt_to_income,
        expense_ratio=expense_ratio,
        emi_burden=emi_burden,
        log_income=log_income,
        days_written=days_written,
        days_in_month=days_in_month,
        extras={
            "rain_dev_yr_min": climate.rain_dev_yr_min,
            "rain_dev_yr_max": climate.rain_dev_yr_max,
            "tot_chg_3m_min": market.tot_chg_3m_min,
        },
    )


def score_from_probs(p_green: float, p_amber: float, p_red: float) -> int:
    """0..100 health score derived from class probabilities.

    Simple weighted sum — green is a full score, amber is half, red is zero.
    Deterministic so we can back-fill / re-stamp without drift.
    """
    raw = 1.0 * p_green + 0.5 * p_amber + 0.0 * p_red
    return int(round(100 * raw))
