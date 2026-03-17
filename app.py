import re
from io import BytesIO
from datetime import date

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(
    page_title="UK Total Compensation Comparison",
    page_icon="💼",
    layout="wide"
)

# ---------------------------------------------------------------------------
# 2026/27 tax constants — England, Wales & Northern Ireland
# ---------------------------------------------------------------------------
PERSONAL_ALLOWANCE = 12570
PA_TAPER_START = 100000
BASIC_RATE_LIMIT = 37700
HIGHER_RATE_THRESHOLD = 125140
NI_PRIMARY_THRESHOLD = 12570
NI_UPPER_THRESHOLD = 50270

# ---------------------------------------------------------------------------
# 2025/26 Scottish income tax thresholds (taxable income, after PA)
# 2026/27 bands not yet confirmed; 2025/26 used as best available estimate.
# ---------------------------------------------------------------------------
SCOT_STARTER_LIMIT  =   2_827   # 19%
SCOT_BASIC_LIMIT    =  14_921   # 20%
SCOT_INTER_LIMIT    =  31_092   # 21%
SCOT_HIGHER_LIMIT   =  62_430   # 42%
SCOT_ADVANCED_LIMIT = 112_570   # 45%  (48% top above this)


def _calc_scotland_income_tax(taxable_income):
    if taxable_income <= 0:
        return 0.0
    tax = 0.0
    if taxable_income > SCOT_ADVANCED_LIMIT:
        tax += (taxable_income - SCOT_ADVANCED_LIMIT) * 0.48
    if taxable_income > SCOT_HIGHER_LIMIT:
        tax += (min(taxable_income, SCOT_ADVANCED_LIMIT) - SCOT_HIGHER_LIMIT) * 0.45
    if taxable_income > SCOT_INTER_LIMIT:
        tax += (min(taxable_income, SCOT_HIGHER_LIMIT) - SCOT_INTER_LIMIT) * 0.42
    if taxable_income > SCOT_BASIC_LIMIT:
        tax += (min(taxable_income, SCOT_INTER_LIMIT) - SCOT_BASIC_LIMIT) * 0.21
    if taxable_income > SCOT_STARTER_LIMIT:
        tax += (min(taxable_income, SCOT_BASIC_LIMIT) - SCOT_STARTER_LIMIT) * 0.20
    tax += min(taxable_income, SCOT_STARTER_LIMIT) * 0.19
    return tax


def calculate_take_home(gross_salary, employee_pension_pct=0, jurisdiction="england"):
    pension_contribution = gross_salary * employee_pension_pct / 100
    adjusted_net_income = gross_salary - pension_contribution

    personal_allowance = PERSONAL_ALLOWANCE
    if adjusted_net_income > PA_TAPER_START:
        personal_allowance = max(
            0, personal_allowance - (adjusted_net_income - PA_TAPER_START) / 2
        )

    taxable_income = max(0, adjusted_net_income - personal_allowance)

    if jurisdiction == "scotland":
        income_tax = _calc_scotland_income_tax(taxable_income)
    else:
        income_tax = 0.0
        if taxable_income > HIGHER_RATE_THRESHOLD:
            income_tax += (taxable_income - HIGHER_RATE_THRESHOLD) * 0.45
            income_tax += (HIGHER_RATE_THRESHOLD - BASIC_RATE_LIMIT) * 0.40
            income_tax += BASIC_RATE_LIMIT * 0.20
        elif taxable_income > BASIC_RATE_LIMIT:
            income_tax += (taxable_income - BASIC_RATE_LIMIT) * 0.40
            income_tax += BASIC_RATE_LIMIT * 0.20
        elif taxable_income > 0:
            income_tax += taxable_income * 0.20

    national_insurance = 0.0
    if adjusted_net_income > NI_UPPER_THRESHOLD:
        national_insurance += (adjusted_net_income - NI_UPPER_THRESHOLD) * 0.02
        national_insurance += (NI_UPPER_THRESHOLD - NI_PRIMARY_THRESHOLD) * 0.08
    elif adjusted_net_income > NI_PRIMARY_THRESHOLD:
        national_insurance += (adjusted_net_income - NI_PRIMARY_THRESHOLD) * 0.08

    take_home = adjusted_net_income - income_tax - national_insurance
    tax_rate = (income_tax + national_insurance) / gross_salary * 100
    deduction_rate = (gross_salary - take_home) / gross_salary * 100

    return {
        'gross': gross_salary,
        'employee_pension': pension_contribution,
        'adjusted_net_income': adjusted_net_income,
        'income_tax': income_tax,
        'national_insurance': national_insurance,
        'take_home': take_home,
        'tax_rate': tax_rate,
        'deduction_rate': deduction_rate,
    }


def calc_package_adjustments(gross, work):
    day_rate = gross / 260
    leave_adj = (work['leave_days'] - 25) * day_rate
    hourly_rate = gross / (52 * 37.5)
    hours_adj = (37.5 - work['hours_pw']) * hourly_rate * 52
    return leave_adj, hours_adj


def format_currency(value):
    return f"£{value:,.0f}"


def fmt_adj(value):
    if abs(value) < 0.5:
        return "—"
    sign = "+" if value >= 0 else "−"
    return f"{sign}{format_currency(abs(value))}"


def _is_strong(text):
    return '<strong>' in text


# ---------------------------------------------------------------------------
# Sidebar helpers
# ---------------------------------------------------------------------------

def position_sidebar_ui(prefix, default_salary, default_label):
    pos_label = st.sidebar.text_input("Label", default_label, key=f"{prefix}_label")
    salary = st.sidebar.number_input(
        "Gross Salary (£)", 10000, 500000, default_salary, 1000, key=f"{prefix}_salary"
    )
    jurisdiction_choice = st.sidebar.radio(
        "Jurisdiction", ["England / Wales / NI", "Scotland"],
        key=f"{prefix}_jurisdiction", horizontal=True,
    )
    jurisdiction = "scotland" if "Scotland" in jurisdiction_choice else "england"

    st.sidebar.markdown("**Working conditions**")
    leave_days = st.sidebar.number_input(
        "Annual leave (days)", 0, 60, 25, 1, key=f"{prefix}_leave"
    )
    office_days = st.sidebar.slider(
        "Office days required per week", 0, 5, 3, 1, key=f"{prefix}_office"
    )
    hours_pw = st.sidebar.number_input(
        "Hours per week", 10.0, 80.0, 37.5, 0.5, key=f"{prefix}_hours", format="%.1f",
    )
    work = {
        "jurisdiction": jurisdiction,
        "leave_days": leave_days,
        "office_days": office_days,
        "hours_pw": hours_pw,
    }

    st.sidebar.markdown("**Pension**")
    pension_enabled = st.sidebar.checkbox("Include pension", True, key=f"{prefix}_pen_enabled")
    if not pension_enabled:
        return salary, pos_label, work, {"enabled": False}

    ptype = st.sidebar.radio(
        "Type", ["DC (Defined Contribution)", "DB (Defined Benefit)"],
        key=f"{prefix}_ptype", horizontal=True,
    )
    employee_pct = st.sidebar.slider(
        "Employee contribution %", 0.0, 15.0, 5.0, 0.5, key=f"{prefix}_emp"
    )
    employer_pct = st.sidebar.slider(
        "Employer contribution %", 0.0, 30.0,
        3.0 if "DC" in ptype else 20.0,
        0.5, key=f"{prefix}_er",
    )
    if "DC" in ptype:
        pension = {"enabled": True, "type": "DC",
                   "employee_pct": employee_pct, "employer_pct": employer_pct}
    else:
        accrual = st.sidebar.selectbox(
            "Accrual rate", ["1/49", "1/57", "1/60", "1/80", "1/85"],
            key=f"{prefix}_accrual",
        )
        pension = {"enabled": True, "type": "DB",
                   "employee_pct": employee_pct, "employer_pct": employer_pct,
                   "accrual": accrual}

    return salary, pos_label, work, pension


# ---------------------------------------------------------------------------
# Comparison table
# ---------------------------------------------------------------------------

JURIS_LABEL = {"england": "Eng/Wales/NI", "scotland": "Scotland"}


def build_comparison_rows(data1, pension1, work1, data2, pension2, work2):
    er1 = data1['gross'] * pension1['employer_pct'] / 100 if pension1.get('enabled') else 0
    er2 = data2['gross'] * pension2['employer_pct'] / 100 if pension2.get('enabled') else 0
    leave_adj1, hours_adj1 = calc_package_adjustments(data1['gross'], work1)
    leave_adj2, hours_adj2 = calc_package_adjustments(data2['gross'], work2)
    cash_package1 = data1['gross'] + er1
    cash_package2 = data2['gross'] + er2
    adjusted_package1 = cash_package1 + leave_adj1 + hours_adj1
    adjusted_package2 = cash_package2 + leave_adj2 + hours_adj2
    either_pension = pension1.get('enabled') or pension2.get('enabled')

    def leave_note(w):
        d, diff = w['leave_days'], w['leave_days'] - 25
        return f"{d} days (standard)" if diff == 0 else \
               f"{d} days ({'+' if diff > 0 else ''}{diff} vs 25)"

    def hours_note(w):
        h, diff = w['hours_pw'], w['hours_pw'] - 37.5
        return "37.5 hrs (standard)" if abs(diff) < 0.01 else \
               f"{h:.1f} hrs ({'+' if diff > 0 else ''}{diff:.1f} vs 37.5)"

    rows = [
        ("Gross Salary",
         format_currency(data1['gross']), format_currency(data2['gross'])),
    ]

    if either_pension:
        rows.append((
            "Employer Pension",
            f"+{format_currency(er1)}" if pension1.get('enabled') else "—",
            f"+{format_currency(er2)}" if pension2.get('enabled') else "—",
        ))

    rows.append((
        "<strong>Total Package Value (cash)</strong>",
        f"<strong>{format_currency(cash_package1)}</strong>",
        f"<strong>{format_currency(cash_package2)}</strong>",
    ))

    rows += [
        (f"Annual Leave Adjustment<br><small style='color:#666;'>vs 25-day standard</small>",
         f"{fmt_adj(leave_adj1)}<br><small style='color:#888;'>{leave_note(work1)}</small>",
         f"{fmt_adj(leave_adj2)}<br><small style='color:#888;'>{leave_note(work2)}</small>"),
        (f"Hours Adjustment<br><small style='color:#666;'>normalised to 37.5 hr/wk</small>",
         f"{fmt_adj(hours_adj1)}<br><small style='color:#888;'>{hours_note(work1)}</small>",
         f"{fmt_adj(hours_adj2)}<br><small style='color:#888;'>{hours_note(work2)}</small>"),
        ("<strong>Adjusted Total Package Value</strong>",
         f"<strong>{format_currency(adjusted_package1)}</strong>",
         f"<strong>{format_currency(adjusted_package2)}</strong>"),
        ("__sep__", "", ""),
    ]

    if work1['jurisdiction'] == work2['jurisdiction']:
        rows.append((
            f"Income Tax ({JURIS_LABEL[work1['jurisdiction']]})",
            f"−{format_currency(data1['income_tax'])}",
            f"−{format_currency(data2['income_tax'])}",
        ))
    else:
        rows.append((
            "Income Tax",
            f"−{format_currency(data1['income_tax'])}<br><small style='color:#888;'>{JURIS_LABEL[work1['jurisdiction']]}</small>",
            f"−{format_currency(data2['income_tax'])}<br><small style='color:#888;'>{JURIS_LABEL[work2['jurisdiction']]}</small>",
        ))

    rows.append((
        "National Insurance",
        f"−{format_currency(data1['national_insurance'])}",
        f"−{format_currency(data2['national_insurance'])}",
    ))

    if either_pension:
        rows.append((
            "Employee Pension Contribution",
            f"−{format_currency(data1['employee_pension'])}" if pension1.get('enabled') else "—",
            f"−{format_currency(data2['employee_pension'])}" if pension2.get('enabled') else "—",
        ))

    rows += [
        ("__sep__", "", ""),
        ("<strong>Take-Home (annual)</strong>",
         f"<strong>{format_currency(data1['take_home'])}</strong>",
         f"<strong>{format_currency(data2['take_home'])}</strong>"),
        ("Take-Home (monthly)",
         format_currency(data1['take_home'] / 12),
         format_currency(data2['take_home'] / 12)),
        ("__sep__", "", ""),
        ("Tax Rate (IT + NI)", f"{data1['tax_rate']:.1f}%", f"{data2['tax_rate']:.1f}%"),
        ("Total Deduction Rate (incl. employee pension)",
         f"{data1['deduction_rate']:.1f}%", f"{data2['deduction_rate']:.1f}%"),
        ("__sep__", "", ""),
        ("Office Days Required / Week",
         f"{work1['office_days']} day{'s' if work1['office_days'] != 1 else ''}",
         f"{work2['office_days']} day{'s' if work2['office_days'] != 1 else ''}"),
    ]

    if pension1.get('type') == 'DB' or pension2.get('type') == 'DB':
        rows.append((
            "DB Accrual Rate",
            pension1.get('accrual', '—') if pension1.get('type') == 'DB' else "—",
            pension2.get('accrual', '—') if pension2.get('type') == 'DB' else "—",
        ))

    if either_pension:
        def pension_summary(p):
            if not p.get('enabled'):
                return "None"
            if p['type'] == 'DC':
                return f"DC · {p['employee_pct']:.1f}% emp / {p['employer_pct']:.1f}% er"
            return f"DB · {p.get('accrual','')} · {p['employee_pct']:.1f}% emp / {p['employer_pct']:.1f}% er (notional)"
        rows.append(("Pension Scheme", pension_summary(pension1), pension_summary(pension2)))

    return rows, adjusted_package1, adjusted_package2


def display_comparison_table(title1, title2, rows):
    html_rows = ""
    non_sep = 0
    for label, v1, v2 in rows:
        if label == "__sep__":
            html_rows += (
                '<tr><td colspan="3" style="padding:0;">'
                '<hr style="margin:4px 0;border:none;border-top:1px solid #ccd6e0;"></td></tr>'
            )
            continue
        bg = "#f4f8fc" if non_sep % 2 == 0 else "#ffffff"
        non_sep += 1
        html_rows += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:11px 18px;font-size:1.08rem;color:#222;vertical-align:top;">{label}</td>'
            f'<td style="padding:11px 18px;font-size:1.08rem;text-align:right;color:#1a3c5e;vertical-align:top;">{v1}</td>'
            f'<td style="padding:11px 18px;font-size:1.08rem;text-align:right;color:#1a5e34;vertical-align:top;">{v2}</td>'
            f'</tr>'
        )
    html = f"""
<table style="width:100%;border-collapse:collapse;margin-bottom:28px;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.10);">
  <thead>
    <tr style="background:#1a3c5e;color:white;">
      <th style="padding:14px 18px;font-size:1.15rem;text-align:left;font-weight:600;width:40%;"></th>
      <th style="padding:14px 18px;font-size:1.15rem;text-align:right;font-weight:600;">{title1}</th>
      <th style="padding:14px 18px;font-size:1.15rem;text-align:right;font-weight:600;">{title2}</th>
    </tr>
  </thead>
  <tbody>{html_rows}</tbody>
</table>"""
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Chart data
# ---------------------------------------------------------------------------

@st.cache_data
def create_salary_data(max_salary, pension_rate, jurisdiction):
    salaries = np.linspace(15000, max_salary, 50)
    data = []
    for salary in salaries:
        r = calculate_take_home(salary, pension_rate, jurisdiction)
        data.append({
            'salary': salary,
            'take_home': r['take_home'],
            'income_tax': r['income_tax'],
            'national_insurance': r['national_insurance'],
            'pension': r['employee_pension'],
            'tax_rate': r['tax_rate'],
            'deduction_rate': r['deduction_rate'],
            'income_tax_pct': r['income_tax'] / salary * 100,
            'ni_pct': r['national_insurance'] / salary * 100,
            'pension_pct': r['employee_pension'] / salary * 100,
            'take_home_pct': r['take_home'] / salary * 100,
        })
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

_FOOTER_TEXT = (
    "2026/27 England/Wales/NI rates: Personal allowance £12,570 · Basic rate 20% to £50,270 · "
    "Higher rate 40% to £125,140 · Additional rate 45% above · Employee NI 8% (PT–UEL) / 2% above UEL · "
    "Personal allowance tapers from £100,000. "
    "Scottish income tax uses 2025/26 bands (2026/27 not yet confirmed): "
    "Starter 19% · Basic 20% · Intermediate 21% · Higher 42% · Advanced 45% · Top 48%. "
    "NI is the same across the UK. "
    "Annual Leave Adjustment values one day as gross ÷ 260; adjusts vs 25-day standard. "
    "Hours Adjustment normalises to 37.5 hr/wk equivalent. "
    "DB employer cost % is notional. "
    "Does not include student loan repayments, salary sacrifice, Marriage Allowance, or childcare vouchers."
)


def generate_html_report(title1, title2, rows, metrics_rows, today):
    """Build a self-contained HTML document. Returns a UTF-8 string."""
    table_rows_html = ""
    non_sep = 0
    for label, v1, v2 in rows:
        if label == "__sep__":
            table_rows_html += (
                '<tr><td colspan="3" style="padding:0;">'
                '<hr style="margin:4px 0;border:none;border-top:1px solid #ccd6e0;"></td></tr>\n'
            )
            continue
        bg = "#f4f8fc" if non_sep % 2 == 0 else "#ffffff"
        non_sep += 1
        table_rows_html += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:10px 16px;font-size:15px;vertical-align:top;">{label}</td>'
            f'<td style="padding:10px 16px;font-size:15px;text-align:right;color:#1a3c5e;vertical-align:top;">{v1}</td>'
            f'<td style="padding:10px 16px;font-size:15px;text-align:right;color:#1a5e34;vertical-align:top;">{v2}</td>'
            f'</tr>\n'
        )

    metrics_html = "".join(
        f'<div style="display:inline-block;margin:0 28px 16px 0;">'
        f'<div style="font-size:12px;color:#666;margin-bottom:4px;">{lbl}</div>'
        f'<div style="font-size:20px;font-weight:700;color:#1a3c5e;">{val}</div>'
        f'</div>\n'
        for lbl, val in metrics_rows
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>UK Total Compensation Comparison</title>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;max-width:980px;margin:40px auto;padding:0 24px;color:#222;}}
  h1{{color:#1a3c5e;font-size:26px;margin-bottom:4px;}}
  .sub{{color:#666;font-size:13px;margin-bottom:28px;}}
  table{{width:100%;border-collapse:collapse;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.10);margin-bottom:32px;}}
  thead tr{{background:#1a3c5e;color:#fff;}}
  th{{padding:13px 16px;font-size:15px;font-weight:600;}}
  th:first-child{{text-align:left;width:40%;}}
  th:not(:first-child){{text-align:right;}}
  .metrics{{background:#f4f8fc;border-radius:8px;padding:20px 24px;margin-bottom:32px;}}
  h2{{color:#1a3c5e;font-size:18px;margin:0 0 16px;}}
  .footer{{font-size:12px;color:#888;border-top:1px solid #ddd;padding-top:16px;line-height:1.6;}}
</style>
</head>
<body>
<h1>&#128188; UK Total Compensation Comparison</h1>
<p class="sub">Generated {today} &middot; 2026/27 tax year &middot; England, Wales, Northern Ireland and Scotland</p>

<table>
  <thead><tr>
    <th></th>
    <th>{title1}</th>
    <th>{title2}</th>
  </tr></thead>
  <tbody>{table_rows_html}</tbody>
</table>

<div class="metrics">
  <h2>Difference Analysis</h2>
  {metrics_html}
</div>

<div class="footer">{_FOOTER_TEXT}</div>
</body>
</html>"""


def generate_pdf_report(title1, title2, rows, metrics_rows, today):
    """Build a PDF using reportlab. Returns bytes."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=18*mm, bottomMargin=18*mm,
    )
    styles = getSampleStyleSheet()
    DARK  = colors.HexColor('#1a3c5e')
    BLUE  = colors.HexColor('#1a3c5e')
    GREEN = colors.HexColor('#1a5e34')
    ALT   = colors.HexColor('#f4f8fc')

    def _prep(text):
        """Prepare text for reportlab Paragraph: normalise HTML."""
        text = re.sub(r'<br\s*/?>', '<br/>', text, flags=re.IGNORECASE)
        text = re.sub(r'<strong>(.*?)</strong>', r'<b>\1</b>', text, flags=re.DOTALL)
        text = re.sub(r'<small[^>]*>(.*?)</small>', r'<font size="6" color="grey">\1</font>', text, flags=re.DOTALL)
        # strip remaining unknown tags
        text = re.sub(r'<(?!b>|/b>|br/>|font|/font)[^>]+>', '', text)
        return text

    def cell(text, bold=False, align=TA_LEFT, color=colors.black, size=8):
        return Paragraph(_prep(text), ParagraphStyle(
            'c', parent=styles['Normal'],
            fontSize=size, leading=size * 1.45,
            textColor=color, alignment=align,
            fontName='Helvetica-Bold' if bold else 'Helvetica',
        ))

    story = []

    # Title block
    story.append(Paragraph("UK Total Compensation Comparison", ParagraphStyle(
        'h1', parent=styles['Title'], fontSize=17, textColor=DARK, spaceAfter=3,
    )))
    story.append(Paragraph(f"Generated {today} · 2026/27 tax year", ParagraphStyle(
        'sub', parent=styles['Normal'], fontSize=8, textColor=colors.grey, spaceAfter=14,
    )))

    # Comparison table
    usable = A4[0] - 36*mm
    col_w = [usable * 0.42, usable * 0.29, usable * 0.29]

    tdata = [[
        cell("", bold=True, size=9),
        cell(title1, bold=True, align=TA_RIGHT, color=colors.white, size=9),
        cell(title2, bold=True, align=TA_RIGHT, color=colors.white, size=9),
    ]]
    sep_indices = []
    idx = 1
    for label, v1, v2 in rows:
        if label == "__sep__":
            sep_indices.append(idx)
            tdata.append([Spacer(1, 3), '', ''])
            idx += 1
            continue
        bold = _is_strong(label)
        tdata.append([
            cell(label, bold=bold),
            cell(v1, bold=bold, align=TA_RIGHT, color=BLUE),
            cell(v2, bold=bold, align=TA_RIGHT, color=GREEN),
        ])
        idx += 1

    ts = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [ALT, colors.white]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('BOX', (0, 0), (-1, -1), 0.4, colors.HexColor('#ccd6e0')),
    ])
    for si in sep_indices:
        ts.add('LINEABOVE', (0, si), (-1, si), 0.5, colors.HexColor('#ccd6e0'))
        ts.add('BACKGROUND', (0, si), (-1, si), colors.white)

    t = Table(tdata, colWidths=col_w, repeatRows=1)
    t.setStyle(ts)
    story.append(t)
    story.append(Spacer(1, 10))

    # Difference metrics
    story.append(Paragraph("Difference Analysis", ParagraphStyle(
        'h2', parent=styles['Heading2'], fontSize=12, textColor=DARK, spaceAfter=6,
    )))
    n = len(metrics_rows)
    mdata = [[
        Paragraph(
            f'<font size="7" color="grey">{lbl}</font><br/><b>{val}</b>',
            ParagraphStyle('m', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER)
        )
        for lbl, val in metrics_rows
    ]]
    mt = Table(mdata, colWidths=[usable / n] * n)
    mt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), ALT),
        ('BOX', (0, 0), (-1, -1), 0.4, colors.HexColor('#ccd6e0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#ccd6e0')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
    ]))
    story.append(mt)
    story.append(Spacer(1, 10))

    # Footer
    story.append(Paragraph(_FOOTER_TEXT, ParagraphStyle(
        'ft', parent=styles['Normal'], fontSize=6.5, textColor=colors.grey, leading=9,
    )))

    doc.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.title("💼 UK Total Compensation Comparison")
    st.markdown(
        "Compare the full value of job offers — salary, pension, annual leave, and working hours. "
        "**2026/27 tax year · England, Wales, Northern Ireland and Scotland.**"
    )

    # ── Sidebar ──────────────────────────────────────────────────────────────
    st.sidebar.header("Position 1")
    salary1, label1, work1, pension1 = position_sidebar_ui("p1", 35000, "Position 1")

    st.sidebar.divider()
    st.sidebar.header("Position 2")
    salary2, label2, work2, pension2 = position_sidebar_ui("p2", 50000, "Position 2")

    st.sidebar.divider()
    st.sidebar.header("Charts")
    max_salary = st.sidebar.slider("Max salary for charts", 50000, 500000, 100000, 10000)
    chart_pension_rate = st.sidebar.slider(
        "Illustrative employee pension %", 0.0, 15.0, 5.0, 0.5,
        help="Employee contribution rate used for the general salary curves.",
    )
    chart_jurisdiction = st.sidebar.radio(
        "Chart jurisdiction", ["England / Wales / NI", "Scotland"],
        horizontal=True, key="chart_juris",
    )
    chart_juris_key = "scotland" if "Scotland" in chart_jurisdiction else "england"

    # ── Calculations ─────────────────────────────────────────────────────────
    emp_pct1 = pension1['employee_pct'] if pension1.get('enabled') else 0
    emp_pct2 = pension2['employee_pct'] if pension2.get('enabled') else 0
    data1 = calculate_take_home(salary1, emp_pct1, work1['jurisdiction'])
    data2 = calculate_take_home(salary2, emp_pct2, work2['jurisdiction'])

    # ── Comparison table ─────────────────────────────────────────────────────
    st.header("Package Comparison")
    rows, adj_pkg1, adj_pkg2 = build_comparison_rows(
        data1, pension1, work1, data2, pension2, work2
    )
    display_comparison_table(
        f"{label1}<br><small style='font-weight:normal;'>{format_currency(salary1)}</small>",
        f"{label2}<br><small style='font-weight:normal;'>{format_currency(salary2)}</small>",
        rows,
    )

    # ── Difference metrics ────────────────────────────────────────────────────
    st.header("Difference Analysis")
    col1, col2, col3, col4, col5 = st.columns(5)
    er1 = salary1 * pension1['employer_pct'] / 100 if pension1.get('enabled') else 0
    er2 = salary2 * pension2['employer_pct'] / 100 if pension2.get('enabled') else 0
    gross_diff    = salary2 - salary1
    package_diff  = (salary2 + er2) - (salary1 + er1)
    adj_diff      = adj_pkg2 - adj_pkg1
    takehome_diff = data2['take_home'] - data1['take_home']
    keep_pct      = (takehome_diff / gross_diff * 100) if gross_diff != 0 else 0

    with col1: st.metric("Gross Difference", format_currency(gross_diff))
    with col2: st.metric("Cash Package Difference", format_currency(package_diff))
    with col3: st.metric("Adjusted Package Difference", format_currency(adj_diff))
    with col4: st.metric("Take-Home Difference", format_currency(takehome_diff))
    with col5: st.metric("You Keep of Extra Gross", f"{keep_pct:.1f}%")

    # ── Export ────────────────────────────────────────────────────────────────
    st.header("Export")
    today_str = date.today().strftime("%d %B %Y")
    title1_plain = f"{label1} ({format_currency(salary1)})"
    title2_plain = f"{label2} ({format_currency(salary2)})"
    metrics_rows = [
        ("Gross Difference",           format_currency(gross_diff)),
        ("Cash Package Difference",    format_currency(package_diff)),
        ("Adjusted Package Diff.",     format_currency(adj_diff)),
        ("Take-Home Difference",       format_currency(takehome_diff)),
        ("You Keep of Extra Gross",    f"{keep_pct:.1f}%"),
    ]

    exp_col1, exp_col2 = st.columns(2)

    with exp_col1:
        html_bytes = generate_html_report(
            title1_plain, title2_plain, rows, metrics_rows, today_str
        ).encode("utf-8")
        st.download_button(
            label="⬇ Download HTML",
            data=html_bytes,
            file_name="compensation_comparison.html",
            mime="text/html",
            use_container_width=True,
        )

    with exp_col2:
        try:
            pdf_bytes = generate_pdf_report(
                title1_plain, title2_plain, rows, metrics_rows, today_str
            )
            st.download_button(
                label="⬇ Download PDF",
                data=pdf_bytes,
                file_name="compensation_comparison.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except ImportError:
            st.info("`reportlab` not installed — run `pip install reportlab` to enable PDF export.")

    # ── Charts ────────────────────────────────────────────────────────────────
    df = create_salary_data(max_salary, chart_pension_rate, chart_juris_key)

    st.header("Gross vs Take-Home Salary")
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=df['salary'], y=df['salary'],
        mode='lines', name='Gross Salary',
        line=dict(color='#1a3c5e', dash='dash', width=2),
    ))
    fig1.add_trace(go.Scatter(
        x=df['salary'], y=df['take_home'],
        mode='lines', name='Take-Home Salary',
        line=dict(color='#2ecc71', width=3),
        fill='tonexty', fillcolor='rgba(52,152,219,0.10)',
    ))
    fig1.update_layout(xaxis_title="Gross Salary (£)", yaxis_title="Amount (£)",
                       hovermode='x unified', height=480)
    st.plotly_chart(fig1, use_container_width=True)

    st.header("Tax & Deduction Rates by Salary")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=df['salary'], y=df['tax_rate'],
        mode='lines', name='Tax Rate (IT + NI)',
        line=dict(color='#e67e22', width=3),
    ))
    if chart_pension_rate > 0:
        fig2.add_trace(go.Scatter(
            x=df['salary'], y=df['deduction_rate'],
            mode='lines', name='Total Deduction Rate (incl. pension)',
            line=dict(color='#e74c3c', width=2, dash='dot'),
        ))
    fig2.update_layout(xaxis_title="Gross Salary (£)", yaxis_title="Rate (%)",
                       hovermode='x unified', height=400)
    st.plotly_chart(fig2, use_container_width=True)

    st.header("Tax Breakdown by Component (% of Gross)")
    df_sampled = df.iloc[::5].copy()
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(x=df_sampled['salary'], y=df_sampled['income_tax_pct'],
                          name='Income Tax', marker_color='#e74c3c'))
    fig3.add_trace(go.Bar(x=df_sampled['salary'], y=df_sampled['ni_pct'],
                          name='National Insurance', marker_color='#e67e22'))
    if chart_pension_rate > 0:
        fig3.add_trace(go.Bar(x=df_sampled['salary'], y=df_sampled['pension_pct'],
                              name='Employee Pension', marker_color='#3498db'))
    fig3.add_trace(go.Bar(x=df_sampled['salary'], y=df_sampled['take_home_pct'],
                          name='Take-Home', marker_color='#2ecc71'))
    fig3.update_layout(
        barmode='stack', xaxis_title="Gross Salary (£)",
        yaxis_title="% of Gross Salary",
        yaxis=dict(ticksuffix="%", range=[0, 100]),
        height=500, hovermode='x unified',
    )
    st.plotly_chart(fig3, use_container_width=True)

    # ── Data table ────────────────────────────────────────────────────────────
    if st.checkbox("Show detailed breakdown table"):
        st.header("Detailed Breakdown")
        display_df = df.copy()
        for col in ['take_home', 'income_tax', 'national_insurance', 'pension']:
            display_df[col] = display_df[col].apply(lambda x: f"£{x:,.0f}")
        display_df['salary'] = display_df['salary'].apply(lambda x: f"£{x:,.0f}")
        display_df['tax_rate'] = display_df['tax_rate'].apply(lambda x: f"{x:.1f}%")
        display_df['deduction_rate'] = display_df['deduction_rate'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(
            display_df[['salary', 'take_home', 'income_tax', 'national_insurance',
                         'pension', 'tax_rate', 'deduction_rate']],
            use_container_width=True,
        )

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"""
**2026/27 England/Wales/NI rates:** Personal allowance £12,570 · Basic rate 20% to £50,270 · Higher rate 40% to £125,140 · Additional rate 45% above · Employee NI 8% (PT–UEL) / 2% above UEL · Personal allowance tapers from £100,000.

**Scottish income tax** uses 2025/26 bands (2026/27 not yet confirmed): Starter 19% · Basic 20% · Intermediate 21% · Higher 42% · Advanced 45% · Top 48%. NI is the same across the UK.

**Annual Leave Adjustment** values one day as gross ÷ 260; adjusts vs 25-day standard. **Hours Adjustment** normalises to 37.5 hr/wk. **DB employer cost %** is notional. Does not include student loan, salary sacrifice, Marriage Allowance, or childcare vouchers.
    """)


if __name__ == "__main__":
    main()
