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

    # sector × band playbook (owner + field-officer actions across every
    # sector and band). These are what the `band_guidance` alert carries,
    # so every green/amber/red business needs them translated.
    "Advise staggered batch sizing to smooth cash flow.":
        "नक़दी संतुलित रखने के लिए बैच का आकार धीरे-धीरे बढ़ाने की सलाह दें।",
    "Ask your field officer about bridge financing or feed-input support right away.":
        "फ़ील्ड अफ़सर से तुरंत ब्रिज फ़ाइनेंस या चारा-इनपुट सहायता के बारे में बात करें।",
    "Assess readiness for growth financing such as an equipment upgrade.":
        "उपकरण अपग्रेड जैसी विस्तार फ़ाइनेंसिंग के लिए तैयारी जाँचें।",
    "Avoid growing your flock beyond what current cash flow can comfortably feed.":
        "अभी की आमदनी जितनी झुंड को खिला सके, उससे ज़्यादा न बढ़ाएँ।",
    "Avoid new debt until demand picks back up.":
        "जब तक माँग वापस न बढ़े, नया कर्ज़ न लें।",
    "Avoid new supplier credit purchases until cash flow firms up.":
        "नक़दी सुधरने तक आपूर्तिकर्ता से उधार खरीद न करें।",
    "Avoid recommending new production financing until demand recovers.":
        "माँग वापस आने तक नई उत्पादन फ़ाइनेंसिंग की सिफ़ारिश न करें।",
    "Avoid taking on new debt for feed purchases.":
        "चारा खरीदने के लिए नया कर्ज़ न लें।",
    "Build a buffer for the next lean period.":
        "अगले मंदे दौर के लिए बचत जमा करें।",
    "Build raw material stock ahead of the next peak season.":
        "अगले पीक सीज़न से पहले कच्चे माल का स्टॉक बनाएँ।",
    "Build up a fodder and cash buffer before the next lean period.":
        "अगले मंदे दौर से पहले चारे और नक़दी की बचत जमा कर लें।",
    "Check feed-cost pass-through against current egg/broiler market prices.":
        "अंडे/ब्रॉयलर के मौजूदा भाव के हिसाब से चारा लागत का असर जाँचें।",
    "Check for disease outbreak or a feed-price shock as the root cause.":
        "जड़ में बीमारी का प्रकोप या चारा-भाव का झटका तो नहीं, यह जाँचें।",
    "Check for local demand disruption such as new competition or nearby price changes.":
        "नई प्रतिस्पर्धा या आसपास के भाव बदलाव जैसी स्थानीय माँग-रुकावट जाँचें।",
    "Check the order pipeline and buyer concentration risk.":
        "ऑर्डर पाइपलाइन और एक ही ख़रीदार पर निर्भरता का जोखिम जाँचें।",
    "Check whether short-term inventory financing is needed.":
        "देखें कि क्या छोटी अवधि की इन्वेंट्री फ़ाइनेंसिंग की ज़रूरत है।",
    "Compare feed suppliers before restocking.":
        "दोबारा भरने से पहले अलग-अलग चारा आपूर्तिकर्ताओं की तुलना करें।",
    "Conduct an on-site check — local demand shocks often drive rural retail risk.":
        "मौक़े पर जाकर जाँचें — गाँव की दुकानों में जोखिम अक्सर स्थानीय माँग गिरने से आता है।",
    "Confirm food-safety/compliance certifications are current.":
        "खाद्य-सुरक्षा/अनुपालन प्रमाणपत्र मौजूदा हैं, पुष्टि करें।",
    "Confirm inventory turnover is healthy.":
        "इन्वेंट्री का टर्नओवर ठीक है, इसकी पुष्टि करें।",
    "Confirm savings are being built up for the off-season.":
        "ऑफ़-सीज़न के लिए बचत जुड़ रही है, पुष्टि करें।",
    "Confirm the enterprise remains stable at the next visit.":
        "अगली मुलाक़ात पर उद्यम की स्थिरता की पुष्टि करें।",
    "Confirm vaccination and biosecurity compliance now.":
        "अभी टीकाकरण और जैव-सुरक्षा अनुपालन की पुष्टि करें।",
    "Connect to emergency working capital.":
        "आपात कार्यशील पूँजी से जोड़ें।",
    "Connect to market-linkage programs or emergency credit.":
        "बाज़ार-लिंकेज कार्यक्रमों या आपात ऋण से जोड़ें।",
    "Consider adding a value-added product line.":
        "मूल्य-वर्धित उत्पाद जोड़ने पर विचार करें।",
    "Consider investing surplus into fodder storage or better vet care.":
        "बची हुई रक़म चारा भंडारण या बेहतर पशु-चिकित्सा में लगाने पर विचार करें।",
    "Consult a vet early if yield is dropping, rather than waiting.":
        "उत्पादन गिर रहा हो तो इंतज़ार न करें, तुरंत पशु-चिकित्सक से मिलें।",
    "Contact your SHG/cooperative for support options.":
        "सहायता विकल्पों के लिए अपने SHG/सहकारी से संपर्क करें।",
    "Cut non-essential input purchases.":
        "ग़ैर-ज़रूरी इनपुट की खरीद बंद करें।",
    "Discuss growth financing options such as additional cattle or cold-chain access.":
        "अतिरिक्त पशु या कोल्ड-चेन पहुँच जैसे विस्तार फ़ाइनेंस विकल्पों पर चर्चा करें।",
    "Discuss modest working capital for inventory expansion if requested.":
        "अनुरोध होने पर इन्वेंट्री बढ़ाने के लिए सीमित कार्यशील पूँजी पर चर्चा करें।",
    "Discuss short-term working capital or a lighter repayment schedule if EMI is tight.":
        "EMI कठिन हो तो छोटी अवधि की कार्यशील पूँजी या हल्की क़िस्त योजना पर चर्चा करें।",
    "Encourage FPO/cooperative linkage if not already formalised.":
        "अगर पहले से न जुड़े हों तो FPO/सहकारी से जुड़ने के लिए प्रेरित करें।",
    "Encourage market-linkage support such as exhibitions or e-commerce onboarding.":
        "प्रदर्शनी या ई-कॉमर्स ऑनबोर्डिंग जैसे बाज़ार-लिंकेज समर्थन के लिए प्रोत्साहित करें।",
    "Escalate if cash flow doesn't recover by the next cycle.":
        "अगले चक्र तक नक़दी न सुधरे तो मामला ऊपर बढ़ाएँ।",
    "Explore a cooperative bulk-selling arrangement for a better milk price.":
        "दूध का बेहतर भाव पाने के लिए सहकारी थोक बिक्री की व्यवस्था तलाशें।",
    "Explore market-linkage or exhibition support to boost demand.":
        "माँग बढ़ाने के लिए बाज़ार-लिंकेज या प्रदर्शनी समर्थन तलाशें।",
    "Explore new sales channels like exhibitions or online platforms.":
        "प्रदर्शनी या ऑनलाइन प्लेटफ़ॉर्म जैसे नए बिक्री चैनल तलाशें।",
    "Flag as a strong candidate for scale-up financing.":
        "बड़े पैमाने की फ़ाइनेंसिंग के लिए मज़बूत उम्मीदवार के रूप में चिह्नित करें।",
    "Flag for close monitoring over the next two cycles.":
        "अगले दो चक्रों तक कड़ी निगरानी के लिए चिह्नित करें।",
    "Hold off on building extra inventory until margins stabilise.":
        "मार्जिन स्थिर होने तक अतिरिक्त इन्वेंट्री जमा न करें।",
    "Hold off on stockpiling raw material until orders firm up.":
        "ऑर्डर पक्के होने तक कच्चा माल जमा न करें।",
    "Identify whether this is a demand shock or a seasonal lean period.":
        "पहचानें कि यह माँग का झटका है या मौसमी मंदी।",
    "Investigate whether the driver is raw-material cost, demand drop, or debt burden.":
        "जाँचें कि कारण कच्चे माल की लागत है, माँग का गिरना या कर्ज़ का बोझ।",
    "Keep building your savings buffer during this stable period.":
        "इस स्थिर दौर में बचत जमा करते रहें।",
    "Keep setting aside savings for the off-season.":
        "ऑफ़-सीज़न के लिए बचत अलग रखते रहें।",
    "Keep up your current savings routine.":
        "मौजूदा बचत की आदत बनाए रखें।",
    "Lock in a bulk feed purchase at today's price if you can.":
        "मुमकिन हो तो आज के भाव पर चारे की थोक खरीद कर लें।",
    "Make immediate outreach a priority.":
        "तुरंत संपर्क करना प्राथमिकता बनाएँ।",
    "Monitor closely since poultry margins can turn quickly even from a stable position.":
        "पोल्ट्री का मार्जिन स्थिर स्थिति से भी तेज़ी से बदल सकता है — क़रीब से निगरानी रखें।",
    "Monitor the demand trend in the enterprise's target market.":
        "उद्यम के लक्षित बाज़ार में माँग की चाल पर नज़र रखें।",
    "Negotiate a longer-term raw material contract to lock in input costs.":
        "इनपुट लागत तय रखने के लिए कच्चे माल का लंबी अवधि का अनुबंध करें।",
    "Note as a stable enterprise for the next review cycle.":
        "अगले समीक्षा चक्र के लिए स्थिर उद्यम के रूप में दर्ज करें।",
    "Note this as a candidate for formal credit access support.":
        "औपचारिक ऋण-पहुँच समर्थन के उम्मीदवार के रूप में दर्ज करें।",
    "Pause new raw material purchases until you have confirmed orders.":
        "पक्के ऑर्डर मिलने तक नया कच्चा माल न खरीदें।",
    "Prioritise essential working capital only where repayment capacity is realistic.":
        "जहाँ चुकौती क्षमता वास्तविक हो, वहीं ज़रूरी कार्यशील पूँजी को प्राथमिकता दें।",
    "Re-check status at the next assessment cycle.":
        "अगले मूल्यांकन चक्र में स्थिति दोबारा जाँचें।",
    "Recommend an emergency credit line or short moratorium.":
        "आपात ऋण-सीमा या छोटी मोहलत की सिफ़ारिश करें।",
    "Recommend inventory rationalisation before extending new credit.":
        "नया कर्ज़ बढ़ाने से पहले इन्वेंट्री को कम-ज़्यादा करने की सिफ़ारिश करें।",
    "Recommend targeted relief such as an input-cost support link or restructured EMI.":
        "इनपुट-लागत सहायता लिंक या पुनर्गठित EMI जैसी लक्षित राहत की सिफ़ारिश करें।",
    "Reduce flock size to what you can sustainably feed.":
        "झुंड को उतना ही रखें जितना लगातार खिला सकें।",
    "Reinvest surplus into flock size or biosecurity upgrades.":
        "बची हुई रक़म झुंड बढ़ाने या जैव-सुरक्षा सुधार में लगाएँ।",
    "Renegotiate supplier payment terms if you can.":
        "अगर मुमकिन हो तो आपूर्तिकर्ता की भुगतान शर्तें दोबारा तय करें।",
    "Renegotiate supplier terms if possible.":
        "मुमकिन हो तो आपूर्तिकर्ता की शर्तें दोबारा तय करें।",
    "Review expense ratio and inventory mix.":
        "खर्च का अनुपात और इन्वेंट्री मिक्स की समीक्षा करें।",
    "Review input-cost pass-through and sourcing options.":
        "इनपुट-लागत के असर और सोर्सिंग विकल्पों की समीक्षा करें।",
    "Review supplier terms while cash flow is strong.":
        "जब नक़दी अच्छी हो, तभी आपूर्तिकर्ता की शर्तों की समीक्षा करें।",
    "Review which items are moving slowly and cut back restocking on those.":
        "देखें कौन-सी चीज़ें धीरे बिक रही हैं और उनका दोबारा भरना कम करें।",
    "Review your pricing since raw material costs are rising faster than sales.":
        "कच्चे माल की लागत बिक्री से तेज़ बढ़ रही है — अपने दाम की समीक्षा करें।",
    "Schedule a farm visit to check fodder stock and herd health.":
        "चारा स्टॉक और पशुओं की सेहत जाँचने के लिए फ़ार्म का दौरा तय करें।",
    "Shift inventory mix toward higher-margin items.":
        "इन्वेंट्री मिक्स को ज़्यादा मार्जिन वाली चीज़ों की तरफ़ मोड़ें।",
    "Spend only on essential feed and vet care for now.":
        "अभी सिर्फ़ ज़रूरी चारे और पशु-चिकित्सा पर ख़र्च करें।",
    "Spread sales across more buyers instead of relying on one.":
        "एक ख़रीदार पर निर्भर होने की जगह बिक्री कई ख़रीदारों में बाँटें।",
    "Talk to your field officer about a repayment pause or emergency working capital before the next production cycle.":
        "अगले उत्पादन चक्र से पहले फ़ील्ड अफ़सर से चुकौती-रुकावट या आपात कार्यशील पूँजी के बारे में बात करें।",
    "Talk to your field officer about emergency credit or a restructured repayment plan before missing a payment.":
        "क़िस्त छूटने से पहले फ़ील्ड अफ़सर से आपात ऋण या पुनर्गठित चुकौती योजना के बारे में बात करें।",
    "Talk to your field officer about short-term support for essential expenses.":
        "ज़रूरी ख़र्चों के लिए छोटी अवधि की सहायता के बारे में फ़ील्ड अफ़सर से बात करें।",
    "Track expenses closely this month.":
        "इस महीने ख़र्चों पर क़रीब से नज़र रखें।",
    "Track feed price trends so you're not caught off guard later.":
        "चारे के भाव की चाल पर नज़र रखें ताकि बाद में झटका न लगे।",
    "Track milk yield against your usual pattern.":
        "अपने आम पैटर्न से दूध उत्पादन की तुलना करते रहें।",
    "Track weekly until stabilised.":
        "स्थिर होने तक हर हफ़्ते जाँच करते रहें।",
    "Treat this as an urgent visit — poultry cash flow deteriorates quickly.":
        "इसे तुरंत मुलाक़ात मानें — पोल्ट्री की नक़दी तेज़ी से बिगड़ती है।",
    "Use this stable phase to help lock in longer-term buyer relationships.":
        "इस स्थिर दौर का इस्तेमाल लंबे समय के ख़रीदार रिश्ते बनाने में करें।",
    "Verify livestock health and feed availability on the ground.":
        "मौक़े पर पशु-स्वास्थ्य और चारे की उपलब्धता की पुष्टि करें।",
    "Verify the root cause before recommending credit.":
        "ऋण की सिफ़ारिश से पहले जड़ कारण की पुष्टि करें।",
    "Watch for disease risk during the visit.":
        "मुलाक़ात के दौरान बीमारी के जोखिम पर नज़र रखें।",
    "Watch for early signs of disease, which can worsen cash flow fast.":
        "बीमारी के शुरुआती संकेतों पर नज़र रखें — इनसे नक़दी तेज़ी से बिगड़ सकती है।",
    "Watch the savings buffer ahead of the lean season.":
        "मंदे सीज़न से पहले बचत के भंडार पर नज़र रखें।",
    "Watch your expenses closely until demand stabilises.":
        "माँग स्थिर होने तक अपने ख़र्चों पर क़रीब से नज़र रखें।",
}


def hindi_for(label_en: str) -> str | None:
    """Returns the Hindi translation if we have one, else None."""
    return _HI.get(label_en)
