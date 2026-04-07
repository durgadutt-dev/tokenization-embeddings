import json
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ── helpers ──────────────────────────────────────────────────────────────────

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
        # ── Plan identity ──
        "Plan Name":            d.get("plan_name"),
        "Plan ID":              d.get("plan_id"),
        "Plan Type":            d.get("plan_type"),
        "Insurer":              d.get("insurer"),
        "Metal Level":          d.get("metal_level"),
        "Actuarial Value":      d.get("actuarial_value"),
        "Plan Year":            d.get("plan_year"),
        "Group Size":           d.get("group_size"),
        "Coverage Area":        d.get("coverage_area"),
        "Network Name":         d.get("network_name"),
        "NAIC Code":            d.get("naic_code"),

        # ── Deductibles ──
        "Deductible Indiv (In-Network)":    de.get("in_network", {}).get("individual"),
        "Deductible Family (In-Network)":   de.get("in_network", {}).get("family"),
        "Deductible Indiv (Out-of-Network)": de.get("out_of_network", {}).get("individual"),
        "Deductible Family (Out-of-Network)": de.get("out_of_network", {}).get("family"),

        # ── OOP Max ──
        "OOP Max Indiv (In-Network)":   op.get("in_network", {}).get("individual"),
        "OOP Max Family (In-Network)":  op.get("in_network", {}).get("family"),
        "OOP Max Indiv (OON)":          op.get("out_of_network", {}).get("individual"),
        "OOP Max Family (OON)":         op.get("out_of_network", {}).get("family"),

        # ── Copays ──
        "Copay PCP (In-Network)":       co.get("primary_care_visit", {}).get("in_network"),
        "Copay Specialist (In-Network)": co.get("specialist_visit", {}).get("in_network"),
        "Copay Urgent Care (In-Network)": co.get("urgent_care", {}).get("in_network"),
        "Copay ER (In-Network)":        co.get("emergency_room", {}).get("in_network"),
        "Copay Telehealth (In-Network)": co.get("telehealth", {}).get("in_network"),

        # ── Coinsurance ──
        "Coinsurance (In-Network)":     ci.get("in_network"),
        "Coinsurance (Out-of-Network)": ci.get("out_of_network"),

        # ── Rx ──
        "Rx Formulary":                 rx.get("formulary_name"),
        "Rx Deductible Indiv":          rx.get("deductible", {}).get("individual"),
        "Rx Tier 1 Generic (30-day)":   tiers.get("tier_1_generic", {}).get("retail_30_day"),
        "Rx Tier 2 Pref Brand (30-day)": tiers.get("tier_2_preferred_brand", {}).get("retail_30_day"),
        "Rx Tier 3 Non-Pref (30-day)":  tiers.get("tier_3_non_preferred_brand", {}).get("retail_30_day"),
        "Rx Tier 4 Specialty (30-day)": tiers.get("tier_4_specialty", {}).get("retail_30_day"),
        "Mail Order Required (Maintenance)": rx.get("mail_order_required_for_maintenance"),

        # ── Key covered services ──
        "Preventive Care (In-Network)":      sv.get("preventive_care", {}).get("in_network"),
        "Inpatient Hospital (In-Network)":   sv.get("inpatient_hospital", {}).get("in_network"),
        "Outpatient Surgery (In-Network)":   sv.get("outpatient_surgery", {}).get("in_network"),
        "Lab Tests (In-Network)":            sv.get("lab_tests", {}).get("in_network"),
        "Imaging CT/MRI (In-Network)":       sv.get("imaging_ct_mri_pet", {}).get("in_network"),
        "Mental Health Outpatient (In-Netw.)": sv.get("mental_health_outpatient", {}).get("in_network"),
        "Physical Therapy (In-Network)":     sv.get("physical_therapy", {}).get("in_network"),
        "Chiropractic (In-Network)":         sv.get("chiropractic_care", {}).get("in_network"),
        "Maternity Delivery (In-Network)":   sv.get("maternity_delivery", {}).get("in_network"),
        "Pediatric Dental (In-Network)":     sv.get("pediatric_dental", {}).get("in_network"),
        "Pediatric Vision (In-Network)":     sv.get("pediatric_vision", {}).get("in_network"),
        "Bariatric Surgery (In-Network)":    sv.get("bariatric_surgery", {}).get("in_network"),
        "Transplants (In-Network)":          sv.get("transplants", {}).get("in_network"),

        # ── Visit limits ──
        "PT/OT/ST Visit Limit":         plan.get("visit_limits", {}).get("physical_therapy"),
        "Chiropractic Visit Limit":     plan.get("visit_limits", {}).get("chiropractic"),
        "Home Health Visit Limit":      plan.get("visit_limits", {}).get("home_health"),
        "SNF Day Limit":                plan.get("visit_limits", {}).get("skilled_nursing_facility"),

        # ── Network ──
        "Requires PCP":                 ni.get("requires_pcp"),
        "Requires Referrals":           ni.get("requires_referrals"),
        "OON Covered":                  ni.get("out_of_network_covered"),
        "National Network":             ni.get("national_network"),

        # ── Additional benefits ──
        "Wellness Program":             ab.get("wellness_programs"),
        "EAP":                          ab.get("employee_assistance_program"),
        "Telemedicine":                 ab.get("telemedicine"),
        "Fitness Reimbursement":        ab.get("fitness_reimbursement"),
        "Nurse Advice Line":            ab.get("nurse_advice_line"),
    }


# ── 10 sample plans ───────────────────────────────────────────────────────────

SAMPLES = [
    {
        "plan_details": {"plan_name": "UnitedHealth Choice Plus — Bronze 6000", "plan_id": "UH-LG-PPO-B6000-2024",
                         "plan_type": "PPO", "insurer": "UnitedHealthcare Insurance Company",
                         "metal_level": "Bronze", "actuarial_value": "0.60", "plan_year": "2024",
                         "group_size": "Large Group (51+)", "coverage_area": "National",
                         "network_name": "UnitedHealth Choice Plus", "naic_code": "79413"},
        "deductibles": {"in_network": {"individual": 6000, "family": 12000},
                        "out_of_network": {"individual": 12000, "family": 24000}},
        "out_of_pocket_maximum": {"in_network": {"individual": 8700, "family": 17400},
                                  "out_of_network": {"individual": 17400, "family": 34800}},
        "copays": {"primary_care_visit": {"in_network": "$40", "out_of_network": "50% after deductible"},
                   "specialist_visit": {"in_network": "$80", "out_of_network": "50% after deductible"},
                   "urgent_care": {"in_network": "$90", "out_of_network": "$90"},
                   "emergency_room": {"in_network": "$400 per visit", "out_of_network": "$400 per visit"},
                   "telehealth": {"in_network": "$10", "out_of_network": "Not covered"}},
        "coinsurance": {"in_network": "40%", "out_of_network": "50%"},
        "prescription_drugs": {"formulary_name": "UHC Standard Formulary 2024",
                               "deductible": {"individual": 0, "family": 0},
                               "tiers": {"tier_1_generic": {"retail_30_day": "$15", "mail_order_90_day": "$30"},
                                         "tier_2_preferred_brand": {"retail_30_day": "$55", "mail_order_90_day": "$110"},
                                         "tier_3_non_preferred_brand": {"retail_30_day": "$110", "mail_order_90_day": "$220"},
                                         "tier_4_specialty": {"retail_30_day": "30% up to $350", "mail_order_90_day": "30% up to $700"}},
                               "mail_order_required_for_maintenance": True},
        "covered_services": {"preventive_care": {"in_network": "No charge", "out_of_network": "50% after deductible"},
                             "inpatient_hospital": {"in_network": "40% after deductible", "out_of_network": "50% after deductible"},
                             "outpatient_surgery": {"in_network": "40% after deductible", "out_of_network": "50% after deductible"},
                             "lab_tests": {"in_network": "40% after deductible", "out_of_network": "50% after deductible"},
                             "imaging_ct_mri_pet": {"in_network": "40% after deductible", "out_of_network": "50% after deductible"},
                             "mental_health_outpatient": {"in_network": "$40 copay", "out_of_network": "50% after deductible"},
                             "physical_therapy": {"in_network": "$80 copay per visit", "out_of_network": "50% after deductible"},
                             "chiropractic_care": {"in_network": "$80 copay per visit", "out_of_network": "50% after deductible"},
                             "maternity_delivery": {"in_network": "40% after deductible", "out_of_network": "50% after deductible"},
                             "pediatric_dental": {"in_network": "Not covered", "out_of_network": "Not covered"},
                             "pediatric_vision": {"in_network": "One exam/year no charge; $100 allowance", "out_of_network": "Not covered"},
                             "bariatric_surgery": {"in_network": "40% after deductible", "out_of_network": "Not covered"},
                             "transplants": {"in_network": "40% after deductible", "out_of_network": "Not covered"}},
        "visit_limits": {"physical_therapy": "50 combined PT/OT/ST visits per plan year", "chiropractic": "25 visits per plan year",
                         "home_health": "100 visits per plan year", "skilled_nursing_facility": "100 days per plan year"},
        "network_information": {"requires_pcp": False, "requires_referrals": False, "out_of_network_covered": True, "national_network": True},
        "additional_benefits": {"wellness_programs": "Rally Health — up to $300 annual incentive",
                                "employee_assistance_program": "OptumHealth EAP — 6 free sessions per issue",
                                "telemedicine": "Doctor on Demand — $10 per visit",
                                "fitness_reimbursement": "$30/month gym reimbursement",
                                "nurse_advice_line": "24/7 — 1-866-774-2060"},
    },
    {
        "plan_details": {"plan_name": "Anthem Blue Cross — Platinum 500", "plan_id": "AN-LG-PPO-P500-2024",
                         "plan_type": "PPO", "insurer": "Anthem Blue Cross Blue Shield",
                         "metal_level": "Platinum", "actuarial_value": "0.90", "plan_year": "2024",
                         "group_size": "Large Group (51+)", "coverage_area": "National",
                         "network_name": "BlueCard PPO", "naic_code": "14163"},
        "deductibles": {"in_network": {"individual": 500, "family": 1000},
                        "out_of_network": {"individual": 1000, "family": 2000}},
        "out_of_pocket_maximum": {"in_network": {"individual": 2500, "family": 5000},
                                  "out_of_network": {"individual": 5000, "family": 10000}},
        "copays": {"primary_care_visit": {"in_network": "$20", "out_of_network": "30% after deductible"},
                   "specialist_visit": {"in_network": "$40", "out_of_network": "30% after deductible"},
                   "urgent_care": {"in_network": "$50", "out_of_network": "$50"},
                   "emergency_room": {"in_network": "$250 per visit", "out_of_network": "$250 per visit"},
                   "telehealth": {"in_network": "$0", "out_of_network": "Not covered"}},
        "coinsurance": {"in_network": "10%", "out_of_network": "30%"},
        "prescription_drugs": {"formulary_name": "Anthem Premier Formulary 2024",
                               "deductible": {"individual": 0, "family": 0},
                               "tiers": {"tier_1_generic": {"retail_30_day": "$5", "mail_order_90_day": "$10"},
                                         "tier_2_preferred_brand": {"retail_30_day": "$30", "mail_order_90_day": "$60"},
                                         "tier_3_non_preferred_brand": {"retail_30_day": "$65", "mail_order_90_day": "$130"},
                                         "tier_4_specialty": {"retail_30_day": "20% up to $200", "mail_order_90_day": "20% up to $400"}},
                               "mail_order_required_for_maintenance": True},
        "covered_services": {"preventive_care": {"in_network": "No charge", "out_of_network": "30% after deductible"},
                             "inpatient_hospital": {"in_network": "10% after deductible", "out_of_network": "30% after deductible"},
                             "outpatient_surgery": {"in_network": "10% after deductible", "out_of_network": "30% after deductible"},
                             "lab_tests": {"in_network": "10% after deductible", "out_of_network": "30% after deductible"},
                             "imaging_ct_mri_pet": {"in_network": "10% after deductible", "out_of_network": "30% after deductible"},
                             "mental_health_outpatient": {"in_network": "$20 copay", "out_of_network": "30% after deductible"},
                             "physical_therapy": {"in_network": "$40 copay per visit", "out_of_network": "30% after deductible"},
                             "chiropractic_care": {"in_network": "$40 copay per visit", "out_of_network": "30% after deductible"},
                             "maternity_delivery": {"in_network": "10% after deductible", "out_of_network": "30% after deductible"},
                             "pediatric_dental": {"in_network": "Preventive: No charge; Basic: 10% after deductible", "out_of_network": "Not covered"},
                             "pediatric_vision": {"in_network": "One exam/year no charge; $200 allowance", "out_of_network": "Not covered"},
                             "bariatric_surgery": {"in_network": "10% after deductible", "out_of_network": "Not covered"},
                             "transplants": {"in_network": "10% after deductible", "out_of_network": "Not covered"}},
        "visit_limits": {"physical_therapy": "Unlimited", "chiropractic": "40 visits per plan year",
                         "home_health": "Unlimited", "skilled_nursing_facility": "180 days per plan year"},
        "network_information": {"requires_pcp": False, "requires_referrals": False, "out_of_network_covered": True, "national_network": True},
        "additional_benefits": {"wellness_programs": "Sydney Health App — up to $600 annual incentive",
                                "employee_assistance_program": "Anthem EAP — 8 free sessions per issue",
                                "telemedicine": "LiveHealth Online — $0 per visit",
                                "fitness_reimbursement": "$40/month gym reimbursement",
                                "nurse_advice_line": "24/7 — 1-800-337-4770"},
    },
    {
        "plan_details": {"plan_name": "Humana HMO — Gold 1000", "plan_id": "HU-LG-HMO-G1000-2024",
                         "plan_type": "HMO", "insurer": "Humana Health Plan Inc.",
                         "metal_level": "Gold", "actuarial_value": "0.80", "plan_year": "2024",
                         "group_size": "Large Group (51+)", "coverage_area": "Regional",
                         "network_name": "Humana Gold Plus HMO", "naic_code": "95885"},
        "deductibles": {"in_network": {"individual": 1000, "family": 2000},
                        "out_of_network": {"individual": None, "family": None}},
        "out_of_pocket_maximum": {"in_network": {"individual": 5500, "family": 11000},
                                  "out_of_network": {"individual": None, "family": None}},
        "copays": {"primary_care_visit": {"in_network": "$30", "out_of_network": "Not covered"},
                   "specialist_visit": {"in_network": "$65", "out_of_network": "Not covered"},
                   "urgent_care": {"in_network": "$65", "out_of_network": "Not covered"},
                   "emergency_room": {"in_network": "$300 per visit", "out_of_network": "$300 per visit"},
                   "telehealth": {"in_network": "$10", "out_of_network": "Not covered"}},
        "coinsurance": {"in_network": "20%", "out_of_network": "Not covered"},
        "prescription_drugs": {"formulary_name": "Humana Drug List 2024",
                               "deductible": {"individual": 250, "family": 500},
                               "tiers": {"tier_1_generic": {"retail_30_day": "$10", "mail_order_90_day": "$20"},
                                         "tier_2_preferred_brand": {"retail_30_day": "$50", "mail_order_90_day": "$100"},
                                         "tier_3_non_preferred_brand": {"retail_30_day": "$95", "mail_order_90_day": "$190"},
                                         "tier_4_specialty": {"retail_30_day": "25% up to $275", "mail_order_90_day": "25% up to $550"}},
                               "mail_order_required_for_maintenance": True},
        "covered_services": {"preventive_care": {"in_network": "No charge", "out_of_network": "Not covered"},
                             "inpatient_hospital": {"in_network": "20% after deductible", "out_of_network": "Not covered"},
                             "outpatient_surgery": {"in_network": "20% after deductible", "out_of_network": "Not covered"},
                             "lab_tests": {"in_network": "20% after deductible", "out_of_network": "Not covered"},
                             "imaging_ct_mri_pet": {"in_network": "20% after deductible", "out_of_network": "Not covered"},
                             "mental_health_outpatient": {"in_network": "$30 copay", "out_of_network": "Not covered"},
                             "physical_therapy": {"in_network": "$65 copay per visit", "out_of_network": "Not covered"},
                             "chiropractic_care": {"in_network": "$65 copay per visit", "out_of_network": "Not covered"},
                             "maternity_delivery": {"in_network": "20% after deductible", "out_of_network": "Not covered"},
                             "pediatric_dental": {"in_network": "Preventive: No charge; Basic: 20% after deductible", "out_of_network": "Not covered"},
                             "pediatric_vision": {"in_network": "One exam/year no charge; $150 allowance", "out_of_network": "Not covered"},
                             "bariatric_surgery": {"in_network": "Not covered", "out_of_network": "Not covered"},
                             "transplants": {"in_network": "20% after deductible", "out_of_network": "Not covered"}},
        "visit_limits": {"physical_therapy": "50 combined PT/OT/ST visits per plan year", "chiropractic": "20 visits per plan year",
                         "home_health": "90 visits per plan year", "skilled_nursing_facility": "90 days per plan year"},
        "network_information": {"requires_pcp": True, "requires_referrals": True, "out_of_network_covered": False, "national_network": False},
        "additional_benefits": {"wellness_programs": "Go365 — up to $500 annual reward",
                                "employee_assistance_program": "Humana EAP — 5 free sessions per issue",
                                "telemedicine": "Doctor on Demand — $10 per visit",
                                "fitness_reimbursement": "$25/month fitness reimbursement",
                                "nurse_advice_line": "24/7 — 1-800-789-7890"},
    },
    {
        "plan_details": {"plan_name": "Kaiser Permanente HMO — Gold 500", "plan_id": "KP-LG-HMO-G500-2024",
                         "plan_type": "HMO", "insurer": "Kaiser Foundation Health Plan",
                         "metal_level": "Gold", "actuarial_value": "0.80", "plan_year": "2024",
                         "group_size": "Large Group (51+)", "coverage_area": "Regional — Kaiser Service Areas",
                         "network_name": "Kaiser Permanente Medical Group", "naic_code": "95378"},
        "deductibles": {"in_network": {"individual": 500, "family": 1000},
                        "out_of_network": {"individual": None, "family": None}},
        "out_of_pocket_maximum": {"in_network": {"individual": 4500, "family": 9000},
                                  "out_of_network": {"individual": None, "family": None}},
        "copays": {"primary_care_visit": {"in_network": "$20", "out_of_network": "Not covered"},
                   "specialist_visit": {"in_network": "$35", "out_of_network": "Not covered"},
                   "urgent_care": {"in_network": "$35", "out_of_network": "Not covered"},
                   "emergency_room": {"in_network": "$250 per visit", "out_of_network": "$250 per visit"},
                   "telehealth": {"in_network": "$0", "out_of_network": "Not covered"}},
        "coinsurance": {"in_network": "20%", "out_of_network": "Not covered"},
        "prescription_drugs": {"formulary_name": "Kaiser Permanente Drug Formulary 2024",
                               "deductible": {"individual": 0, "family": 0},
                               "tiers": {"tier_1_generic": {"retail_30_day": "$10", "mail_order_90_day": "$20"},
                                         "tier_2_preferred_brand": {"retail_30_day": "$40", "mail_order_90_day": "$80"},
                                         "tier_3_non_preferred_brand": {"retail_30_day": "$70", "mail_order_90_day": "$140"},
                                         "tier_4_specialty": {"retail_30_day": "20% up to $200", "mail_order_90_day": "20% up to $400"}},
                               "mail_order_required_for_maintenance": False},
        "covered_services": {"preventive_care": {"in_network": "No charge", "out_of_network": "Not covered"},
                             "inpatient_hospital": {"in_network": "20% after deductible", "out_of_network": "Emergency only"},
                             "outpatient_surgery": {"in_network": "20% after deductible", "out_of_network": "Not covered"},
                             "lab_tests": {"in_network": "$20 per visit", "out_of_network": "Not covered"},
                             "imaging_ct_mri_pet": {"in_network": "20% after deductible", "out_of_network": "Not covered"},
                             "mental_health_outpatient": {"in_network": "$20 copay", "out_of_network": "Not covered"},
                             "physical_therapy": {"in_network": "$35 copay per visit", "out_of_network": "Not covered"},
                             "chiropractic_care": {"in_network": "$35 copay per visit", "out_of_network": "Not covered"},
                             "maternity_delivery": {"in_network": "20% after deductible", "out_of_network": "Not covered"},
                             "pediatric_dental": {"in_network": "Included; Preventive no charge", "out_of_network": "Not covered"},
                             "pediatric_vision": {"in_network": "One exam/year no charge; $175 allowance", "out_of_network": "Not covered"},
                             "bariatric_surgery": {"in_network": "20% after deductible (with criteria)", "out_of_network": "Not covered"},
                             "transplants": {"in_network": "20% after deductible", "out_of_network": "Not covered"}},
        "visit_limits": {"physical_therapy": "60 combined PT/OT/ST visits per plan year", "chiropractic": "30 visits per plan year",
                         "home_health": "Unlimited medically necessary", "skilled_nursing_facility": "100 days per plan year"},
        "network_information": {"requires_pcp": True, "requires_referrals": False, "out_of_network_covered": False, "national_network": False},
        "additional_benefits": {"wellness_programs": "Kaiser Thrive — up to $400 annual incentive",
                                "employee_assistance_program": "Kaiser EAP — unlimited telephonic counseling",
                                "telemedicine": "Kaiser Video Visit — $0 per visit",
                                "fitness_reimbursement": "$20/month fitness reimbursement",
                                "nurse_advice_line": "24/7 — 1-800-290-4400"},
    },
    {
        "plan_details": {"plan_name": "BCBS PPO — Silver 3500", "plan_id": "BC-LG-PPO-S3500-2024",
                         "plan_type": "PPO", "insurer": "Blue Cross Blue Shield of Illinois",
                         "metal_level": "Silver", "actuarial_value": "0.70", "plan_year": "2024",
                         "group_size": "Large Group (51+)", "coverage_area": "National",
                         "network_name": "BlueCard Preferred Provider", "naic_code": "54771"},
        "deductibles": {"in_network": {"individual": 3500, "family": 7000},
                        "out_of_network": {"individual": 7000, "family": 14000}},
        "out_of_pocket_maximum": {"in_network": {"individual": 7900, "family": 15800},
                                  "out_of_network": {"individual": 15800, "family": 31600}},
        "copays": {"primary_care_visit": {"in_network": "$35", "out_of_network": "50% after deductible"},
                   "specialist_visit": {"in_network": "$70", "out_of_network": "50% after deductible"},
                   "urgent_care": {"in_network": "$75", "out_of_network": "$75"},
                   "emergency_room": {"in_network": "$375 per visit", "out_of_network": "$375 per visit"},
                   "telehealth": {"in_network": "$10", "out_of_network": "Not covered"}},
        "coinsurance": {"in_network": "30%", "out_of_network": "50%"},
        "prescription_drugs": {"formulary_name": "BCBS Value Formulary 2024",
                               "deductible": {"individual": 500, "family": 1000},
                               "tiers": {"tier_1_generic": {"retail_30_day": "$12", "mail_order_90_day": "$24"},
                                         "tier_2_preferred_brand": {"retail_30_day": "$50", "mail_order_90_day": "$100"},
                                         "tier_3_non_preferred_brand": {"retail_30_day": "$95", "mail_order_90_day": "$190"},
                                         "tier_4_specialty": {"retail_30_day": "30% up to $300", "mail_order_90_day": "30% up to $600"}},
                               "mail_order_required_for_maintenance": True},
        "covered_services": {"preventive_care": {"in_network": "No charge", "out_of_network": "50% after deductible"},
                             "inpatient_hospital": {"in_network": "30% after deductible", "out_of_network": "50% after deductible"},
                             "outpatient_surgery": {"in_network": "30% after deductible", "out_of_network": "50% after deductible"},
                             "lab_tests": {"in_network": "30% after deductible", "out_of_network": "50% after deductible"},
                             "imaging_ct_mri_pet": {"in_network": "30% after deductible", "out_of_network": "50% after deductible"},
                             "mental_health_outpatient": {"in_network": "$35 copay", "out_of_network": "50% after deductible"},
                             "physical_therapy": {"in_network": "$70 copay per visit", "out_of_network": "50% after deductible"},
                             "chiropractic_care": {"in_network": "$70 copay per visit", "out_of_network": "50% after deductible"},
                             "maternity_delivery": {"in_network": "30% after deductible", "out_of_network": "50% after deductible"},
                             "pediatric_dental": {"in_network": "Not covered — separate plan required", "out_of_network": "Not covered"},
                             "pediatric_vision": {"in_network": "One exam/year no charge; $125 allowance", "out_of_network": "Not covered"},
                             "bariatric_surgery": {"in_network": "30% after deductible", "out_of_network": "Not covered"},
                             "transplants": {"in_network": "30% after deductible", "out_of_network": "Not covered"}},
        "visit_limits": {"physical_therapy": "60 combined PT/OT/ST visits per plan year", "chiropractic": "30 visits per plan year",
                         "home_health": "120 visits per plan year", "skilled_nursing_facility": "120 days per plan year"},
        "network_information": {"requires_pcp": False, "requires_referrals": False, "out_of_network_covered": True, "national_network": True},
        "additional_benefits": {"wellness_programs": "Blue365 — up to $350 annual incentive",
                                "employee_assistance_program": "BCBS EAP — 6 free sessions per issue",
                                "telemedicine": "Teladoc — $10 per visit",
                                "fitness_reimbursement": "$25/month gym reimbursement",
                                "nurse_advice_line": "24/7 — 1-800-282-8161"},
    },
    {
        "plan_details": {"plan_name": "Molina Marketplace — Silver 2000 HMO", "plan_id": "MO-LG-HMO-S2000-2024",
                         "plan_type": "HMO", "insurer": "Molina Healthcare of California",
                         "metal_level": "Silver", "actuarial_value": "0.70", "plan_year": "2024",
                         "group_size": "Small Group (1–50)", "coverage_area": "Regional — California",
                         "network_name": "Molina Marketplace Network", "naic_code": "96776"},
        "deductibles": {"in_network": {"individual": 2000, "family": 4000},
                        "out_of_network": {"individual": None, "family": None}},
        "out_of_pocket_maximum": {"in_network": {"individual": 7000, "family": 14000},
                                  "out_of_network": {"individual": None, "family": None}},
        "copays": {"primary_care_visit": {"in_network": "$30", "out_of_network": "Not covered"},
                   "specialist_visit": {"in_network": "$60", "out_of_network": "Not covered"},
                   "urgent_care": {"in_network": "$60", "out_of_network": "Not covered"},
                   "emergency_room": {"in_network": "$350 per visit", "out_of_network": "$350 per visit"},
                   "telehealth": {"in_network": "$0", "out_of_network": "Not covered"}},
        "coinsurance": {"in_network": "30%", "out_of_network": "Not covered"},
        "prescription_drugs": {"formulary_name": "Molina PDL 2024",
                               "deductible": {"individual": 0, "family": 0},
                               "tiers": {"tier_1_generic": {"retail_30_day": "$3", "mail_order_90_day": "$6"},
                                         "tier_2_preferred_brand": {"retail_30_day": "$45", "mail_order_90_day": "$90"},
                                         "tier_3_non_preferred_brand": {"retail_30_day": "$80", "mail_order_90_day": "$160"},
                                         "tier_4_specialty": {"retail_30_day": "25% up to $250", "mail_order_90_day": "25% up to $500"}},
                               "mail_order_required_for_maintenance": False},
        "covered_services": {"preventive_care": {"in_network": "No charge", "out_of_network": "Not covered"},
                             "inpatient_hospital": {"in_network": "30% after deductible", "out_of_network": "Not covered"},
                             "outpatient_surgery": {"in_network": "30% after deductible", "out_of_network": "Not covered"},
                             "lab_tests": {"in_network": "30% after deductible", "out_of_network": "Not covered"},
                             "imaging_ct_mri_pet": {"in_network": "30% after deductible", "out_of_network": "Not covered"},
                             "mental_health_outpatient": {"in_network": "$30 copay", "out_of_network": "Not covered"},
                             "physical_therapy": {"in_network": "$60 copay per visit", "out_of_network": "Not covered"},
                             "chiropractic_care": {"in_network": "Not covered", "out_of_network": "Not covered"},
                             "maternity_delivery": {"in_network": "30% after deductible", "out_of_network": "Not covered"},
                             "pediatric_dental": {"in_network": "Preventive: No charge; Basic: 30% after deductible", "out_of_network": "Not covered"},
                             "pediatric_vision": {"in_network": "One exam/year no charge; $100 allowance", "out_of_network": "Not covered"},
                             "bariatric_surgery": {"in_network": "Not covered", "out_of_network": "Not covered"},
                             "transplants": {"in_network": "30% after deductible", "out_of_network": "Not covered"}},
        "visit_limits": {"physical_therapy": "40 combined PT/OT/ST visits per plan year", "chiropractic": "Not covered",
                         "home_health": "80 visits per plan year", "skilled_nursing_facility": "60 days per plan year"},
        "network_information": {"requires_pcp": True, "requires_referrals": True, "out_of_network_covered": False, "national_network": False},
        "additional_benefits": {"wellness_programs": "Molina Healthy Living — up to $200 annual incentive",
                                "employee_assistance_program": "Molina EAP — 3 free sessions per issue",
                                "telemedicine": "Teladoc — $0 per visit",
                                "fitness_reimbursement": "Not included",
                                "nurse_advice_line": "24/7 — 1-888-665-4621"},
    },
    {
        "plan_details": {"plan_name": "Oscar Health PPO — Bronze 5000", "plan_id": "OS-LG-PPO-B5000-2024",
                         "plan_type": "PPO", "insurer": "Oscar Health Insurance Corp.",
                         "metal_level": "Bronze", "actuarial_value": "0.60", "plan_year": "2024",
                         "group_size": "Small Group (1–50)", "coverage_area": "Regional — Select States",
                         "network_name": "Oscar Select Network", "naic_code": "15524"},
        "deductibles": {"in_network": {"individual": 5000, "family": 10000},
                        "out_of_network": {"individual": 10000, "family": 20000}},
        "out_of_pocket_maximum": {"in_network": {"individual": 8700, "family": 17400},
                                  "out_of_network": {"individual": 17400, "family": 34800}},
        "copays": {"primary_care_visit": {"in_network": "$3 (first 3 visits free)", "out_of_network": "50% after deductible"},
                   "specialist_visit": {"in_network": "$75 after deductible", "out_of_network": "50% after deductible"},
                   "urgent_care": {"in_network": "$75 after deductible", "out_of_network": "$75 after deductible"},
                   "emergency_room": {"in_network": "$500 after deductible", "out_of_network": "$500 after deductible"},
                   "telehealth": {"in_network": "$0 (unlimited via Oscar app)", "out_of_network": "Not covered"}},
        "coinsurance": {"in_network": "40%", "out_of_network": "50%"},
        "prescription_drugs": {"formulary_name": "Oscar Drug Formulary 2024",
                               "deductible": {"individual": 0, "family": 0},
                               "tiers": {"tier_1_generic": {"retail_30_day": "$3", "mail_order_90_day": "$6"},
                                         "tier_2_preferred_brand": {"retail_30_day": "$60", "mail_order_90_day": "$120"},
                                         "tier_3_non_preferred_brand": {"retail_30_day": "$110", "mail_order_90_day": "$220"},
                                         "tier_4_specialty": {"retail_30_day": "30% up to $300", "mail_order_90_day": "30% up to $600"}},
                               "mail_order_required_for_maintenance": False},
        "covered_services": {"preventive_care": {"in_network": "No charge", "out_of_network": "50% after deductible"},
                             "inpatient_hospital": {"in_network": "40% after deductible", "out_of_network": "50% after deductible"},
                             "outpatient_surgery": {"in_network": "40% after deductible", "out_of_network": "50% after deductible"},
                             "lab_tests": {"in_network": "40% after deductible", "out_of_network": "50% after deductible"},
                             "imaging_ct_mri_pet": {"in_network": "40% after deductible", "out_of_network": "50% after deductible"},
                             "mental_health_outpatient": {"in_network": "$0 via Oscar app; $75 in-person after deductible", "out_of_network": "50% after deductible"},
                             "physical_therapy": {"in_network": "$75 copay after deductible", "out_of_network": "50% after deductible"},
                             "chiropractic_care": {"in_network": "$75 copay after deductible", "out_of_network": "50% after deductible"},
                             "maternity_delivery": {"in_network": "40% after deductible", "out_of_network": "50% after deductible"},
                             "pediatric_dental": {"in_network": "Not covered — separate plan", "out_of_network": "Not covered"},
                             "pediatric_vision": {"in_network": "One exam/year no charge; $100 allowance", "out_of_network": "Not covered"},
                             "bariatric_surgery": {"in_network": "Not covered", "out_of_network": "Not covered"},
                             "transplants": {"in_network": "40% after deductible", "out_of_network": "Not covered"}},
        "visit_limits": {"physical_therapy": "40 combined PT/OT/ST visits per plan year", "chiropractic": "20 visits per plan year",
                         "home_health": "100 visits per plan year", "skilled_nursing_facility": "60 days per plan year"},
        "network_information": {"requires_pcp": False, "requires_referrals": False, "out_of_network_covered": True, "national_network": False},
        "additional_benefits": {"wellness_programs": "Oscar Rewards — $1/day for walking goals, up to $365/year",
                                "employee_assistance_program": "Included — 6 free sessions per issue",
                                "telemedicine": "Oscar Virtual Urgent Care — $0 unlimited",
                                "fitness_reimbursement": "Not included",
                                "nurse_advice_line": "24/7 Concierge Team — in-app"},
    },
    {
        "plan_details": {"plan_name": "Centene Ambetter — Gold 750 HMO", "plan_id": "CE-LG-HMO-G750-2024",
                         "plan_type": "HMO", "insurer": "Centene Corporation / Ambetter",
                         "metal_level": "Gold", "actuarial_value": "0.80", "plan_year": "2024",
                         "group_size": "Individual & Family Plan", "coverage_area": "Regional — Select States",
                         "network_name": "Ambetter Essential Care Network", "naic_code": "78700"},
        "deductibles": {"in_network": {"individual": 750, "family": 1500},
                        "out_of_network": {"individual": None, "family": None}},
        "out_of_pocket_maximum": {"in_network": {"individual": 6000, "family": 12000},
                                  "out_of_network": {"individual": None, "family": None}},
        "copays": {"primary_care_visit": {"in_network": "$35", "out_of_network": "Not covered"},
                   "specialist_visit": {"in_network": "$70", "out_of_network": "Not covered"},
                   "urgent_care": {"in_network": "$70", "out_of_network": "Not covered"},
                   "emergency_room": {"in_network": "$325 per visit", "out_of_network": "$325 per visit"},
                   "telehealth": {"in_network": "$0", "out_of_network": "Not covered"}},
        "coinsurance": {"in_network": "20%", "out_of_network": "Not covered"},
        "prescription_drugs": {"formulary_name": "Ambetter Drug List 2024",
                               "deductible": {"individual": 0, "family": 0},
                               "tiers": {"tier_1_generic": {"retail_30_day": "$5", "mail_order_90_day": "$10"},
                                         "tier_2_preferred_brand": {"retail_30_day": "$45", "mail_order_90_day": "$90"},
                                         "tier_3_non_preferred_brand": {"retail_30_day": "$85", "mail_order_90_day": "$170"},
                                         "tier_4_specialty": {"retail_30_day": "25% up to $250", "mail_order_90_day": "25% up to $500"}},
                               "mail_order_required_for_maintenance": True},
        "covered_services": {"preventive_care": {"in_network": "No charge", "out_of_network": "Not covered"},
                             "inpatient_hospital": {"in_network": "20% after deductible", "out_of_network": "Not covered"},
                             "outpatient_surgery": {"in_network": "20% after deductible", "out_of_network": "Not covered"},
                             "lab_tests": {"in_network": "20% after deductible", "out_of_network": "Not covered"},
                             "imaging_ct_mri_pet": {"in_network": "20% after deductible", "out_of_network": "Not covered"},
                             "mental_health_outpatient": {"in_network": "$35 copay", "out_of_network": "Not covered"},
                             "physical_therapy": {"in_network": "$70 copay per visit", "out_of_network": "Not covered"},
                             "chiropractic_care": {"in_network": "$70 copay per visit", "out_of_network": "Not covered"},
                             "maternity_delivery": {"in_network": "20% after deductible", "out_of_network": "Not covered"},
                             "pediatric_dental": {"in_network": "Preventive: No charge; Basic: 20% after deductible", "out_of_network": "Not covered"},
                             "pediatric_vision": {"in_network": "One exam/year no charge; $150 allowance", "out_of_network": "Not covered"},
                             "bariatric_surgery": {"in_network": "Not covered", "out_of_network": "Not covered"},
                             "transplants": {"in_network": "20% after deductible", "out_of_network": "Not covered"}},
        "visit_limits": {"physical_therapy": "50 combined PT/OT/ST visits per plan year", "chiropractic": "20 visits per plan year",
                         "home_health": "100 visits per plan year", "skilled_nursing_facility": "90 days per plan year"},
        "network_information": {"requires_pcp": True, "requires_referrals": True, "out_of_network_covered": False, "national_network": False},
        "additional_benefits": {"wellness_programs": "Ambetter Healthy Rewards — up to $300 annual incentive",
                                "employee_assistance_program": "Not included",
                                "telemedicine": "24/7 Teladoc — $0 per visit",
                                "fitness_reimbursement": "Not included",
                                "nurse_advice_line": "24/7 — 1-833-514-0390"},
    },
    {
        "plan_details": {"plan_name": "Highmark BCBS PPO — Silver 2000", "plan_id": "HM-LG-PPO-S2000-2024",
                         "plan_type": "PPO", "insurer": "Highmark Blue Cross Blue Shield",
                         "metal_level": "Silver", "actuarial_value": "0.70", "plan_year": "2024",
                         "group_size": "Large Group (51+)", "coverage_area": "Regional — PA/WV/DE",
                         "network_name": "Highmark Blue Network", "naic_code": "20427"},
        "deductibles": {"in_network": {"individual": 2000, "family": 4000},
                        "out_of_network": {"individual": 4000, "family": 8000}},
        "out_of_pocket_maximum": {"in_network": {"individual": 6500, "family": 13000},
                                  "out_of_network": {"individual": 13000, "family": 26000}},
        "copays": {"primary_care_visit": {"in_network": "$30", "out_of_network": "40% after deductible"},
                   "specialist_visit": {"in_network": "$65", "out_of_network": "40% after deductible"},
                   "urgent_care": {"in_network": "$65", "out_of_network": "$65"},
                   "emergency_room": {"in_network": "$300 per visit", "out_of_network": "$300 per visit"},
                   "telehealth": {"in_network": "$5", "out_of_network": "Not covered"}},
        "coinsurance": {"in_network": "30%", "out_of_network": "40%"},
        "prescription_drugs": {"formulary_name": "Highmark Drug Formulary 2024",
                               "deductible": {"individual": 250, "family": 500},
                               "tiers": {"tier_1_generic": {"retail_30_day": "$10", "mail_order_90_day": "$20"},
                                         "tier_2_preferred_brand": {"retail_30_day": "$48", "mail_order_90_day": "$96"},
                                         "tier_3_non_preferred_brand": {"retail_30_day": "$90", "mail_order_90_day": "$180"},
                                         "tier_4_specialty": {"retail_30_day": "25% up to $275", "mail_order_90_day": "25% up to $550"}},
                               "mail_order_required_for_maintenance": True},
        "covered_services": {"preventive_care": {"in_network": "No charge", "out_of_network": "40% after deductible"},
                             "inpatient_hospital": {"in_network": "30% after deductible", "out_of_network": "40% after deductible"},
                             "outpatient_surgery": {"in_network": "30% after deductible", "out_of_network": "40% after deductible"},
                             "lab_tests": {"in_network": "30% after deductible", "out_of_network": "40% after deductible"},
                             "imaging_ct_mri_pet": {"in_network": "30% after deductible", "out_of_network": "40% after deductible"},
                             "mental_health_outpatient": {"in_network": "$30 copay", "out_of_network": "40% after deductible"},
                             "physical_therapy": {"in_network": "$65 copay per visit", "out_of_network": "40% after deductible"},
                             "chiropractic_care": {"in_network": "$65 copay per visit", "out_of_network": "40% after deductible"},
                             "maternity_delivery": {"in_network": "30% after deductible", "out_of_network": "40% after deductible"},
                             "pediatric_dental": {"in_network": "Not covered — separate plan", "out_of_network": "Not covered"},
                             "pediatric_vision": {"in_network": "One exam/year no charge; $125 allowance", "out_of_network": "Not covered"},
                             "bariatric_surgery": {"in_network": "30% after deductible", "out_of_network": "Not covered"},
                             "transplants": {"in_network": "30% after deductible", "out_of_network": "Not covered"}},
        "visit_limits": {"physical_therapy": "60 combined PT/OT/ST visits per plan year", "chiropractic": "30 visits per plan year",
                         "home_health": "120 visits per plan year", "skilled_nursing_facility": "120 days per plan year"},
        "network_information": {"requires_pcp": False, "requires_referrals": False, "out_of_network_covered": True, "national_network": False},
        "additional_benefits": {"wellness_programs": "Highmark Well360 — up to $400 annual incentive",
                                "employee_assistance_program": "Highmark EAP — 6 free sessions per issue",
                                "telemedicine": "Teladoc — $5 per visit",
                                "fitness_reimbursement": "$25/month gym reimbursement",
                                "nurse_advice_line": "24/7 — 1-800-651-5465"},
    },
    {
        "plan_details": {"plan_name": "Health Net Salud HMO — Silver 1500", "plan_id": "HN-LG-HMO-S1500-2024",
                         "plan_type": "HMO", "insurer": "Health Net of California",
                         "metal_level": "Silver", "actuarial_value": "0.70", "plan_year": "2024",
                         "group_size": "Small Group (1–50)", "coverage_area": "Regional — California",
                         "network_name": "Health Net CA Network", "naic_code": "95301"},
        "deductibles": {"in_network": {"individual": 1500, "family": 3000},
                        "out_of_network": {"individual": None, "family": None}},
        "out_of_pocket_maximum": {"in_network": {"individual": 7200, "family": 14400},
                                  "out_of_network": {"individual": None, "family": None}},
        "copays": {"primary_care_visit": {"in_network": "$30", "out_of_network": "Not covered"},
                   "specialist_visit": {"in_network": "$60", "out_of_network": "Not covered"},
                   "urgent_care": {"in_network": "$60", "out_of_network": "Not covered"},
                   "emergency_room": {"in_network": "$300 per visit", "out_of_network": "$300 per visit"},
                   "telehealth": {"in_network": "$10", "out_of_network": "Not covered"}},
        "coinsurance": {"in_network": "30%", "out_of_network": "Not covered"},
        "prescription_drugs": {"formulary_name": "Health Net Drug Formulary 2024",
                               "deductible": {"individual": 250, "family": 500},
                               "tiers": {"tier_1_generic": {"retail_30_day": "$10", "mail_order_90_day": "$20"},
                                         "tier_2_preferred_brand": {"retail_30_day": "$50", "mail_order_90_day": "$100"},
                                         "tier_3_non_preferred_brand": {"retail_30_day": "$90", "mail_order_90_day": "$180"},
                                         "tier_4_specialty": {"retail_30_day": "25% up to $250", "mail_order_90_day": "25% up to $500"}},
                               "mail_order_required_for_maintenance": True},
        "covered_services": {"preventive_care": {"in_network": "No charge", "out_of_network": "Not covered"},
                             "inpatient_hospital": {"in_network": "30% after deductible", "out_of_network": "Not covered"},
                             "outpatient_surgery": {"in_network": "30% after deductible", "out_of_network": "Not covered"},
                             "lab_tests": {"in_network": "30% after deductible", "out_of_network": "Not covered"},
                             "imaging_ct_mri_pet": {"in_network": "30% after deductible", "out_of_network": "Not covered"},
                             "mental_health_outpatient": {"in_network": "$30 copay", "out_of_network": "Not covered"},
                             "physical_therapy": {"in_network": "$60 copay per visit", "out_of_network": "Not covered"},
                             "chiropractic_care": {"in_network": "$60 copay per visit", "out_of_network": "Not covered"},
                             "maternity_delivery": {"in_network": "30% after deductible", "out_of_network": "Not covered"},
                             "pediatric_dental": {"in_network": "Preventive: No charge; Basic: 30% after deductible", "out_of_network": "Not covered"},
                             "pediatric_vision": {"in_network": "One exam/year no charge; $100 allowance", "out_of_network": "Not covered"},
                             "bariatric_surgery": {"in_network": "30% after deductible (criteria required)", "out_of_network": "Not covered"},
                             "transplants": {"in_network": "30% after deductible", "out_of_network": "Not covered"}},
        "visit_limits": {"physical_therapy": "45 combined PT/OT/ST visits per plan year", "chiropractic": "20 visits per plan year",
                         "home_health": "100 visits per plan year", "skilled_nursing_facility": "100 days per plan year"},
        "network_information": {"requires_pcp": True, "requires_referrals": True, "out_of_network_covered": False, "national_network": False},
        "additional_benefits": {"wellness_programs": "Health Net Well-Being — up to $300 annual incentive",
                                "employee_assistance_program": "Managed Health Network EAP — 6 free sessions per issue",
                                "telemedicine": "Teladoc — $10 per visit",
                                "fitness_reimbursement": "$20/month gym reimbursement",
                                "nurse_advice_line": "24/7 — 1-800-675-6110"},
    },
]


# ── load existing JSON plans ──────────────────────────────────────────────────

import glob, os

catalog_dir = os.path.join(os.path.dirname(__file__), "catalog")
plans = []
for path in sorted(glob.glob(os.path.join(catalog_dir, "*.json"))):
    with open(path) as f:
        plans.append(json.load(f))

plans.extend(SAMPLES)

# ── flatten all plans ─────────────────────────────────────────────────────────

rows = [flat(p) for p in plans]
headers = list(rows[0].keys())

# ── build workbook ────────────────────────────────────────────────────────────

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Insurance Plans"

HEADER_FILL   = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT   = Font(bold=True, color="FFFFFF", size=11)
ALT_FILL      = PatternFill("solid", fgColor="D6E4F0")
BORDER_SIDE   = Side(style="thin", color="BFBFBF")
CELL_BORDER   = Border(left=BORDER_SIDE, right=BORDER_SIDE, top=BORDER_SIDE, bottom=BORDER_SIDE)

# section colours (column index ranges, 1-based)
SECTION_COLORS = {
    range(1, 12):  "E8F4FD",   # Plan identity
    range(12, 16): "FFF2CC",   # Deductibles
    range(16, 20): "E2EFDA",   # OOP Max
    range(20, 25): "FCE4D6",   # Copays
    range(25, 27): "F4CCCC",   # Coinsurance
    range(27, 34): "EAD1DC",   # Rx
    range(34, 47): "D9EAD3",   # Services
    range(47, 51): "CFE2F3",   # Limits
    range(51, 55): "FFF2CC",   # Network
    range(55, 60): "D9D2E9",   # Benefits
}

def section_color(col_idx):
    for rng, color in SECTION_COLORS.items():
        if col_idx in rng:
            return color
    return "FFFFFF"

# Header row
for col, header in enumerate(headers, start=1):
    cell = ws.cell(row=1, column=col, value=header)
    cell.fill   = HEADER_FILL
    cell.font   = HEADER_FONT
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = CELL_BORDER

ws.row_dimensions[1].height = 45

# Data rows
for row_idx, row in enumerate(rows, start=2):
    bg = ALT_FILL if row_idx % 2 == 0 else None
    for col_idx, key in enumerate(headers, start=1):
        val = row[key]
        cell = ws.cell(row=row_idx, column=col_idx, value=val)
        sc = section_color(col_idx)
        if row_idx % 2 == 0:
            # slightly darken section colour for alt rows
            cell.fill = PatternFill("solid", fgColor=sc)
        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        cell.border = CELL_BORDER
    ws.row_dimensions[row_idx].height = 30

# Column widths
ws.column_dimensions["A"].width = 36  # Plan Name
ws.column_dimensions["B"].width = 22  # Plan ID
for col in range(3, len(headers) + 1):
    ws.column_dimensions[get_column_letter(col)].width = 26

# Freeze header
ws.freeze_panes = "A2"

# Auto-filter
ws.auto_filter.ref = ws.dimensions

out_path = os.path.join(os.path.dirname(__file__), "catalog", "insurance_plans.xlsx")
wb.save(out_path)
print(f"Saved: {out_path}  ({len(rows)} plans, {len(headers)} columns)")
