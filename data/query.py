import os
import logging
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

_pool = None


def _get_pool():
    global _pool
    if _pool is None or _pool.closed:
        _pool = pool.ThreadedConnectionPool(1, 10, os.environ["DATABASE_URL"])
    return _pool


def _query(sql, params=None):
    p = _get_pool()
    conn = p.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    except Exception as e:
        logger.warning(f"Database query failed: {e}")
        conn.reset()
        return []
    finally:
        p.putconn(conn)


def get_state_profile(state_name):
    rows = _query("SELECT * FROM state_ag_profiles WHERE state_name = %s", (state_name,))
    if not rows:
        return None
    row = rows[0]
    return (
        f"STATE AGRICULTURAL PROFILE — {row['state_name']} ({row['abbreviation']})\n"
        f"USDA Region: {row['usda_region']}\n"
        f"Climate Zones: {row['climate_zones']}\n"
        f"Growing Season: {row['growing_season_start']} to {row['growing_season_end']}\n"
        f"Annual Precipitation: {row['annual_precipitation_inches']} inches\n"
        f"Top Commodities: {row['top_commodities']}\n"
        f"Total Farms: {row['total_farms']:,}\n"
        f"Average Farm Size: {row['avg_farm_size_acres']} acres\n"
        f"Total Ag Revenue: {row['total_ag_revenue']}\n"
        f"Ag % of GDP: {row['ag_percentage_of_gdp']}\n"
        f"Primary Soil Types: {row['primary_soil_types']}\n"
        f"Hardiness Zones: {row['hardiness_zones']}"
    )


def get_state_regulations(state_name):
    rows = _query("SELECT * FROM state_ag_regulations WHERE state_name = %s", (state_name,))
    if not rows:
        return None
    row = rows[0]
    return (
        f"STATE REGULATIONS — {row['state_name']}\n"
        f"Water Rights: {row['water_rights_doctrine']}\n"
        f"Right to Farm: {row['right_to_farm_law']}\n"
        f"Ag Tax Exemptions: {row['ag_exemption_details']}\n"
        f"Labor Regulations: {row['labor_regulations']}\n"
        f"Environmental Regulations: {row['environmental_regulations']}\n"
        f"Organic Certification: {row['organic_certification_contacts']}\n"
        f"State Ag Department: {row['state_ag_department_name']} — {row['state_ag_department_url']}"
    )


def get_state_programs(state_name):
    rows = _query(
        "SELECT * FROM state_financial_programs WHERE state_name = %s ORDER BY program_type, program_name",
        (state_name,)
    )
    if not rows:
        return None
    lines = [f"FINANCIAL PROGRAMS — {state_name}"]
    for row in rows:
        lines.append(
            f"• {row['program_name']} ({row['program_type']})\n"
            f"  Agency: {row['administering_agency']}\n"
            f"  Eligibility: {row['eligibility_summary']}\n"
            f"  Max Amount: {row['max_amount']}\n"
            f"  Description: {row['description']}\n"
            f"  Website: {row['website_url']}"
        )
    return "\n".join(lines)


def get_state_commodities(state_name):
    rows = _query(
        "SELECT * FROM state_commodities WHERE state_name = %s ORDER BY state_rank_national",
        (state_name,)
    )
    if not rows:
        return None
    lines = [f"TOP COMMODITIES — {state_name}"]
    for row in rows:
        trend_str = f" (trend: {row['trend']})" if row['trend'] else ""
        lines.append(
            f"• {row['commodity_name']} [{row['commodity_category']}] — "
            f"National Rank #{row['state_rank_national']}, "
            f"Value: {row['annual_production_value']}, "
            f"Price: {row['avg_price_per_unit']}, "
            f"Scale: {row['acreage_or_head_count']}{trend_str}"
        )
    return "\n".join(lines)


def get_business_benchmarks(business_type):
    rows = _query("SELECT * FROM business_type_benchmarks WHERE business_type = %s", (business_type,))
    if not rows:
        return None
    row = rows[0]
    return (
        f"INDUSTRY BENCHMARKS — {row['business_type']}\n"
        f"Typical Startup Cost: {row['avg_startup_cost_range']}\n"
        f"Revenue Range: {row['typical_revenue_range']}\n"
        f"Average Profit Margin: {row['avg_profit_margin']}\n"
        f"Common Challenges: {row['common_challenges']}\n"
        f"Key Success Factors: {row['key_success_factors']}\n"
        f"Typical Financing: {row['typical_financing_sources']}\n"
        f"Common Insurance: {row['common_insurance_types']}\n"
        f"Regulatory Focus: {row['regulatory_focus_areas']}\n"
        f"Growth Outlook: {row['growth_outlook']}"
    )


def get_extension_info(state_name):
    rows = _query("SELECT * FROM extension_services WHERE state_name = %s", (state_name,))
    if not rows:
        return None
    row = rows[0]
    return (
        f"EXTENSION SERVICE — {row['state_name']}\n"
        f"University: {row['university_name']}\n"
        f"Website: {row['extension_website']}\n"
        f"Phone: {row['main_phone']}\n"
        f"Specialty Programs: {row['specialty_programs']}\n"
        f"Focus Areas: {row['focus_areas']}"
    )


def get_advisor_context(state_name, business_type):
    sections = []

    if state_name:
        profile = get_state_profile(state_name)
        if profile:
            sections.append(profile)

        commodities = get_state_commodities(state_name)
        if commodities:
            sections.append(commodities)

        regulations = get_state_regulations(state_name)
        if regulations:
            sections.append(regulations)

        programs = get_state_programs(state_name)
        if programs:
            sections.append(programs)

        extension = get_extension_info(state_name)
        if extension:
            sections.append(extension)

    if business_type:
        benchmarks = get_business_benchmarks(business_type)
        if benchmarks:
            sections.append(benchmarks)

    if not sections:
        return None

    return "\n\n".join(sections)
