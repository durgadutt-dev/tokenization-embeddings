"""
Generate 500 realistic health insurance plans and export to Excel.
"""
import json, os, random, itertools, glob
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

random.seed(42)

# ── Reference data ────────────────────────────────────────────────────────────

INSURERS = [
    ("Aetna Life Insurance Company",            "PPO",  True,  "60054"),
    ("Cigna Health and Life Insurance Company", "HMO",  False, "67369"),
    ("UnitedHealthcare Insurance Company",      "PPO",  True,  "79413"),
    ("Anthem Blue Cross Blue Shield",           "PPO",  True,  "14163"),
    ("Humana Health Plan Inc.",                 "HMO",  False, "95885"),
    ("Kaiser Foundation Health Plan",           "HMO",  False, "95378"),
    ("Blue Cross Blue Shield of Texas",         "PPO",  True,  "54771"),
    ("Molina Healthcare",                       "HMO",  False, "96776"),
    ("Oscar Health Insurance Corp.",            "EPO",  False, "15524"),
    ("Centene / Ambetter",                      "HMO",  False, "78700"),
    ("Highmark Blue Cross Blue Shield",         "PPO",  True,  "20427"),
    ("Health Net of California",                "HMO",  False, "95301"),
    ("Harvard Pilgrim Health Care",             "PPO",  True,  "96385"),
    ("Medica Health Plans",                     "HMO",  False, "61182"),
    ("Tufts Health Plan",                       "PPO",  True,  "55247"),
    ("CareFirst BlueCross BlueShield",          "PPO",  True,  "10455"),
    ("Bright Health Insurance",                 "EPO",  False, "15499"),
    ("Friday Health Plans",                     "HMO",  False, "15601"),
    ("PreferredOne Insurance Company",          "PPO",  True,  "45104"),
    ("Scott & White Health Plan",               "HMO",  False, "96245"),
]

NETWORKS = {
    "Aetna Life Insurance Company":            ["Aetna Choice POS II", "Aetna Open Choice PPO", "Aetna Whole Health"],
    "Cigna Health and Life Insurance Company": ["Cigna LocalPlus", "Cigna Open Access Plus", "Cigna Connect"],
    "UnitedHealthcare Insurance Company":      ["UHC Choice Plus", "UHC Navigate", "UHC Core"],
    "Anthem Blue Cross Blue Shield":           ["BlueCard PPO", "Anthem Blue Access PPO", "Anthem Select PPO"],
    "Humana Health Plan Inc.":                 ["Humana Gold Plus HMO", "Humana Preferred PPO", "Humana National POS"],
    "Kaiser Foundation Health Plan":           ["Kaiser Permanente Medical Group", "Kaiser Select HMO"],
    "Blue Cross Blue Shield of Texas":         ["BlueChoice PPO", "Blue Advantage HMO", "Blue Premier PPO"],
    "Molina Healthcare":                       ["Molina Marketplace Network", "Molina Complete Care"],
    "Oscar Health Insurance Corp.":            ["Oscar Select Network", "Oscar Metro Network"],
    "Centene / Ambetter":                      ["Ambetter Essential Care", "Ambetter Balanced Care", "Ambetter Secure Care"],
    "Highmark Blue Cross Blue Shield":         ["Highmark Blue Network", "Highmark Flex Blue PPO"],
    "Health Net of California":                ["Health Net CA Network", "Health Net SmartCare"],
    "Harvard Pilgrim Health Care":             ["Harvard Pilgrim Network", "Harvard Pilgrim Flex PPO"],
    "Medica Health Plans":                     ["Medica Choice Passport", "Medica Elect PPO"],
    "Tufts Health Plan":                       ["Tufts PPO Network", "Tufts Preferred HMO"],
    "CareFirst BlueCross BlueShield":          ["CareFirst BlueChoice", "CareFirst BlueCross PPO"],
    "Bright Health Insurance":                 ["Bright HealthCare Network", "Bright Select Network"],
    "Friday Health Plans":                     ["Friday HMO Network", "Friday Flex Network"],
    "PreferredOne Insurance Company":          ["PreferredOne Provider Network", "PreferredOne PPO Plus"],
    "Scott & White Health Plan":               ["Scott & White HMO", "Scott & White PPO"],
}

PLAN_TYPES = ["HMO", "PPO", "EPO", "POS"]

METAL_CONFIG = {
    # metal: (actuarial, deductible_range_indiv, oop_max_range_indiv, coinsurance_in, coinsurance_out)
    "Bronze":   (0.60, (4000, 8700),  (7000, 8700),  "40%", "50%"),
    "Silver":   (0.70, (1500, 4500),  (6000, 8700),  "30%", "40%"),
    "Gold":     (0.80, (500,  2000),  (4000, 7000),  "20%", "40%"),
    "Platinum": (0.90, (0,   750),   (2000, 4500),  "10%", "30%"),
}

COVERAGE_AREAS = [
    "National", "Regional — California", "Regional — Texas", "Regional — Northeast",
    "Regional — Midwest", "Regional — Southeast", "Regional — Mountain West",
    "Regional — Pacific Northwest", "Regional — Mid-Atlantic", "Regional — New England",
]

GROUP_SIZES = ["Large Group (51+)", "Small Group (1–50)", "Individual & Family Plan"]

WELLNESS_PROGRAMS = [
    "Up to $500 annual incentive for health activities",
    "Up to $400 annual incentive for biometric screening",
    "Up to $300 annual reward for wellness milestones",
    "Up to $600 annual incentive via mobile app",
    "Up to $200 annual incentive for preventive care",
    "Up to $250 annual incentive for fitness challenges",
    "Up to $350 annual reward for health assessment",
    "Not included",
]

GYM_REIMBURSEMENTS = [
    "Not included",
    "$15/month gym reimbursement",
    "$20/month gym reimbursement",
    "$25/month gym reimbursement",
    "$30/month gym reimbursement",
    "$40/month gym reimbursement",
    "$50/month gym reimbursement",
]

TELEMEDICINE = [
    "$0 per visit — unlimited",
    "$0 per visit via app",
    "$5 per visit",
    "$10 per visit",
    "$15 per visit",
    "$20 per visit",
    "Not included",
]

EAP_OPTIONS = [
    "3 free counseling sessions per issue per year",
    "5 free counseling sessions per issue per year",
    "6 free counseling sessions per issue per year",
    "8 free counseling sessions per issue per year",
    "Unlimited telephonic counseling",
    "Not included",
]

FORMULARY_NAMES = {
    "Aetna Life Insurance Company":            "Aetna Standard Formulary 2024",
    "Cigna Health and Life Insurance Company": "Cigna Formulary 2 — Standard 2024",
    "UnitedHealthcare Insurance Company":      "UHC Standard Formulary 2024",
    "Anthem Blue Cross Blue Shield":           "Anthem Premier Formulary 2024",
    "Humana Health Plan Inc.":                 "Humana Drug List 2024",
    "Kaiser Foundation Health Plan":           "Kaiser Permanente Drug Formulary 2024",
    "Blue Cross Blue Shield of Texas":         "BCBS Value Formulary 2024",
    "Molina Healthcare":                       "Molina PDL 2024",
    "Oscar Health Insurance Corp.":            "Oscar Drug Formulary 2024",
    "Centene / Ambetter":                      "Ambetter Drug List 2024",
    "Highmark Blue Cross Blue Shield":         "Highmark Drug Formulary 2024",
    "Health Net of California":                "Health Net Drug Formulary 2024",
    "Harvard Pilgrim Health Care":             "Harvard Pilgrim Formulary 2024",
    "Medica Health Plans":                     "Medica Drug Formulary 2024",
    "Tufts Health Plan":                       "Tufts Health Drug List 2024",
    "CareFirst BlueCross BlueShield":          "CareFirst Drug Formulary 2024",
    "Bright Health Insurance":                 "Bright Health Drug List 2024",
    "Friday Health Plans":                     "Friday Health PDL 2024",
    "PreferredOne Insurance Company":          "PreferredOne Drug Formulary 2024",
    "Scott & White Health Plan":               "Scott & White Formulary 2024",
}

NURSE_LINES = {
    "Aetna Life Insurance Company":            "24/7 — 1-800-556-1555",
    "Cigna Health and Life Insurance Company": "24/7 — 1-800-244-6224",
    "UnitedHealthcare Insurance Company":      "24/7 — 1-866-774-2060",
    "Anthem Blue Cross Blue Shield":           "24/7 — 1-800-337-4770",
    "Humana Health Plan Inc.":                 "24/7 — 1-800-789-7890",
    "Kaiser Foundation Health Plan":           "24/7 — 1-800-290-4400",
    "Blue Cross Blue Shield of Texas":         "24/7 — 1-800-282-8161",
    "Molina Healthcare":                       "24/7 — 1-888-665-4621",
    "Oscar Health Insurance Corp.":            "24/7 Concierge Team — in-app",
    "Centene / Ambetter":                      "24/7 — 1-833-514-0390",
    "Highmark Blue Cross Blue Shield":         "24/7 — 1-800-651-5465",
    "Health Net of California":                "24/7 — 1-800-675-6110",
    "Harvard Pilgrim Health Care":             "24/7 — 1-888-333-4742",
    "Medica Health Plans":                     "24/7 — 1-800-952-3455",
    "Tufts Health Plan":                       "24/7 — 1-800-462-0224",
    "CareFirst BlueCross BlueShield":          "24/7 — 1-800-783-4582",
    "Bright Health Insurance":                 "24/7 — 1-833-230-2010",
    "Friday Health Plans":                     "24/7 — 1-888-867-5765",
    "PreferredOne Insurance Company":          "24/7 — 1-763-847-4477",
    "Scott & White Health Plan":               "24/7 — 1-844-799-7947",
}

# ── Plan generator ────────────────────────────────────────────────────────────

def rx_copays(metal, t1_base, t2_base, t3_base):
    mult = {"Bronze": 1.3, "Silver": 1.1, "Gold": 1.0, "Platinum": 0.75}[metal]
    t1 = max(3, int(t1_base * mult))
    t2 = max(20, int(t2_base * mult))
    t3 = max(40, int(t3_base * mult))
    t4_pct = {"Bronze": "30%", "Silver": "25%", "Gold": "20%", "Platinum": "15%"}[metal]
    t4_cap = {"Bronze": 350, "Silver": 300, "Gold": 250, "Platinum": 200}[metal]
    return t1, t2, t3, t4_pct, t4_cap


def make_plan(idx, insurer_row, metal, plan_type, area, group_size, seed_offset=0):
    rng = random.Random(idx * 31 + seed_offset)

    insurer, default_type, national, naic = insurer_row
    network_name = rng.choice(NETWORKS[insurer])

    av, ded_range, oop_range, coin_in, coin_out = METAL_CONFIG[metal]

    ded_indiv   = rng.randint(*ded_range) // 100 * 100
    ded_family  = ded_indiv * 2
    oop_indiv   = max(ded_indiv + 500, rng.randint(*oop_range) // 100 * 100)
    oop_family  = oop_indiv * 2

    is_hmo = plan_type in ("HMO", "EPO")
    oon_covered = not is_hmo

    # copay scaling by metal
    pcp_copay_vals  = {"Bronze": (40,60), "Silver": (25,40), "Gold": (20,35), "Platinum": (10,25)}
    spec_copay_vals = {"Bronze": (80,120), "Silver": (55,85), "Gold": (40,70), "Platinum": (20,45)}
    uc_copay_vals   = {"Bronze": (80,120), "Silver": (55,85), "Gold": (50,75), "Platinum": (30,55)}
    er_copay_vals   = {"Bronze": (450,600), "Silver": (350,450), "Gold": (250,375), "Platinum": (150,250)}
    tele_vals       = {"Bronze": (10,20), "Silver": (5,15), "Gold": (0,10), "Platinum": (0,5)}

    pcp  = rng.randint(*pcp_copay_vals[metal])
    spec = rng.randint(*spec_copay_vals[metal])
    uc   = rng.randint(*uc_copay_vals[metal])
    er   = rng.randint(*er_copay_vals[metal])
    tele = rng.randint(*tele_vals[metal])

    # Rx
    t1, t2, t3, t4_pct, t4_cap = rx_copays(metal, 10, 50, 90)
    rx_ded_indiv = 0 if metal in ("Gold", "Platinum") else rng.choice([0, 250, 500])
    rx_ded_fam   = rx_ded_indiv * 2

    # bariatric: only some plans cover it
    covers_bariatric = rng.random() < {"Bronze": 0.2, "Silver": 0.4, "Gold": 0.65, "Platinum": 0.85}[metal]
    bariatric_in = f"{coin_in.replace('%','')}% coinsurance after deductible" if covers_bariatric else "Not covered"

    # PT/chiro visit limits
    pt_limit    = rng.choice([30, 40, 45, 50, 60, "Unlimited"])
    chiro_limit = rng.choice([15, 20, 25, 30, "Not covered"])
    hh_limit    = rng.choice([60, 80, 100, 120, "Unlimited"])
    snf_limit   = rng.choice([60, 90, 100, 120, 180])

    # gym reimbursement — deliberately varied
    gym = rng.choice(GYM_REIMBURSEMENTS)
    wellness = rng.choice(WELLNESS_PROGRAMS)
    tele_benefit = rng.choice(TELEMEDICINE)
    eap = rng.choice(EAP_OPTIONS)

    requires_pcp      = is_hmo
    requires_referrals = is_hmo and rng.random() < 0.8
    national_network  = national and (area == "National")

    short_insurer = insurer.split()[0]
    plan_name = f"{short_insurer} {plan_type} — {metal} {ded_indiv}"
    plan_id   = f"{short_insurer[:2].upper()}-{group_size[:2].upper()}-{plan_type}-{metal[0]}{ded_indiv}-2024-{idx:04d}"

    oon_str = lambda s: "Not covered" if is_hmo else s

    plan = {
        "plan_details": {
            "plan_name": plan_name,
            "plan_id": plan_id,
            "plan_type": plan_type,
            "insurer": insurer,
            "metal_level": metal,
            "actuarial_value": str(av),
            "plan_year": "2024",
            "group_size": group_size,
            "coverage_area": area,
            "network_name": network_name,
            "naic_code": naic,
        },
        "deductibles": {
            "in_network": {"individual": ded_indiv, "family": ded_family},
            "out_of_network": {"individual": ded_indiv*2 if oon_covered else None,
                               "family":     ded_family*2 if oon_covered else None},
        },
        "out_of_pocket_maximum": {
            "in_network": {"individual": oop_indiv, "family": oop_family},
            "out_of_network": {"individual": oop_indiv*2 if oon_covered else None,
                               "family":     oop_family*2 if oon_covered else None},
        },
        "copays": {
            "primary_care_visit":  {"in_network": f"${pcp}",  "out_of_network": oon_str(f"40% after deductible")},
            "specialist_visit":    {"in_network": f"${spec}", "out_of_network": oon_str(f"40% after deductible")},
            "urgent_care":         {"in_network": f"${uc}",   "out_of_network": oon_str(f"${uc}")},
            "emergency_room":      {"in_network": f"${er} per visit", "out_of_network": f"${er} per visit"},
            "telehealth":          {"in_network": f"${tele}" if tele > 0 else "$0",
                                    "out_of_network": "Not covered"},
        },
        "coinsurance": {
            "in_network": coin_in,
            "out_of_network": coin_out if oon_covered else "Not covered",
        },
        "prescription_drugs": {
            "formulary_name": FORMULARY_NAMES[insurer],
            "deductible": {"individual": rx_ded_indiv, "family": rx_ded_fam},
            "tiers": {
                "tier_1_generic":          {"retail_30_day": f"${t1}",  "mail_order_90_day": f"${t1*2}"},
                "tier_2_preferred_brand":  {"retail_30_day": f"${t2}",  "mail_order_90_day": f"${t2*2}"},
                "tier_3_non_preferred_brand": {"retail_30_day": f"${t3}", "mail_order_90_day": f"${t3*2}"},
                "tier_4_specialty":        {"retail_30_day": f"{t4_pct} up to ${t4_cap}", "mail_order_90_day": f"{t4_pct} up to ${t4_cap*2}"},
            },
            "mail_order_required_for_maintenance": rng.choice([True, False]),
        },
        "covered_services": {
            "preventive_care":           {"in_network": "No charge", "out_of_network": oon_str("40% after deductible")},
            "inpatient_hospital":        {"in_network": f"{coin_in} after deductible", "out_of_network": oon_str(f"{coin_out} after deductible")},
            "outpatient_surgery":        {"in_network": f"{coin_in} after deductible", "out_of_network": oon_str(f"{coin_out} after deductible")},
            "lab_tests":                 {"in_network": f"{coin_in} after deductible", "out_of_network": oon_str(f"{coin_out} after deductible")},
            "imaging_ct_mri_pet":        {"in_network": f"{coin_in} after deductible", "out_of_network": oon_str(f"{coin_out} after deductible")},
            "mental_health_outpatient":  {"in_network": f"${pcp} copay per visit",    "out_of_network": oon_str(f"{coin_out} after deductible")},
            "physical_therapy":          {"in_network": f"${spec} copay per visit",   "out_of_network": oon_str(f"{coin_out} after deductible")},
            "chiropractic_care":         {"in_network": f"${spec} copay per visit" if chiro_limit != "Not covered" else "Not covered",
                                          "out_of_network": "Not covered"},
            "maternity_delivery":        {"in_network": f"{coin_in} after deductible", "out_of_network": oon_str(f"{coin_out} after deductible")},
            "pediatric_dental":          {"in_network": "Preventive: No charge; Basic: covered after deductible", "out_of_network": oon_str("Not covered")},
            "pediatric_vision":          {"in_network": f"One exam/year no charge; ${rng.choice([100,125,150,175,200])} allowance", "out_of_network": "Not covered"},
            "bariatric_surgery":         {"in_network": bariatric_in, "out_of_network": "Not covered"},
            "transplants":               {"in_network": f"{coin_in} after deductible", "out_of_network": "Not covered"},
        },
        "visit_limits": {
            "physical_therapy":         f"{pt_limit} combined PT/OT/ST visits per plan year" if pt_limit != "Unlimited" else "Unlimited",
            "chiropractic":             f"{chiro_limit} visits per plan year" if chiro_limit != "Not covered" else "Not covered",
            "home_health":              f"{hh_limit} visits per plan year" if hh_limit != "Unlimited" else "Unlimited",
            "skilled_nursing_facility": f"{snf_limit} days per plan year",
        },
        "network_information": {
            "requires_pcp": requires_pcp,
            "requires_referrals": requires_referrals,
            "out_of_network_covered": oon_covered,
            "national_network": national_network,
        },
        "additional_benefits": {
            "wellness_programs":          wellness,
            "employee_assistance_program": eap,
            "telemedicine":               tele_benefit,
            "fitness_reimbursement":      gym,
            "nurse_advice_line":          NURSE_LINES[insurer],
        },
    }
    return plan


# ── flatten ───────────────────────────────────────────────────────────────────

def flat(plan):
    d  = plan.get("plan_details", {})
    de = plan.get("deductibles", {})
    op = plan.get("out_of_pocket_maximum", {})
    co = plan.get("copays", {})
    ci = plan.get("coinsurance", {})
    rx = plan.get("prescription_drugs", {})
    sv = plan.get("covered_services", {})
    ni = plan.get("network_information", {})
    ab = plan.get("additional_benefits", {})
    tiers = rx.get("tiers", {})
    return {
        "Plan Name":                              d.get("plan_name"),
        "Plan ID":                                d.get("plan_id"),
        "Plan Type":                              d.get("plan_type"),
        "Insurer":                                d.get("insurer"),
        "Metal Level":                            d.get("metal_level"),
        "Actuarial Value":                        d.get("actuarial_value"),
        "Plan Year":                              d.get("plan_year"),
        "Group Size":                             d.get("group_size"),
        "Coverage Area":                          d.get("coverage_area"),
        "Network Name":                           d.get("network_name"),
        "NAIC Code":                              d.get("naic_code"),
        "Deductible Indiv (In-Network)":          de.get("in_network", {}).get("individual"),
        "Deductible Family (In-Network)":         de.get("in_network", {}).get("family"),
        "Deductible Indiv (Out-of-Network)":      de.get("out_of_network", {}).get("individual"),
        "Deductible Family (Out-of-Network)":     de.get("out_of_network", {}).get("family"),
        "OOP Max Indiv (In-Network)":             op.get("in_network", {}).get("individual"),
        "OOP Max Family (In-Network)":            op.get("in_network", {}).get("family"),
        "OOP Max Indiv (OON)":                    op.get("out_of_network", {}).get("individual"),
        "OOP Max Family (OON)":                   op.get("out_of_network", {}).get("family"),
        "Copay PCP (In-Network)":                 co.get("primary_care_visit", {}).get("in_network"),
        "Copay Specialist (In-Network)":          co.get("specialist_visit", {}).get("in_network"),
        "Copay Urgent Care (In-Network)":         co.get("urgent_care", {}).get("in_network"),
        "Copay ER (In-Network)":                  co.get("emergency_room", {}).get("in_network"),
        "Copay Telehealth (In-Network)":          co.get("telehealth", {}).get("in_network"),
        "Coinsurance (In-Network)":               ci.get("in_network"),
        "Coinsurance (Out-of-Network)":           ci.get("out_of_network"),
        "Rx Formulary":                           rx.get("formulary_name"),
        "Rx Deductible Indiv":                    rx.get("deductible", {}).get("individual"),
        "Rx Tier 1 Generic (30-day)":             tiers.get("tier_1_generic", {}).get("retail_30_day"),
        "Rx Tier 2 Pref Brand (30-day)":          tiers.get("tier_2_preferred_brand", {}).get("retail_30_day"),
        "Rx Tier 3 Non-Pref (30-day)":            tiers.get("tier_3_non_preferred_brand", {}).get("retail_30_day"),
        "Rx Tier 4 Specialty (30-day)":           tiers.get("tier_4_specialty", {}).get("retail_30_day"),
        "Mail Order Required (Maintenance)":      rx.get("mail_order_required_for_maintenance"),
        "Preventive Care (In-Network)":           sv.get("preventive_care", {}).get("in_network"),
        "Inpatient Hospital (In-Network)":        sv.get("inpatient_hospital", {}).get("in_network"),
        "Outpatient Surgery (In-Network)":        sv.get("outpatient_surgery", {}).get("in_network"),
        "Lab Tests (In-Network)":                 sv.get("lab_tests", {}).get("in_network"),
        "Imaging CT/MRI (In-Network)":            sv.get("imaging_ct_mri_pet", {}).get("in_network"),
        "Mental Health Outpatient (In-Netw.)":    sv.get("mental_health_outpatient", {}).get("in_network"),
        "Physical Therapy (In-Network)":          sv.get("physical_therapy", {}).get("in_network"),
        "Chiropractic (In-Network)":              sv.get("chiropractic_care", {}).get("in_network"),
        "Maternity Delivery (In-Network)":        sv.get("maternity_delivery", {}).get("in_network"),
        "Pediatric Dental (In-Network)":          sv.get("pediatric_dental", {}).get("in_network"),
        "Pediatric Vision (In-Network)":          sv.get("pediatric_vision", {}).get("in_network"),
        "Bariatric Surgery (In-Network)":         sv.get("bariatric_surgery", {}).get("in_network"),
        "Transplants (In-Network)":               sv.get("transplants", {}).get("in_network"),
        "PT/OT/ST Visit Limit":                   plan.get("visit_limits", {}).get("physical_therapy"),
        "Chiropractic Visit Limit":               plan.get("visit_limits", {}).get("chiropractic"),
        "Home Health Visit Limit":                plan.get("visit_limits", {}).get("home_health"),
        "SNF Day Limit":                          plan.get("visit_limits", {}).get("skilled_nursing_facility"),
        "Requires PCP":                           ni.get("requires_pcp"),
        "Requires Referrals":                     ni.get("requires_referrals"),
        "OON Covered":                            ni.get("out_of_network_covered"),
        "National Network":                       ni.get("national_network"),
        "Wellness Program":                       ab.get("wellness_programs"),
        "EAP":                                    ab.get("employee_assistance_program"),
        "Telemedicine":                           ab.get("telemedicine"),
        "Fitness Reimbursement":                  ab.get("fitness_reimbursement"),
        "Nurse Advice Line":                      ab.get("nurse_advice_line"),
    }


# ── Build 500 plans ───────────────────────────────────────────────────────────

# Load 2 real JSON plans first
catalog_dir = os.path.join(os.path.dirname(__file__), "catalog")
all_plans = []
for path in sorted(glob.glob(os.path.join(catalog_dir, "*.json"))):
    with open(path) as f:
        all_plans.append(json.load(f))

# Generate the rest up to 500
metals      = list(METAL_CONFIG.keys())
plan_types  = PLAN_TYPES
areas       = COVERAGE_AREAS
group_sizes = GROUP_SIZES

combo_pool = list(itertools.product(INSURERS, metals, plan_types, areas, group_sizes))
random.shuffle(combo_pool)

idx = len(all_plans)
for insurer_row, metal, ptype, area, gsize in combo_pool:
    if len(all_plans) >= 500:
        break
    # Skip HMO with national area (unrealistic)
    if ptype in ("HMO", "EPO") and area == "National":
        continue
    plan = make_plan(idx, insurer_row, metal, ptype, area, gsize, seed_offset=idx)
    all_plans.append(plan)
    idx += 1

# If still under 500, fill with PPO national plans
while len(all_plans) < 500:
    insurer_row = random.choice(INSURERS)
    metal       = random.choice(metals)
    plan = make_plan(idx, insurer_row, metal, "PPO", "National", "Large Group (51+)", seed_offset=idx+9999)
    all_plans.append(plan)
    idx += 1

print(f"Total plans generated: {len(all_plans)}")

# ── Excel export ──────────────────────────────────────────────────────────────

rows    = [flat(p) for p in all_plans]
headers = list(rows[0].keys())

wb = openpyxl.Workbook(write_only=False)
ws = wb.active
ws.title = "Insurance Plans"

HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=10)
BORDER_SIDE = Side(style="thin", color="CCCCCC")
CELL_BORDER = Border(left=BORDER_SIDE, right=BORDER_SIDE, top=BORDER_SIDE, bottom=BORDER_SIDE)

SECTION_COLORS = [
    (range(1,  12), "E8F4FD"),   # Plan identity
    (range(12, 16), "FFF2CC"),   # Deductibles
    (range(16, 20), "E2EFDA"),   # OOP Max
    (range(20, 25), "FCE4D6"),   # Copays
    (range(25, 27), "F4CCCC"),   # Coinsurance
    (range(27, 35), "EAD1DC"),   # Rx
    (range(35, 48), "D9EAD3"),   # Services
    (range(48, 52), "CFE2F3"),   # Limits
    (range(52, 56), "FFF2CC"),   # Network
    (range(56, 61), "D9D2E9"),   # Benefits
]

ALT_DARKEN = {
    "E8F4FD": "C5DFF0", "FFF2CC": "FFE680", "E2EFDA": "C3DEB8",
    "FCE4D6": "F9CAAF", "F4CCCC": "EDA0A0", "EAD1DC": "D8A8BF",
    "D9EAD3": "B9D9B2", "CFE2F3": "AACCE8", "D9D2E9": "BCB2D8",
}

def get_section_color(col_idx, alt=False):
    for rng, color in SECTION_COLORS:
        if col_idx in rng:
            return ALT_DARKEN.get(color, "F0F0F0") if alt else color
    return "FFFFFF"

# Header
for col, header in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col, value=header)
    cell.fill      = HEADER_FILL
    cell.font      = HEADER_FONT
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border    = CELL_BORDER
ws.row_dimensions[1].height = 42

# Data rows
for ri, row in enumerate(rows, 2):
    alt = (ri % 2 == 0)
    for ci, key in enumerate(headers, 1):
        cell = ws.cell(row=ri, column=ci, value=row[key])
        cell.fill      = PatternFill("solid", fgColor=get_section_color(ci, alt))
        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=False)
        cell.border    = CELL_BORDER
    ws.row_dimensions[ri].height = 18

# Column widths
ws.column_dimensions["A"].width = 34
ws.column_dimensions["B"].width = 26
for c in range(3, len(headers)+1):
    ws.column_dimensions[get_column_letter(c)].width = 24

ws.freeze_panes = "A2"
ws.auto_filter.ref = ws.dimensions

out_path = os.path.join(catalog_dir, "insurance_plans_500.xlsx")
wb.save(out_path)
print(f"Saved: {out_path}  ({len(rows)} rows × {len(headers)} columns)")

# ── Print ground truth for the failing query ──────────────────────────────────
print("\n── Ground truth for the failing query ──────────────────────────────")
print("Query: PPO plan | deductible ≤ $1,000 | bariatric covered | gym ≥ $35/month | no referrals required\n")

def gym_amount(s):
    if not s or s == "Not included":
        return 0
    try:
        return int(s.split("$")[1].split("/")[0])
    except Exception:
        return 0

matches = []
for p in all_plans:
    d    = p["plan_details"]
    de   = p["deductibles"]["in_network"]
    ni   = p["network_information"]
    sv   = p["covered_services"]
    ab   = p["additional_benefits"]
    bar  = sv.get("bariatric_surgery", {}).get("in_network", "")
    gym  = gym_amount(ab.get("fitness_reimbursement", ""))

    if (d["plan_type"] == "PPO"
            and de["individual"] <= 1000
            and "Not covered" not in bar
            and gym >= 35
            and not ni.get("requires_referrals", True)):
        matches.append(f"  ✓ {d['plan_name']}  |  deductible=${de['individual']}  |  gym=${gym}/mo  |  bariatric={bar[:35]}")

print(f"Exact matches: {len(matches)}")
for m in matches[:10]:
    print(m)
if len(matches) > 10:
    print(f"  ... and {len(matches)-10} more")
