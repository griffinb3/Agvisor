import csv
import io
import re
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

CHART_DIRECTIVE_RE = re.compile(r'\[CHART:(\w+):([^\]]+)\]', re.IGNORECASE)
VALID_INLINE_CHART_TYPES = {'line', 'bar', 'doughnut'}
INLINE_CHART_CANONICAL_COLS = {
    'revenue', 'expenses', 'net_income', 'gross_profit', 'cogs',
    'assets', 'liabilities', 'equity', 'debt',
    'current_assets', 'current_liabilities', 'operating_income', 'ebitda',
}

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


def _linear_regression(values):
    n = len(values)
    if n < 2:
        return None, None
    xs = list(range(n))
    sx = sum(xs)
    sy = sum(values)
    sxy = sum(x * y for x, y in zip(xs, values))
    sxx = sum(x * x for x in xs)
    denom = n * sxx - sx * sx
    if denom == 0:
        return None, None
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return slope, intercept


def _predict_values(values, periods_forward=2):
    clean = [v for v in values if v is not None]
    if len(clean) < 2:
        return []
    slope, intercept = _linear_regression(clean)
    if slope is None:
        return []
    n = len(clean)
    return [round(slope * (n + i) + intercept, 2) for i in range(periods_forward)]


_LABEL_HINTS = {'year', 'date', 'period', 'month', 'quarter', 'fy', 'fiscal', 'time', 'week', 'season', 'crop', 'variety', 'type', 'category', 'name', 'item', 'region', 'location', 'state', 'product'}


def _get_generic_chart_data(rows, headers):
    """Fallback: build chart data from ANY numeric columns in the file."""
    if not rows or not headers:
        return {'has_data': False}

    # Find label column: prefer columns whose name hints at a period/category
    label_col = None
    for h in headers:
        if any(hint in h.lower() for hint in _LABEL_HINTS):
            label_col = h
            break
    if label_col is None:
        label_col = headers[0]

    # Collect numeric columns (excluding the label column)
    numeric_cols = []
    for h in headers:
        if h == label_col:
            continue
        vals = [_safe_float(row.get(h)) for row in rows[:20]]
        non_null = [v for v in vals if v is not None]
        if len(non_null) >= max(1, len(rows[:20]) // 2):
            numeric_cols.append(h)
    numeric_cols = numeric_cols[:8]  # cap at 8 series

    if not numeric_cols:
        return {'has_data': False}

    labels = []
    for i, row in enumerate(rows[:20]):
        lv = str(row.get(label_col, '')).strip()
        labels.append(lv if lv and lv.lower() not in ('none', 'null', '') else f"Row {i + 1}")

    datasets = {}
    for col in numeric_cols:
        datasets[col] = [_safe_float(row.get(col)) for row in rows[:20]]

    n_periods = len(labels)

    # Predictions for numeric series with >= 2 data points
    prediction_labels = []
    predictions = {}
    if n_periods >= 2:
        try:
            years = [int(lbl) for lbl in labels]
            last = max(years)
            prediction_labels = [f"{last + 1} (proj.)", f"{last + 2} (proj.)"]
        except (ValueError, TypeError):
            prediction_labels = ["Next Period (proj.)", "Period +2 (proj.)"]
        for col in numeric_cols:
            preds = _predict_values(datasets[col], 2)
            if preds:
                predictions[col] = preds

    # Recommended chart type
    if n_periods >= 3:
        recommended = 'line'
    elif n_periods == 2:
        recommended = 'bar'
    elif len(numeric_cols) > 1:
        recommended = 'doughnut'
    else:
        recommended = 'bar'

    # Composition from last row
    composition = {}
    last_row = rows[n_periods - 1] if n_periods > 0 else {}
    for col in numeric_cols:
        v = _safe_float(last_row.get(col))
        if v is not None:
            composition[col] = v

    # Scatter: first two numeric cols as x/y
    scatter_data = []
    if len(numeric_cols) >= 2:
        for i in range(n_periods):
            xv = datasets[numeric_cols[0]][i]
            yv = datasets[numeric_cols[1]][i]
            if xv is not None and yv is not None:
                scatter_data.append({'x': xv, 'y': yv, 'label': labels[i]})

    return {
        'has_data': True,
        'labels': labels,
        'prediction_labels': prediction_labels,
        'datasets': datasets,
        'margins': {},
        'ratios': {},
        'predictions': predictions,
        'recommended_chart_type': recommended,
        'composition': composition,
        'scatter_data': scatter_data,
        'generic': True,
        'x_label': numeric_cols[0] if len(numeric_cols) >= 1 else '',
        'y_label': numeric_cols[1] if len(numeric_cols) >= 2 else '',
    }


def get_chart_data(rows, headers):
    if not rows or not headers:
        return {'has_data': False}

    col_mapping = _map_columns(headers)
    if not col_mapping:
        return _get_generic_chart_data(rows, headers)

    has_financial = any(k in col_mapping for k in [
        'revenue', 'expenses', 'net_income', 'assets', 'liabilities', 'equity',
        'gross_profit', 'operating_income', 'cogs'
    ])
    if not has_financial:
        return _get_generic_chart_data(rows, headers)

    has_year = 'year' in col_mapping

    # Deduplicate by year and sort chronologically when year data is present
    if has_year:
        year_col = col_mapping['year']
        seen_years = {}
        for row in rows:
            y = str(row.get(year_col, '')).strip()
            if y and y.lower() not in ('none', 'null', ''):
                seen_years[y] = row  # later rows overwrite earlier ones (keep last per year)
        try:
            rows = [v for _, v in sorted(seen_years.items(), key=lambda x: int(x[0]))]
        except (ValueError, TypeError):
            rows = list(seen_years.values())

    labels = []
    raw = {'revenue': [], 'expenses': [], 'net_income': [], 'gross_profit': []}
    margins = {'gross_margin': [], 'net_margin': [], 'operating_margin': []}
    ratios = {'current_ratio': [], 'debt_to_equity': [], 'debt_to_asset': []}

    for i, row in enumerate(rows[:20]):
        year_val = row.get(col_mapping.get('year', ''), '') if has_year else ''
        label = str(year_val).strip() if year_val and str(year_val).strip() else f"Period {i + 1}"
        labels.append(label)

        m = _compute_row_metrics(row, col_mapping)
        raw['revenue'].append(m.get('_revenue'))
        raw['expenses'].append(m.get('_expenses'))
        raw['net_income'].append(m.get('_net_income'))
        gp = _get_val(row, col_mapping, 'gross_profit')
        if gp is None and m.get('_revenue') is not None and _get_val(row, col_mapping, 'cogs') is not None:
            gp = m['_revenue'] - _get_val(row, col_mapping, 'cogs')
        raw['gross_profit'].append(gp)

        margins['gross_margin'].append(m.get('gross_margin'))
        margins['net_margin'].append(m.get('net_margin'))
        margins['operating_margin'].append(m.get('operating_margin'))

        ratios['current_ratio'].append(m.get('current_ratio'))
        ratios['debt_to_equity'].append(m.get('debt_to_equity'))
        ratios['debt_to_asset'].append(m.get('debt_to_asset'))

    def _has_values(lst):
        return any(v is not None for v in lst)

    datasets = {k: v for k, v in raw.items() if _has_values(v)}
    margins = {k: v for k, v in margins.items() if _has_values(v)}
    ratios = {k: v for k, v in ratios.items() if _has_values(v)}

    prediction_labels = []
    predictions = {}
    if len(labels) >= 2:
        try:
            years = [int(lbl) for lbl in labels]
            last_year = max(years)
            prediction_labels = [f"{last_year + 1} (proj.)", f"{last_year + 2} (proj.)"]
        except (ValueError, TypeError):
            prediction_labels = ["Next Period (proj.)", "Period +2 (proj.)"]

        for key in ['revenue', 'expenses', 'net_income']:
            if key in datasets:
                preds = _predict_values(datasets[key], 2)
                if preds:
                    predictions[key] = preds

    if not labels:
        return {'has_data': False}

    # Recommended chart type selection
    n_periods = len(labels)
    has_time_series = any(k in datasets for k in ['revenue', 'expenses', 'net_income'])
    if has_time_series and n_periods >= 3:
        recommended_chart_type = 'line'
    elif has_time_series and n_periods == 2:
        recommended_chart_type = 'bar'
    elif has_time_series and n_periods == 1:
        recommended_chart_type = 'doughnut'
    elif margins:
        recommended_chart_type = 'scatter'
    else:
        recommended_chart_type = 'bar'

    # Doughnut: latest period composition
    latest = rows[n_periods - 1] if n_periods > 0 else {}
    composition = {}
    for key in ['revenue', 'expenses', 'net_income', 'gross_profit', 'cogs']:
        if key in col_mapping:
            val = _get_val(latest, col_mapping, key)
            if val is not None:
                composition[key] = val

    # Scatter: revenue vs net_margin pairs
    scatter_data = []
    for i in range(n_periods):
        rev = datasets.get('revenue', [None] * n_periods)[i]
        nm = margins.get('net_margin', [None] * n_periods)[i]
        if rev is not None and nm is not None:
            scatter_data.append({'x': rev, 'y': nm, 'label': labels[i]})

    return {
        'has_data': True,
        'labels': labels,
        'prediction_labels': prediction_labels,
        'datasets': datasets,
        'margins': margins,
        'ratios': ratios,
        'predictions': predictions,
        'recommended_chart_type': recommended_chart_type,
        'composition': composition,
        'scatter_data': scatter_data
    }


def get_forecast_chart_data(rows, headers):
    """
    Build a forecast inline chart showing historical data (solid) and projected
    data (dashed) for revenue, expenses, and net income.
    Returns None if insufficient data for projections.
    """
    base = get_chart_data(rows, headers)
    if not base or not base.get('has_data'):
        return None

    labels = base.get('labels', [])
    prediction_labels = base.get('prediction_labels', [])
    datasets = base.get('datasets', {})
    predictions = base.get('predictions', {})

    if not prediction_labels or not predictions:
        return None

    all_labels = labels + prediction_labels
    n_hist = len(labels)
    chart_datasets = {}
    chart_projections = {}

    for key in ['revenue', 'expenses', 'net_income']:
        hist_vals = datasets.get(key, [])
        proj_vals = predictions.get(key, [])
        if not hist_vals or not any(v is not None for v in hist_vals) or not proj_vals:
            continue

        hist_series = list(hist_vals) + [None] * len(proj_vals)
        last_hist = next((v for v in reversed(hist_vals) if v is not None), None)
        proj_series = [None] * n_hist + proj_vals
        if last_hist is not None:
            proj_series[n_hist - 1] = last_hist

        chart_datasets[key] = hist_series
        chart_projections[key] = proj_series

    if not chart_datasets:
        return None

    return {
        'has_data': True,
        'is_forecast': True,
        'chart_type': 'line',
        'inline': True,
        'labels': all_labels,
        'datasets': chart_datasets,
        'projections': chart_projections,
        'cutoff': n_hist - 1,
    }


def get_comparison_forecast_chart_data(rows, headers, revenue_boost_pct=15.0, cost_reduction_pct=10.0):
    """
    Build a comparison forecast chart with two projected trajectories:
      - Baseline: current trend via linear regression (no changes)
      - Enhanced: projected trajectory if board recommendations are applied
    Returns None if insufficient data.
    """
    base = get_chart_data(rows, headers)
    if not base or not base.get('has_data'):
        return None

    labels = base.get('labels', [])
    prediction_labels = base.get('prediction_labels', [])
    datasets = base.get('datasets', {})
    predictions = base.get('predictions', {})

    if not prediction_labels or not predictions:
        return None

    n_hist = len(labels)
    n_proj = len(prediction_labels)
    all_labels = labels + prediction_labels

    rev_boost = revenue_boost_pct / 100.0
    cost_cut = cost_reduction_pct / 100.0

    series = {}
    projections = {}

    for key in ['revenue', 'net_income', 'expenses']:
        hist_vals = datasets.get(key, [])
        proj_vals = predictions.get(key, [])
        if not hist_vals or not any(v is not None for v in hist_vals) or not proj_vals:
            continue

        last_hist = next((v for v in reversed(hist_vals) if v is not None), None)
        if last_hist is None:
            continue

        # Baseline: historical solid + projected dashed (current trajectory)
        base_series = list(hist_vals) + [None] * n_proj
        base_proj = [None] * n_hist + list(proj_vals)
        base_proj[n_hist - 1] = last_hist

        # Enhanced: same historical, but boosted projections
        if key == 'revenue':
            enh_proj_vals = [v * (1 + rev_boost) if v is not None else None for v in proj_vals]
        elif key == 'expenses':
            enh_proj_vals = [v * (1 - cost_cut) if v is not None else None for v in proj_vals]
        elif key == 'net_income':
            # Recompute from enhanced revenue minus enhanced expenses if available
            rev_hist = datasets.get('revenue', [])
            exp_hist = datasets.get('expenses', [])
            rev_proj = predictions.get('revenue', [])
            exp_proj = predictions.get('expenses', [])
            enh_proj_vals = []
            for i in range(n_proj):
                r = rev_proj[i] if i < len(rev_proj) and rev_proj[i] is not None else None
                e = exp_proj[i] if i < len(exp_proj) and exp_proj[i] is not None else None
                if r is not None and e is not None:
                    enh_proj_vals.append(r * (1 + rev_boost) - e * (1 - cost_cut))
                elif proj_vals[i] is not None:
                    # Fallback: boost net income directly
                    enh_proj_vals.append(proj_vals[i] * (1 + rev_boost * 0.7 + cost_cut * 0.5))
                else:
                    enh_proj_vals.append(None)
        else:
            enh_proj_vals = proj_vals

        enh_proj = [None] * n_hist + list(enh_proj_vals)
        enh_proj[n_hist - 1] = last_hist

        series[key] = base_series
        projections[f'{key}_baseline'] = base_proj
        projections[f'{key}_enhanced'] = enh_proj

    if not series:
        return None

    return {
        'has_data': True,
        'chart_type': 'comparison_forecast',
        'labels': all_labels,
        'cutoff': n_hist,
        'revenue_boost_pct': round(revenue_boost_pct, 1),
        'cost_reduction_pct': round(cost_reduction_pct, 1),
        'datasets': series,
        'projections': projections,
    }


def parse_chart_directive(text, user_profile):
    """
    Find and extract a [CHART:type:col1,col2,...] directive from advisor response text.
    Returns (clean_text, chart_data_or_None).
    chart_data will be None if no directive found or data cannot be resolved.
    """
    match = CHART_DIRECTIVE_RE.search(text)
    if not match:
        return text, None

    chart_type = match.group(1).lower()
    requested_cols = [c.strip().lower().replace(' ', '_') for c in match.group(2).split(',')]

    if chart_type not in VALID_INLINE_CHART_TYPES:
        chart_type = 'bar'

    clean_text = CHART_DIRECTIVE_RE.sub('', text).strip()

    if not user_profile:
        return clean_text, None

    business_data_files = user_profile.get('business_data_files', [])
    if not business_data_files:
        return clean_text, None

    all_headers = []
    all_rows = []
    for bdf in business_data_files:
        for h in bdf.get('headers', []):
            if h not in all_headers:
                all_headers.append(h)
        all_rows.extend(bdf.get('preview', []))

    if not all_headers or not all_rows:
        return clean_text, None

    col_mapping = _map_columns(all_headers)
    year_col = col_mapping.get('year')

    resolved = {}
    for req in requested_cols:
        if req in INLINE_CHART_CANONICAL_COLS and req in col_mapping:
            resolved[req] = col_mapping[req]
        else:
            for canonical, actual in col_mapping.items():
                if canonical == req or req in canonical or canonical in req:
                    resolved[canonical] = actual
                    break
            if req not in resolved:
                for h in all_headers:
                    if _fuzzy_match_column(h, [req, req.replace('_', ' ')]):
                        resolved[req] = h
                        break

    if not resolved:
        return clean_text, None

    labels = []
    datasets = {k: [] for k in resolved}

    for i, row in enumerate(all_rows[:20]):
        if year_col:
            lv = str(row.get(year_col, '')).strip()
            label = lv if lv and lv.lower() not in ('none', 'null', '') else f"Period {i + 1}"
        else:
            label = f"Period {i + 1}"
        labels.append(label)
        for canonical, actual_col in resolved.items():
            datasets[canonical].append(_safe_float(row.get(actual_col)))

    datasets = {k: v for k, v in datasets.items() if any(x is not None for x in v)}
    if not labels or not datasets:
        return clean_text, None

    composition = {}
    if all_rows:
        last_row = all_rows[len(labels) - 1]
        for canonical, actual_col in resolved.items():
            v = _safe_float(last_row.get(actual_col))
            if v is not None:
                composition[canonical] = v

    return clean_text, {
        'has_data': True,
        'chart_type': chart_type,
        'labels': labels,
        'datasets': datasets,
        'composition': composition,
        'inline': True,
    }
