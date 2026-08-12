"""Hindi translations for the highest-frequency plan-action strings.

The framework has ~120 unique English strings; we ship a curated ~25 for the
driver overlays that fire most often (liquidity, climate, market, new-business).
The rest fall back to the English label — the frontend renders whatever
`label_hi` contains, falling back to `label_en` when null.

Extending this map is a copy job: add another `en → hi` line.
"""
from __future__ import annotations

_HI: dict[str, str] = {
    # liquidity_debt_stress
    "Set aside a fixed share of incoming cash toward rebuilding your buffer before any new spending.":
        "नई खर्च से पहले हर आय का एक तय हिस्सा अपने रिज़र्व में डालें।",
    "Talk to your lender early about restructuring if you have an existing loan.":
        "अगर कर्ज़ चल रहा है, तो बैंक से पहले ही पुनर्गठन के बारे में बात करें।",
    "Avoid taking on new debt until your buffer improves.":
        "जब तक बचत सुधरे नहीं, तब तक नया कर्ज़ न लें।",
    "Assess eligibility for repayment restructuring or a moratorium.":
        "पुनर्भुगतान पुनर्गठन या मोहलत की पात्रता जाँचें।",
    "Consider linking to a lower-cost credit product.":
        "कम ब्याज वाले कर्ज़ उत्पाद से जोड़ने पर विचार करें।",
    "Flag for close monitoring before default risk rises.":
        "डिफ़ॉल्ट का जोखिम बढ़ने से पहले कड़ी निगरानी के लिए चिह्नित करें।",

    # climate_stress_deficit
    "Plan input purchases early rather than buying at peak prices later.":
        "बाद में महँगे दामों की जगह इनपुट पहले ही खरीद लें।",
    "Check for local advisories on drought-resistant practices.":
        "स्थानीय सूखा-सहनशील खेती की सलाह देखें।",
    "Build a small reserve for potential feed/input price increases.":
        "चारा/इनपुट के दाम बढ़ने की स्थिति के लिए छोटा रिज़र्व बनाएँ।",
    "Cross-check with local agri/market advisory for input price movement.":
        "इनपुट कीमतों की स्थानीय कृषि/बाज़ार सलाह से पुष्टि करें।",
    "Consider flagging for climate-risk-linked support such as weather-indexed insurance or a seasonal advisory.":
        "मौसम-आधारित बीमा या मौसमी सलाह जैसे जलवायु-जोखिम समर्थन के लिए चिह्नित करें।",
    "Note the deviation in the enterprise's risk profile.":
        "उद्यम की जोखिम प्रोफ़ाइल में विचलन दर्ज करें।",

    # climate_stress_excess
    "Prepare for heavier-than-normal rainfall — protect stored inputs.":
        "सामान्य से अधिक बारिश की तैयारी करें — भंडारित इनपुट सुरक्षित रखें।",

    # market_stress
    "Delay any supplier credit purchases.":
        "आपूर्तिकर्ता से उधार खरीद टालें।",
    "Stock only fast-moving essential items for now.":
        "अभी केवल तेज़ बिकने वाली ज़रूरी वस्तुएँ रखें।",
    "Contact your field officer about restructuring an existing loan or EMI.":
        "मौजूदा कर्ज़ या EMI के पुनर्गठन के लिए फ़ील्ड अफ़सर से संपर्क करें।",

    # new_business
    "Track daily cash flow strictly for the first six months.":
        "पहले छह महीने रोज़ का हिसाब सख्ती से रखें।",
    "Keep a small rainy-day reserve from every payout.":
        "हर आमदनी से थोड़ी बचत मुसीबत के लिए अलग रखें।",
}


def hindi_for(label_en: str) -> str | None:
    """Returns the Hindi translation if we have one, else None."""
    return _HI.get(label_en)
