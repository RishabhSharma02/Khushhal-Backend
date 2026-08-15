"""
Risk-action engine (Step 3 of the pipeline).

Given a predicted risk BAND (green/amber/red, from the classifier), the enterprise
SECTOR, and its current-state CONTEXT, return the actionables an owner and a field
officer should take -- straight from risk_action_framework.json:

  * sector + band actions   (sector_band_actions[sector][band])
  * driver overlays         (extra actions when a specific stress condition fires)

Trigger conditions are implemented exactly as documented in the framework JSON.
"""
import json, os

_HERE = os.path.dirname(os.path.abspath(__file__))
FRAMEWORK = json.load(open(os.path.join(_HERE, "artifacts", "risk_action_framework.json")))


def get_actionables(sector, band, ctx):
    """
    sector : dairy | poultry | food_processing | handicrafts | rural_retail
    band   : green | amber | red   (output of the classification model)
    ctx    : dict with any of
             savings_months, debt_service_cov, rain_dev_yr_min, rain_dev_yr_max,
             tot_chg_3m_min, is_new_business, years_in_operation
    Returns a structured dict of owner + field-officer actionables.
    """
    # Unknown sectors (e.g. BusinessSector.other) fall back to rural_retail
    # so the alerts API still returns a playbook instead of empty actions.
    sector_key = sector if sector in FRAMEWORK["sector_band_actions"] else "rural_retail"
    sba = FRAMEWORK["sector_band_actions"].get(sector_key, {}).get(band, {})
    result = {
        "sector": sector,
        "band": band,
        "owner_actions": list(sba.get("owner", [])),
        "field_officer_actions": list(sba.get("field_officer", [])),
        "triggered_overlays": [],
    }

    ov = FRAMEWORK["driver_overlays"]

    def fire(name):
        o = ov[name]
        result["triggered_overlays"].append({
            "driver": name,
            "owner_action": list(o.get("owner_action", [])),
            "field_officer_action": list(o.get("field_officer_action", [])),
        })

    sm   = ctx.get("savings_months")
    dscr = ctx.get("debt_service_cov")
    has_loan = ctx.get("has_loan")
    rmin = ctx.get("rain_dev_yr_min")
    rmax = ctx.get("rain_dev_yr_max")
    tmin = ctx.get("tot_chg_3m_min")
    newb = ctx.get("is_new_business")
    yrs  = ctx.get("years_in_operation")

    # driver overlays -- conditions per the framework's liquidity axis: the
    # debt-service test only applies when the enterprise actually has a loan.
    low_savings = sm is not None and sm < 1
    weak_dscr   = has_loan == 1 and dscr is not None and dscr < 0.75
    if low_savings or weak_dscr:
        fire("liquidity_debt_stress")
    if rmin is not None and rmin <= -27:
        fire("climate_stress_deficit")
    if rmax is not None and rmax >= 31:
        fire("climate_stress_excess")
    if tmin is not None and tmin <= -0.10:
        fire("market_stress")
    if newb == 1 or (yrs is not None and yrs <= 1):
        fire("new_business")

    return result


if __name__ == "__main__":
    demo = get_actionables("rural_retail", "red",
                           {"savings_months": 0.6, "debt_service_cov": 0.5,
                            "tot_chg_3m_min": -0.15, "is_new_business": 0,
                            "years_in_operation": 5})
    print(json.dumps(demo, indent=2))
