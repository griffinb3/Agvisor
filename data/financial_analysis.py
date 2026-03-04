import csv
import io
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

COLUMN_ALIASES = {
    'revenue': ['revenue', 'total_revenue', 'total revenue', 'sales', 'total_sales', 'total sales', 'gross_revenue', 'gross revenue', 'income', 'total_income'],
    'expenses': ['expenses', 'total_expenses', 'total expenses', 'operating_expenses', 'operating expenses', 'total_costs', 'total costs', 'cost', 'costs'],
    'net_income': ['net_income', 'net income', 'net_profit', 'net profit', 'profit', 'net_earnings', 'net earnings', 'bottom_line'],
    'gross_profit': ['gross_profit', 'gross profit', 'gross_margin', 'gross margin', 'gross_income', 'gross income'],
    'operating_income': ['operating_income', 'operating income', 'operating_profit', 'operating profit', 'ebit'],
    'ebitda': ['ebitda'],
    'cogs': ['cogs', 'cost_of_goods_sold', 'cost of goods sold', 'cost_of_sales', 'cost of sales', 'direct_costs', 'direct costs'],
    'assets': ['assets', 'total_assets', 'total assets'],
    'current_assets': ['current_assets', 'current assets'],
    'liabilities': ['liabilities', 'total_liabilities', 'total liabilities', 'total_debt', 'total debt'],
    'current_liabilities': ['current_liabilities', 'current liabilities'],
    'equity': ['equity', 'total_equity', 'total equity', 'owners_equity', 'owners equity', 'stockholders_equity', 'net_worth', 'net worth'],
    'debt': ['debt', 'long_term_debt', 'long term debt', 'total_debt', 'total debt'],
    'depreciation': ['depreciation', 'depreciation_amortization', 'depreciation and amortization', 'd_a', 'da'],
    'interest': ['interest', 'interest_expense', 'interest expense'],
    'taxes': ['taxes', 'tax', 'income_tax', 'income tax', 'tax_expense'],
    'year': ['year', 'fiscal_year', 'fiscal year', 'date', 'period', 'fy'],
}

SIMILARITY_THRESHOLD = 0.75


def _fuzzy_match_column(col_name, aliases):
    col_lower = col_name.lower().strip()
    for alias in aliases:
        if col_lower == alias:
            return True
        if SequenceMatcher(None, col_lower, alias).ratio() >= SIMILARITY_THRESHOLD:
            return True
    return False


def _map_columns(headers):
    mapping = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for header in headers:
            if _fuzzy_match_column(header, aliases):
                mapping[canonical] = header
                break
    return mapping


def _safe_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        cleaned = str(value).replace(',', '').replace('$', '').replace('%', '').strip()
        if not cleaned or cleaned == '-' or cleaned.lower() in ('n/a', 'na', 'none', 'null', ''):
            return None
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _get_val(row, col_mapping, key):
    if key not in col_mapping:
        return None
    return _safe_float(row.get(col_mapping[key]))


def _fmt_pct(value):
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def _fmt_ratio(value):
    if value is None:
        return "N/A"
    return f"{value:.2f}"


def _fmt_currency(value):
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000:
        return f"${value/1_000_000:,.1f}M"
    if abs(value) >= 1_000:
        return f"${value/1_000:,.1f}K"
    return f"${value:,.0f}"


def _compute_row_metrics(row, col_mapping):
    metrics = {}

    revenue = _get_val(row, col_mapping, 'revenue')
    expenses = _get_val(row, col_mapping, 'expenses')
    net_income = _get_val(row, col_mapping, 'net_income')
    gross_profit = _get_val(row, col_mapping, 'gross_profit')
    operating_income = _get_val(row, col_mapping, 'operating_income')
    ebitda = _get_val(row, col_mapping, 'ebitda')
    cogs = _get_val(row, col_mapping, 'cogs')
    assets = _get_val(row, col_mapping, 'assets')
    current_assets = _get_val(row, col_mapping, 'current_assets')
    liabilities = _get_val(row, col_mapping, 'liabilities')
    current_liabilities = _get_val(row, col_mapping, 'current_liabilities')
    equity = _get_val(row, col_mapping, 'equity')
    debt = _get_val(row, col_mapping, 'debt')
    depreciation = _get_val(row, col_mapping, 'depreciation')
    interest = _get_val(row, col_mapping, 'interest')
    taxes = _get_val(row, col_mapping, 'taxes')

    if net_income is None and revenue is not None and expenses is not None:
        net_income = revenue - expenses

    if gross_profit is None and revenue is not None and cogs is not None:
        gross_profit = revenue - cogs

    if operating_income is None and gross_profit is not None and expenses is not None and cogs is not None:
        operating_income = gross_profit - (expenses - cogs)
    elif operating_income is None and revenue is not None and expenses is not None:
        operating_income = revenue - expenses

    if revenue and revenue != 0:
        if gross_profit is not None:
            metrics['gross_margin'] = (gross_profit / revenue) * 100
        if net_income is not None:
            metrics['net_margin'] = (net_income / revenue) * 100
        if operating_income is not None:
            metrics['operating_margin'] = (operating_income / revenue) * 100
        if ebitda is not None:
            metrics['ebitda_margin'] = (ebitda / revenue) * 100
        elif operating_income is not None and depreciation is not None:
            computed_ebitda = operating_income + depreciation
            metrics['ebitda_margin'] = (computed_ebitda / revenue) * 100
        if expenses is not None:
            metrics['operating_expense_ratio'] = (expenses / revenue) * 100

    if current_assets is not None and current_liabilities is not None and current_liabilities != 0:
        metrics['current_ratio'] = current_assets / current_liabilities

    if current_assets is not None and current_liabilities is not None:
        metrics['working_capital'] = current_assets - current_liabilities

    if equity is not None and equity != 0:
        if debt is not None:
            metrics['debt_to_equity'] = debt / equity
        elif liabilities is not None:
            metrics['debt_to_equity'] = liabilities / equity

    if assets is not None and assets != 0:
        if debt is not None:
            metrics['debt_to_asset'] = debt / assets
        elif liabilities is not None:
            metrics['debt_to_asset'] = liabilities / assets
        if equity is not None:
            metrics['equity_to_asset'] = equity / assets
        if revenue is not None:
            metrics['asset_turnover'] = revenue / assets

    metrics['_revenue'] = revenue
    metrics['_expenses'] = expenses
    metrics['_net_income'] = net_income

    return metrics


def _compute_trends(yearly_metrics):
    if len(yearly_metrics) < 2:
        return {}

    trends = {}
    for key_label, internal_key in [('revenue', '_revenue'), ('expenses', '_expenses'), ('net_income', '_net_income')]:
        values = [(y, m.get(internal_key)) for y, m in yearly_metrics]
        values = [(y, v) for y, v in values if v is not None]
        if len(values) >= 2:
            growth_rates = []
            for i in range(1, len(values)):
                prev_val = values[i-1][1]
                curr_val = values[i][1]
                if prev_val and prev_val != 0:
                    rate = ((curr_val - prev_val) / abs(prev_val)) * 100
                    growth_rates.append((values[i][0], rate))
            if growth_rates:
                trends[key_label] = growth_rates

    return trends


def analyze_financial_data(rows, headers=None):
    if not rows:
        return None

    if headers is None and rows:
        headers = list(rows[0].keys())

    col_mapping = _map_columns(headers)

    if not col_mapping:
        return None

    has_financial = any(k in col_mapping for k in [
        'revenue', 'expenses', 'net_income', 'assets', 'liabilities', 'equity',
        'gross_profit', 'operating_income', 'cogs'
    ])
    if not has_financial:
        return None

    has_year = 'year' in col_mapping
    yearly_metrics = []

    for row in rows:
        year_val = row.get(col_mapping.get('year', ''), '') if has_year else None
        metrics = _compute_row_metrics(row, col_mapping)
        if metrics:
            yearly_metrics.append((str(year_val) if year_val else f"Row {len(yearly_metrics)+1}", metrics))

    if not yearly_metrics:
        return None

    sections = []
    sections.append("=" * 50)
    sections.append("COMPUTED FINANCIAL ANALYSIS")
    sections.append("=" * 50)

    profitability_keys = ['gross_margin', 'net_margin', 'operating_margin', 'ebitda_margin']
    liquidity_keys = ['current_ratio', 'working_capital']
    solvency_keys = ['debt_to_equity', 'debt_to_asset', 'equity_to_asset']
    efficiency_keys = ['asset_turnover', 'operating_expense_ratio']

    latest = yearly_metrics[-1][1]
    latest_label = yearly_metrics[-1][0]

    prof_items = []
    for key in profitability_keys:
        if key in latest:
            label = key.replace('_', ' ').title()
            prof_items.append(f"  {label}: {_fmt_pct(latest[key])}")
    if prof_items:
        sections.append(f"\nPROFITABILITY METRICS (Period: {latest_label}):")
        sections.extend(prof_items)

    liq_items = []
    for key in liquidity_keys:
        if key in latest:
            label = key.replace('_', ' ').title()
            if key == 'working_capital':
                liq_items.append(f"  {label}: {_fmt_currency(latest[key])}")
            else:
                liq_items.append(f"  {label}: {_fmt_ratio(latest[key])}")
    if liq_items:
        sections.append(f"\nLIQUIDITY METRICS (Period: {latest_label}):")
        sections.extend(liq_items)

    solv_items = []
    for key in solvency_keys:
        if key in latest:
            label = key.replace('_', ' ').title()
            solv_items.append(f"  {label}: {_fmt_ratio(latest[key])}")
    if solv_items:
        sections.append(f"\nSOLVENCY METRICS (Period: {latest_label}):")
        sections.extend(solv_items)

    eff_items = []
    for key in efficiency_keys:
        if key in latest:
            label = key.replace('_', ' ').title()
            if key == 'operating_expense_ratio':
                eff_items.append(f"  {label}: {_fmt_pct(latest[key])}")
            else:
                eff_items.append(f"  {label}: {_fmt_ratio(latest[key])}")
    if eff_items:
        sections.append(f"\nEFFICIENCY METRICS (Period: {latest_label}):")
        sections.extend(eff_items)

    if len(yearly_metrics) >= 2:
        trends = _compute_trends(yearly_metrics)
        if trends:
            sections.append("\nYEAR-OVER-YEAR TRENDS:")
            for metric_name, rates in trends.items():
                label = metric_name.replace('_', ' ').title()
                trend_parts = []
                for year, rate in rates:
                    direction = "↑" if rate > 0 else "↓" if rate < 0 else "→"
                    trend_parts.append(f"{year}: {direction} {abs(rate):.1f}%")
                sections.append(f"  {label}: {', '.join(trend_parts)}")

                if len(rates) >= 2:
                    avg_rate = sum(r for _, r in rates) / len(rates)
                    sections.append(f"    Average Annual Growth: {_fmt_pct(avg_rate)}")

    if len(yearly_metrics) > 1:
        sections.append(f"\nMULTI-PERIOD SUMMARY ({len(yearly_metrics)} periods analyzed):")
        for metric_name, internal_key in [('Revenue', '_revenue'), ('Expenses', '_expenses'), ('Net Income', '_net_income')]:
            values = [m.get(internal_key) for _, m in yearly_metrics if m.get(internal_key) is not None]
            if values:
                sections.append(f"  {metric_name}: {_fmt_currency(values[0])} → {_fmt_currency(values[-1])}")

    sections.append("")
    return "\n".join(sections)


def analyze_csv_string(csv_string):
    try:
        reader = csv.DictReader(io.StringIO(csv_string))
        rows = list(reader)
        headers = reader.fieldnames
        if not rows or not headers:
            return None
        return analyze_financial_data(rows, headers)
    except Exception as e:
        logger.warning(f"Failed to analyze CSV data: {e}")
        return None


def analyze_records(headers, preview_rows):
    if not headers or not preview_rows:
        return None
    try:
        return analyze_financial_data(preview_rows, headers)
    except Exception as e:
        logger.warning(f"Failed to analyze financial records: {e}")
        return None
