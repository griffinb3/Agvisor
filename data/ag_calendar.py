from datetime import date, datetime
from typing import Optional


SEASONAL_ACTIVITIES = {
    "spring": {
        "months": [3, 4, 5],
        "label": "Spring (March–May)",
        "general": [
            "Soil testing and field preparation",
            "Planting season for row crops (corn, soybeans, cotton, rice)",
            "Spring fertilizer and herbicide applications",
            "Equipment maintenance and calibration",
            "Crop insurance acreage reporting deadlines approaching",
            "Pasture renovation and weed control",
            "Review and finalize marketing plans for the crop year",
        ],
        "livestock": [
            "Spring calving and lambing season",
            "Vaccinations and health protocols for newborns",
            "Turnout to pasture — assess forage readiness",
            "Breeding season planning for fall calving herds",
            "Parasite management (deworming)",
            "Fence repair and water system checks",
        ],
        "crops": [
            "Finalize seed orders and treat seed if needed",
            "Monitor soil temperature and moisture for planting windows",
            "Apply pre-emergence herbicides",
            "Scout for early-season pests (cutworms, seedling diseases)",
            "Calibrate planters and drills",
            "Consider cover crop termination timing",
        ],
    },
    "summer": {
        "months": [6, 7, 8],
        "label": "Summer (June–August)",
        "general": [
            "Crop monitoring and scouting",
            "Irrigation management — monitor soil moisture",
            "Integrated pest management (IPM) critical period",
            "Hay cutting and baling (first and second cuttings)",
            "Review mid-season marketing opportunities",
            "Monitor weather forecasts for storms and drought",
            "Consider forward contracting for fall harvest",
        ],
        "livestock": [
            "Heat stress management for cattle and poultry",
            "Fly and parasite control programs",
            "Ensure adequate water supply and shade",
            "Mid-summer pasture rotation",
            "Pregnancy checking for spring-bred cows",
            "Monitor body condition scores",
        ],
        "crops": [
            "Post-emergence herbicide applications",
            "Fungicide applications at key growth stages (e.g., R3 soybeans, VT corn)",
            "Tissue testing and in-season nitrogen management",
            "Scout for disease pressure (rust, blight, mold)",
            "Monitor pollination (corn) and pod set (soybeans)",
            "Begin harvest planning and logistics",
        ],
    },
    "fall": {
        "months": [9, 10, 11],
        "label": "Fall (September–November)",
        "general": [
            "Harvest season — monitor grain moisture and quality",
            "Grain storage management and bin prep",
            "Post-harvest marketing decisions — storage vs. sale",
            "Fall cover crop planting",
            "Year-end tax planning — evaluate equipment purchases",
            "Crop insurance claim deadlines if applicable",
            "Review cash flow and operating loan positions",
        ],
        "livestock": [
            "Weaning calves — preconditioning programs",
            "Fall pregnancy checking and culling decisions",
            "Backgrounding and stocker programs",
            "Hay and feed inventory assessment for winter",
            "Fall vaccinations and booster shots",
            "Marketing decisions for feeder calves",
        ],
        "crops": [
            "Combine maintenance and harvest logistics",
            "Soil sampling for next season",
            "Apply fall fertilizer (P & K) based on soil tests",
            "Plan cover crop mixes and seeding rates",
            "Evaluate variety/hybrid performance for next year",
            "Assess tile drainage and field improvement needs",
        ],
    },
    "winter": {
        "months": [12, 1, 2],
        "label": "Winter (December–February)",
        "general": [
            "Financial planning and annual budget preparation",
            "Tax filing and estimated payment deadlines",
            "Equipment maintenance, repair, and replacement planning",
            "Seed and input ordering for next season",
            "Business planning and goal setting",
            "Attend farm shows and educational events",
            "Review insurance coverage and crop insurance options",
        ],
        "livestock": [
            "Winter feeding programs — monitor hay quality and supply",
            "Calving prep for spring-calving herds",
            "Facility maintenance and bedding management",
            "Bull selection and breeding decisions for next year",
            "Nutritional management for gestating cows",
            "Review herd health protocols with veterinarian",
        ],
        "crops": [
            "Review previous season yield data and financials",
            "Plan crop rotations for the coming year",
            "Finalize seed and chemical orders (early-order discounts)",
            "Attend agronomy and crop production workshops",
            "Develop nutrient management plans",
            "Evaluate precision ag technology and data from last season",
        ],
    },
}


DEADLINES = [
    {
        "month": 1,
        "day": 15,
        "title": "Estimated Tax Payment Due (Q4)",
        "description": "Federal estimated tax payment for Q4 of previous year due to IRS.",
        "category": "tax",
        "business_types": None,
    },
    {
        "month": 1,
        "day": 31,
        "title": "W-2 and 1099 Filing Deadline",
        "description": "Deadline to provide W-2s to employees and 1099s to contractors.",
        "category": "tax",
        "business_types": None,
    },
    {
        "month": 2,
        "day": 28,
        "title": "ARC/PLC Enrollment Deadline (typical)",
        "description": "USDA ARC/PLC program enrollment deadline — contact local FSA office for exact date.",
        "category": "usda_program",
        "business_types": ["crop_farming", "diversified"],
    },
    {
        "month": 3,
        "day": 1,
        "title": "Farmer Tax Filing (if no estimated payments)",
        "description": "Farmers who did not make estimated tax payments must file by March 1.",
        "category": "tax",
        "business_types": None,
    },
    {
        "month": 3,
        "day": 15,
        "title": "Spring Crop Insurance Sales Closing",
        "description": "Federal crop insurance sales closing date for spring-planted crops in many states. Verify with your agent.",
        "category": "insurance",
        "business_types": ["crop_farming", "diversified"],
    },
    {
        "month": 4,
        "day": 15,
        "title": "Federal Tax Filing Deadline / Q1 Estimated Payment",
        "description": "Federal income tax return due. Also Q1 estimated tax payment deadline.",
        "category": "tax",
        "business_types": None,
    },
    {
        "month": 5,
        "day": 31,
        "title": "EQIP Application Ranking (typical)",
        "description": "NRCS EQIP applications are typically ranked in spring — check with local NRCS office.",
        "category": "usda_program",
        "business_types": None,
    },
    {
        "month": 6,
        "day": 15,
        "title": "Estimated Tax Payment Due (Q2)",
        "description": "Federal estimated tax payment for Q2.",
        "category": "tax",
        "business_types": None,
    },
    {
        "month": 7,
        "day": 15,
        "title": "Crop Insurance Acreage Reporting",
        "description": "Crop insurance acreage reporting deadline for spring-planted crops. Report planted acres to your agent.",
        "category": "insurance",
        "business_types": ["crop_farming", "diversified"],
    },
    {
        "month": 8,
        "day": 1,
        "title": "CRP General Signup (typical window)",
        "description": "USDA Conservation Reserve Program (CRP) general signup typically opens mid-year. Check FSA for current dates.",
        "category": "usda_program",
        "business_types": ["crop_farming", "diversified"],
    },
    {
        "month": 9,
        "day": 15,
        "title": "Estimated Tax Payment Due (Q3)",
        "description": "Federal estimated tax payment for Q3.",
        "category": "tax",
        "business_types": None,
    },
    {
        "month": 9,
        "day": 30,
        "title": "Fall Crop Insurance Sales Closing",
        "description": "Federal crop insurance sales closing date for fall-planted crops (winter wheat, etc.) in many states.",
        "category": "insurance",
        "business_types": ["crop_farming", "diversified"],
    },
    {
        "month": 10,
        "day": 15,
        "title": "Extended Tax Filing Deadline",
        "description": "Deadline for those who filed a tax extension in April.",
        "category": "tax",
        "business_types": None,
    },
    {
        "month": 11,
        "day": 15,
        "title": "Crop Insurance Production Reporting",
        "description": "Year-end crop insurance production reporting deadline for many crops.",
        "category": "insurance",
        "business_types": ["crop_farming", "diversified"],
    },
    {
        "month": 12,
        "day": 31,
        "title": "Year-End Tax Planning Deadline",
        "description": "Last day for equipment purchases, prepaid expenses, and other tax strategies for the current tax year.",
        "category": "tax",
        "business_types": None,
    },
    {
        "month": 12,
        "day": 31,
        "title": "ARC/PLC Base Acre Reallocation Deadline (if applicable)",
        "description": "Deadline to reallocate base acres under the Farm Bill — check FSA for current program year details.",
        "category": "usda_program",
        "business_types": ["crop_farming", "diversified"],
    },
]

GROWING_SEASON_ADJUSTMENTS = {
    "early": {
        "description": "Early growing season (Southern states)",
        "planting_shift": "Planting typically begins 2–4 weeks earlier than national averages.",
        "harvest_shift": "Harvest often begins in August/September.",
        "notes": "Double-cropping opportunities (e.g., winter wheat followed by soybeans). Longer pest pressure window.",
    },
    "standard": {
        "description": "Standard growing season (Midwest/Mid-Atlantic)",
        "planting_shift": "Standard planting windows apply (April–May for most row crops).",
        "harvest_shift": "Harvest typically September–November.",
        "notes": "Follow standard USDA crop calendar for your region.",
    },
    "late": {
        "description": "Late/short growing season (Northern states)",
        "planting_shift": "Planting may be delayed until May or early June depending on conditions.",
        "harvest_shift": "Harvest often extends into late October–November; frost risk is a key factor.",
        "notes": "Select shorter-season varieties. Monitor frost dates closely. Consider storage to avoid harvest-time basis pressure.",
    },
}


MONTH_TO_SEASON = {}
for season, data in SEASONAL_ACTIVITIES.items():
    for m in data["months"]:
        MONTH_TO_SEASON[m] = season


def _classify_growing_season(growing_season_start: Optional[str]) -> str:
    if not growing_season_start:
        return "standard"
    start_lower = growing_season_start.lower().strip()
    early_months = ["january", "february", "march"]
    late_months = ["may", "june", "july"]
    for m in early_months:
        if m in start_lower:
            return "early"
    for m in late_months:
        if m in start_lower:
            return "late"
    return "standard"


def _get_upcoming_deadlines(current_date: date, business_type: Optional[str] = None, window_days: int = 60):
    upcoming = []
    for dl in DEADLINES:
        try:
            dl_date = date(current_date.year, dl["month"], dl["day"])
        except ValueError:
            dl_date = date(current_date.year, dl["month"], 28)

        if dl_date < current_date:
            try:
                dl_date = date(current_date.year + 1, dl["month"], dl["day"])
            except ValueError:
                dl_date = date(current_date.year + 1, dl["month"], 28)

        days_until = (dl_date - current_date).days
        if 0 <= days_until <= window_days:
            if dl["business_types"] is None or (business_type and business_type in dl["business_types"]):
                upcoming.append({
                    "date": dl_date.strftime("%B %d"),
                    "days_until": days_until,
                    "title": dl["title"],
                    "description": dl["description"],
                    "category": dl["category"],
                })

    upcoming.sort(key=lambda x: x["days_until"])
    return upcoming


def get_seasonal_context(
    state_name: Optional[str] = None,
    business_type: Optional[str] = None,
    current_date: Optional[date] = None,
    growing_season_start: Optional[str] = None,
) -> str:
    if current_date is None:
        current_date = date.today()

    month = current_date.month
    season_key = MONTH_TO_SEASON[month]
    season_data = SEASONAL_ACTIVITIES[season_key]

    sections = []
    sections.append(f"Current Date: {current_date.strftime('%B %d, %Y')}")
    sections.append(f"Current Season: {season_data['label']}")

    gs_class = _classify_growing_season(growing_season_start)
    gs_info = GROWING_SEASON_ADJUSTMENTS[gs_class]
    if state_name:
        sections.append(f"Growing Season ({state_name}): {gs_info['description']}")
        sections.append(f"  {gs_info['planting_shift']}")
        sections.append(f"  {gs_info['harvest_shift']}")
        sections.append(f"  Note: {gs_info['notes']}")

    sections.append("")
    sections.append("KEY ACTIVITIES FOR THIS SEASON:")
    for item in season_data["general"]:
        sections.append(f"  • {item}")

    bt_lower = (business_type or "").lower()
    if any(kw in bt_lower for kw in ["livestock", "cattle", "ranch", "dairy", "poultry", "hog", "pig", "sheep"]):
        sections.append("")
        sections.append("LIVESTOCK-SPECIFIC ACTIVITIES:")
        for item in season_data["livestock"]:
            sections.append(f"  • {item}")
    if any(kw in bt_lower for kw in ["crop", "grain", "farm", "diversified", "row crop", "cotton", "rice", "corn", "soybean"]):
        sections.append("")
        sections.append("CROP-SPECIFIC ACTIVITIES:")
        for item in season_data["crops"]:
            sections.append(f"  • {item}")
    if not bt_lower or bt_lower in ["other", "general", ""]:
        sections.append("")
        sections.append("LIVESTOCK-SPECIFIC ACTIVITIES:")
        for item in season_data["livestock"]:
            sections.append(f"  • {item}")
        sections.append("")
        sections.append("CROP-SPECIFIC ACTIVITIES:")
        for item in season_data["crops"]:
            sections.append(f"  • {item}")

    upcoming = _get_upcoming_deadlines(current_date, business_type)
    if upcoming:
        sections.append("")
        sections.append("UPCOMING DEADLINES (next 60 days):")
        for dl in upcoming:
            urgency = ""
            if dl["days_until"] <= 7:
                urgency = " ⚠️ URGENT"
            elif dl["days_until"] <= 14:
                urgency = " ⏰ SOON"
            sections.append(
                f"  • {dl['date']} ({dl['days_until']} days away{urgency}): {dl['title']}"
            )
            sections.append(f"    {dl['description']}")

    return "\n".join(sections)
