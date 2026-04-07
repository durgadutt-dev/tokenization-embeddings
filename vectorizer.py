"""
vectorizer.py
-------------
Converts a plan JSON dict into two representations:

  1. extract_features(plan) → np.ndarray of shape (NUM_FEATURES,)
     Fixed-length numeric vector of key cost-sharing and network attributes.
     Used for structured similarity (scaled with StandardScaler).

  2. plan_to_text(plan) → str
     Readable plain-English summary of the plan.
     Embedded with SentenceTransformer for semantic similarity.

Both representations are combined in recommender.py to compute hybrid similarity.
"""
import re
import numpy as np

# ── Feature names (order matters — must stay in sync with extract_features) ───
FEATURE_NAMES = [
    "deductible_individual_in",
    "deductible_family_in",
    "oop_individual_in",
    "oop_family_in",
    "copay_pcp",
    "copay_specialist",
    "copay_urgent_care",
    "copay_er",
    "coinsurance_in",          # stored as decimal, e.g. 0.20 for 20%
    "rx_tier1_retail",
    "rx_tier2_retail",
    "rx_tier3_retail",
    "visit_limit_pt",
    "visit_limit_chiro",
    "visit_limit_snf_days",
    "visit_limit_home_health",
    "requires_pcp",            # 0 or 1
    "requires_referrals",      # 0 or 1
    "oon_covered",             # 0 or 1
    "metal_level_ordinal",     # bronze=0, silver=1, gold=2, platinum=3
    "plan_type_ordinal",       # hmo=0, epo=1, ppo/pos=2, hdhp=3
]

NUM_FEATURES = len(FEATURE_NAMES)

_METAL_ORDINAL = {"bronze": 0, "silver": 1, "gold": 2, "platinum": 3}
_TYPE_ORDINAL  = {"hmo": 0, "epo": 1, "ppo": 2, "pos": 2, "hdhp": 3}

# Sentinel for unlimited visit counts (e.g. "Unlimited (parity)")
_UNLIMITED = 999.0


# ── Parsing helpers ───────────────────────────────────────────────────────────

def _parse_dollar(s) -> float:
    """
    Extract the first dollar amount from a string.

    Examples:
        "$30"            → 30.0
        "$350 per visit" → 350.0
        "$0 via MDLIVE"  → 0.0
        1500             → 1500.0
        None             → nan
    """
    if s is None:
        return float("nan")
    if isinstance(s, (int, float)):
        return float(s)
    text = str(s).lower()
    if "unlimited" in text or "not applicable" in text:
        return _UNLIMITED
    m = re.search(r"\$?([\d,]+(?:\.\d+)?)", text)
    return float(m.group(1).replace(",", "")) if m else float("nan")


def _parse_pct(s) -> float:
    """
    Parse a percentage string to a decimal.

    Examples:
        "20%"  → 0.20
        "30 %" → 0.30
        None   → nan
    """
    if s is None:
        return float("nan")
    if isinstance(s, (int, float)):
        v = float(s)
        return v / 100.0 if v > 1.0 else v
    m = re.search(r"([\d.]+)\s*%", str(s))
    return float(m.group(1)) / 100.0 if m else float("nan")


def _parse_visit_limit(s) -> float:
    """
    Extract a number from visit/day limit strings.

    Examples:
        "60 combined PT/OT/ST visits per plan year" → 60.0
        "30 visits per plan year"                   → 30.0
        "Unlimited (parity)"                        → 999.0
        None                                        → nan
    """
    if s is None:
        return float("nan")
    text = str(s).lower()
    if "unlimited" in text:
        return _UNLIMITED
    m = re.search(r"([\d,]+)", text)
    return float(m.group(1).replace(",", "")) if m else float("nan")


def _safe(val: float, default: float = 0.0) -> float:
    """Replace NaN with a default value."""
    return default if (isinstance(val, float) and np.isnan(val)) else val


# ── Public API ────────────────────────────────────────────────────────────────

def extract_features(plan: dict) -> np.ndarray:
    """
    Extract a fixed-length numeric feature vector from a plan JSON dict.

    Missing or unparseable values default to 0.0 so the vector is always
    complete. The StandardScaler in catalog_builder.py will normalise
    across the catalog before similarity is computed.

    Args:
        plan: Parsed plan JSON dict (as produced by plan_parser.py or hand-crafted).

    Returns:
        np.ndarray of shape (NUM_FEATURES,) with dtype float32.
    """
    d  = plan.get("deductibles", {})
    o  = plan.get("out_of_pocket_maximum", {})
    cp = plan.get("copays", {})
    rx = plan.get("prescription_drugs", {}).get("tiers", {})
    vl = plan.get("visit_limits", {})
    ni = plan.get("network_information", {})
    pd = plan.get("plan_details", {})

    features = [
        _safe(_parse_dollar(d.get("in_network", {}).get("individual"))),
        _safe(_parse_dollar(d.get("in_network", {}).get("family"))),
        _safe(_parse_dollar(o.get("in_network", {}).get("individual"))),
        _safe(_parse_dollar(o.get("in_network", {}).get("family"))),
        _safe(_parse_dollar(cp.get("primary_care_visit",  {}).get("in_network"))),
        _safe(_parse_dollar(cp.get("specialist_visit",    {}).get("in_network"))),
        _safe(_parse_dollar(cp.get("urgent_care",         {}).get("in_network"))),
        _safe(_parse_dollar(cp.get("emergency_room",      {}).get("in_network"))),
        _safe(_parse_pct(plan.get("coinsurance", {}).get("in_network"))),
        _safe(_parse_dollar(rx.get("tier_1_generic",          {}).get("retail_30_day"))),
        _safe(_parse_dollar(rx.get("tier_2_preferred_brand",  {}).get("retail_30_day"))),
        _safe(_parse_dollar(rx.get("tier_3_non_preferred_brand", {}).get("retail_30_day"))),
        _safe(_parse_visit_limit(vl.get("physical_therapy"))),
        _safe(_parse_visit_limit(vl.get("chiropractic"))),
        _safe(_parse_visit_limit(vl.get("skilled_nursing_facility"))),
        _safe(_parse_visit_limit(vl.get("home_health"))),
        float(bool(ni.get("requires_pcp",        False))),
        float(bool(ni.get("requires_referrals",  False))),
        float(bool(ni.get("out_of_network_covered", True))),
        float(_METAL_ORDINAL.get(str(pd.get("metal_level", "")).lower(), 1)),
        float(_TYPE_ORDINAL.get( str(pd.get("plan_type",   "")).lower(), 1)),
    ]

    return np.array(features, dtype=np.float32)


def plan_to_text(plan: dict) -> str:
    """
    Produce a readable plain-English summary of a plan for semantic embedding.

    Sentence-transformers capture meaning better from structured prose than
    from raw JSON keys, so this function surfaces all cost-sharing and network
    attributes in a consistent, human-readable format.

    Args:
        plan: Parsed plan JSON dict.

    Returns:
        Multi-line string suitable for SentenceTransformer.encode().
    """
    pd_ = plan.get("plan_details", {})
    d   = plan.get("deductibles", {})
    o   = plan.get("out_of_pocket_maximum", {})
    cp  = plan.get("copays", {})
    rx  = plan.get("prescription_drugs", {}).get("tiers", {})
    ni  = plan.get("network_information", {})
    cs  = plan.get("covered_services", {})
    vl  = plan.get("visit_limits", {})
    ex  = plan.get("exclusions", [])
    ab  = plan.get("additional_benefits", {})

    def g(obj, *keys, default="N/A"):
        """Safely walk nested dict keys."""
        for k in keys:
            if not isinstance(obj, dict):
                return default
            obj = obj.get(k, default)
        return obj if obj != {} else default

    lines = [
        f"Plan name: {pd_.get('plan_name', 'Unknown')}",
        f"Insurer: {pd_.get('insurer', 'Unknown')}",
        f"Plan type: {pd_.get('plan_type', 'Unknown')} | Metal level: {pd_.get('metal_level', 'Unknown')}",
        f"Network: {pd_.get('network_name', 'Unknown')} | National network: {ni.get('national_network', 'Unknown')}",
        f"Requires PCP: {ni.get('requires_pcp', False)} | Requires referrals: {ni.get('requires_referrals', False)}",
        f"Out-of-network covered: {ni.get('out_of_network_covered', 'Unknown')}",
        "",
        f"Individual deductible (in-network): ${g(d, 'in_network', 'individual')}",
        f"Family deductible (in-network): ${g(d, 'in_network', 'family')}",
        f"Individual OOP maximum (in-network): ${g(o, 'in_network', 'individual')}",
        f"Family OOP maximum (in-network): ${g(o, 'in_network', 'family')}",
        f"Coinsurance (in-network): {g(plan, 'coinsurance', 'in_network')}",
        "",
        f"PCP visit copay: {g(cp, 'primary_care_visit', 'in_network')}",
        f"Specialist visit copay: {g(cp, 'specialist_visit', 'in_network')}",
        f"Urgent care copay: {g(cp, 'urgent_care', 'in_network')}",
        f"Emergency room copay: {g(cp, 'emergency_room', 'in_network')}",
        f"Telehealth copay: {g(cp, 'telehealth', 'in_network')}",
        "",
        f"Tier 1 generic Rx (30-day retail): {g(rx, 'tier_1_generic', 'retail_30_day')}",
        f"Tier 2 preferred brand Rx (30-day retail): {g(rx, 'tier_2_preferred_brand', 'retail_30_day')}",
        f"Tier 3 non-preferred brand Rx (30-day retail): {g(rx, 'tier_3_non_preferred_brand', 'retail_30_day')}",
        f"Tier 4 specialty Rx: {g(rx, 'tier_4_specialty', 'retail_30_day')}",
        "",
        f"Inpatient hospital (in-network): {g(cs, 'inpatient_hospital', 'in_network')}",
        f"Outpatient surgery (in-network): {g(cs, 'outpatient_surgery', 'in_network')}",
        f"Mental health outpatient: {g(cs, 'mental_health_outpatient', 'in_network')}",
        f"Physical therapy: {g(cs, 'physical_therapy', 'in_network')} | Limit: {vl.get('physical_therapy', 'N/A')}",
        f"Chiropractic: {g(cs, 'chiropractic_care', 'in_network')} | Limit: {vl.get('chiropractic', 'N/A')}",
        f"Skilled nursing facility: {g(cs, 'skilled_nursing_facility', 'in_network')} | Limit: {vl.get('skilled_nursing_facility', 'N/A')}",
        f"Home health care: {g(cs, 'home_health_care', 'in_network')} | Limit: {vl.get('home_health', 'N/A')}",
        f"Bariatric surgery covered: {g(cs, 'bariatric_surgery', 'in_network')}",
        f"Infertility treatment: {g(cs, 'infertility_treatment', 'in_network')}",
    ]

    if ex:
        lines.append(f"Key exclusions: {'; '.join(ex[:6])}")

    if ab.get("wellness_programs"):
        lines.append(f"Wellness programs: {ab['wellness_programs']}")
    if ab.get("telemedicine"):
        lines.append(f"Telemedicine: {ab['telemedicine']}")

    return "\n".join(lines)
