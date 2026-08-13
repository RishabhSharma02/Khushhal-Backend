"""Runtime wrapper around the trained NABARD risk pipeline.

Mirrors `pipeline/run_full_pipeline.py` but scores one enterprise at a time
from live app state instead of the training CSV:

    build_feature_context(business, snapshot, entries)
        → FeatureContext
    score(FeatureContext)
        → ScoreResult { cf_h1..cf_h6, band, probs, actionables }

Models load once at process start via `load_models()`; inference is
CPU-bound sklearn/LightGBM and must be called from a thread-pool by any
async caller (`asyncio.to_thread` is fine).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.ml.risk_actions import get_actionables

_HERE = os.path.dirname(os.path.abspath(__file__))
_ART = os.path.join(_HERE, "artifacts")

REG_PATH = os.path.join(_ART, "combined_model.pkl")
BAND_PATH = os.path.join(_ART, "band_classifier_extended.joblib")
TEMPLATES_PATH = os.path.join(_ART, "sector_templates.json")

MODEL_VERSION = "nabard-coldstart-v1"


@dataclass
class _Models:
    regression: Any
    features_reg: list[str]
    band_model: Any
    band_features: list[str]
    templates: dict


_bundle: _Models | None = None


def load_models() -> _Models:
    """Idempotent — safe to call from lifespan and tests."""
    global _bundle
    if _bundle is not None:
        return _bundle
    reg_pkg = joblib.load(REG_PATH)
    band_pkg = joblib.load(BAND_PATH)
    with open(TEMPLATES_PATH) as f:
        templates = json.load(f)
    _bundle = _Models(
        regression=reg_pkg["regression"],
        features_reg=list(reg_pkg["features_reg"]),
        band_model=band_pkg["model"],
        band_features=list(band_pkg["feature_columns"]),
        templates=templates,
    )
    return _bundle


@dataclass
class FeatureContext:
    """Everything the pipeline needs about one business at one assessment.

    Populated by `app/ml/features.py::build_feature_context`.
    """
    business_id: int
    sector: str  # dairy | poultry | food_processing | handicrafts | rural_retail
    assessment_month: date

    # User-derived overrides (all optional — templates fill anything missing).
    monthly_income: float | None = None
    monthly_expenditure: float | None = None
    savings_amount: float | None = None
    loan_outstanding: float | None = None
    emi_amount: float | None = None
    has_loan: int = 0
    is_new_business: int = 0
    years_in_operation: int = 0

    # Derived cash-flow snapshot for the current period.
    net_cf_now: float | None = None
    margin_now: float | None = None
    savings_months: float | None = None
    debt_service_cov: float | None = None
    debt_to_income: float | None = None
    expense_ratio: float | None = None
    emi_burden: float | None = None
    log_income: float | None = None

    # Days tracked this month, for the health-card meta.
    days_written: int = 0
    days_in_month: int = 30

    # Extras that risk_actions consumes but the models do not.
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class Overlay:
    driver: str
    owner_action: list[str]
    field_officer_action: list[str]


@dataclass
class ScoreResult:
    band: str  # green | amber | red
    p_green: float
    p_amber: float
    p_red: float
    forecast: list[float]  # 6 monthly cf preds
    owner_actions: list[str]
    field_officer_actions: list[str]
    overlays: list[Overlay]
    model_version: str = MODEL_VERSION


# ---------------- internal helpers ----------------

def _template_row(templates: dict, sector: str, horizon: int) -> dict:
    numeric = templates["numeric_by_sector_horizon"].get(sector)
    if numeric is None:
        # Fall back to the "other" or any sector if unknown.
        numeric = next(iter(templates["numeric_by_sector_horizon"].values()))
    return dict(numeric[str(horizon)])


def _apply_ctx_overrides(row: dict, ctx: FeatureContext, horizon: int) -> dict:
    """Overlay user-derived values on top of the sector template."""
    row = dict(row)
    row["horizon"] = float(horizon)
    row["years_in_operation"] = float(ctx.years_in_operation)
    row["is_new_business"] = float(ctx.is_new_business)
    row["has_loan"] = float(ctx.has_loan)

    if ctx.monthly_income is not None:
        row["monthly_income"] = float(ctx.monthly_income)
    if ctx.monthly_expenditure is not None:
        row["monthly_expenditure"] = float(ctx.monthly_expenditure)
    if ctx.savings_amount is not None:
        row["savings_amount"] = float(ctx.savings_amount)
    if ctx.loan_outstanding is not None:
        row["loan_outstanding"] = float(ctx.loan_outstanding)
    if ctx.emi_amount is not None:
        row["emi_amount"] = float(ctx.emi_amount)

    for k in ("net_cf_now", "margin_now", "savings_months", "debt_service_cov",
              "debt_to_income", "expense_ratio", "emi_burden", "log_income"):
        v = getattr(ctx, k)
        if v is not None:
            row[k] = float(v)
    return row


def _band_ctx(ctx: FeatureContext) -> dict:
    """Context handed to `risk_actions.get_actionables` — merges climate /
    market extras from the injected feeds (neutral by default).
    """
    return dict(
        savings_months=ctx.savings_months,
        debt_service_cov=ctx.debt_service_cov,
        has_loan=int(ctx.has_loan),
        rain_dev_yr_min=ctx.extras.get("rain_dev_yr_min", 0.0),
        rain_dev_yr_max=ctx.extras.get("rain_dev_yr_max", 0.0),
        tot_chg_3m_min=ctx.extras.get("tot_chg_3m_min", 0.0),
        is_new_business=int(ctx.is_new_business),
        years_in_operation=int(ctx.years_in_operation),
    )


# ---------------- public scoring ----------------

def score(ctx: FeatureContext) -> ScoreResult:
    bundle = load_models()

    # Step 1 — build a 6-row frame (one per horizon) using the sector
    # template as baseline and layering user data on top.
    rows = []
    for h in range(1, 7):
        base = _template_row(bundle.templates, ctx.sector, h)
        rows.append(_apply_ctx_overrides(base, ctx, h))
    df = pd.DataFrame(rows)
    df["sector"] = ctx.sector

    # Ensure every regression feature is present (fill missing with 0.0).
    for col in bundle.features_reg:
        if col not in df.columns:
            df[col] = 0.0
    x_reg = df[bundle.features_reg].astype(float)
    cf = bundle.regression.predict(x_reg)
    cf = [float(v) for v in cf]

    # Step 2 — engineered stats + band classifier.
    cf_np = np.asarray(cf, dtype=float)
    weights = np.arange(1, 7) - 3.5
    engineered = {
        f"cf_h{h}": cf_np[h - 1] for h in range(1, 7)
    }
    engineered.update({
        "mean": float(cf_np.mean()),
        "std": float(cf_np.std()),
        "min": float(cf_np.min()),
        "max": float(cf_np.max()),
        "slope": float((cf_np @ weights) / 17.5),
        "cumsum": float(cf_np.sum()),
        "n_negative_months": int((cf_np < 0).sum()),
        "first3_avg": float(cf_np[:3].mean()),
        "last3_avg": float(cf_np[3:].mean()),
        "momentum": float(cf_np[3:].mean() - cf_np[:3].mean()),
        "savings_months": float(ctx.savings_months or 0.0),
        "debt_service_cov": float(ctx.debt_service_cov or 0.0),
        "has_loan": float(ctx.has_loan),
    })

    x_band = pd.DataFrame([engineered])
    for col in bundle.band_features:
        if col not in x_band.columns:
            x_band[col] = 0.0
    x_band = x_band[bundle.band_features].astype(float)

    band = str(bundle.band_model.predict(x_band)[0])
    proba = bundle.band_model.predict_proba(x_band)[0]
    class_probs = {str(c): float(p) for c, p in zip(bundle.band_model.classes_, proba)}

    # Step 3 — actionables via the framework, unchanged from the training pipeline.
    act = get_actionables(ctx.sector, band, _band_ctx(ctx))

    overlays = [
        Overlay(
            driver=o["driver"],
            owner_action=list(o["owner_action"]),
            field_officer_action=list(o["field_officer_action"]),
        )
        for o in act["triggered_overlays"]
    ]

    return ScoreResult(
        band=band,
        p_green=class_probs.get("green", 0.0),
        p_amber=class_probs.get("amber", 0.0),
        p_red=class_probs.get("red", 0.0),
        forecast=cf,
        owner_actions=list(act["owner_actions"]),
        field_officer_actions=list(act["field_officer_actions"]),
        overlays=overlays,
    )
