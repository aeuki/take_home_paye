from datetime import date

import streamlit as st

st.set_page_config(page_title="UK Take-Home Calculator", page_icon="💼", layout="centered")

# ---------------------------------------------------------------------------
# 2026/27 tax constants — England, Wales & Northern Ireland
# ---------------------------------------------------------------------------
PERSONAL_ALLOWANCE    = 12_570
PA_TAPER_START        = 100_000
BASIC_RATE_LIMIT      =  37_700
HIGHER_RATE_THRESHOLD = 125_140
NI_PRIMARY_THRESHOLD  =  12_570
NI_UPPER_THRESHOLD    =  50_270


def calculate_take_home(gross, employee_pension_pct=0):
    pension  = gross * employee_pension_pct / 100
    ani      = gross - pension  # adjusted net income

    pa = PERSONAL_ALLOWANCE
    if ani > PA_TAPER_START:
        pa = max(0, pa - (ani - PA_TAPER_START) / 2)

    taxable = max(0, ani - pa)

    if taxable > HIGHER_RATE_THRESHOLD:
        it = (taxable - HIGHER_RATE_THRESHOLD) * 0.45 \
           + (HIGHER_RATE_THRESHOLD - BASIC_RATE_LIMIT) * 0.40 \
           + BASIC_RATE_LIMIT * 0.20
    elif taxable > BASIC_RATE_LIMIT:
        it = (taxable - BASIC_RATE_LIMIT) * 0.40 + BASIC_RATE_LIMIT * 0.20
    else:
        it = taxable * 0.20

    if ani > NI_UPPER_THRESHOLD:
        ni = (ani - NI_UPPER_THRESHOLD) * 0.02 \
           + (NI_UPPER_THRESHOLD - NI_PRIMARY_THRESHOLD) * 0.08
    elif ani > NI_PRIMARY_THRESHOLD:
        ni = (ani - NI_PRIMARY_THRESHOLD) * 0.08
    else:
        ni = 0.0

    take_home = ani - it - ni
    return {
        "gross":       gross,
        "pension_ee":  pension,
        "ani":         ani,
        "income_tax":  it,
        "ni":          ni,
        "take_home":   take_home,
        "tax_rate":    (it + ni) / gross * 100,
        "deduction_rate": (gross - take_home) / gross * 100,
    }


def fmt(v):
    return f"£{v:,.0f}"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.header("Inputs")

salary = st.sidebar.number_input("Base Salary (£)", 10_000, 500_000, 35_000, 1_000)
bonus_pct = st.sidebar.number_input(
    "Annual bonus (%)", 0.0, 200.0, 0.0, 1.0, format="%.1f",
    help="% of base salary, taxed as income.",
)

st.sidebar.markdown("**Working conditions**")
leave_days = st.sidebar.number_input("Annual leave (days)", 0, 60, 25, 1)
hours_pw   = st.sidebar.number_input("Hours per week", 10.0, 80.0, 37.5, 0.5, format="%.1f")
commute    = st.sidebar.number_input(
    "Annual commuting cost (£)", 0, 30_000, 0, 100,
    help="Rail, parking, fuel, etc.",
)

st.sidebar.markdown("**Pension**")
pen_on   = st.sidebar.checkbox("Include pension", True)
pen_ee   = st.sidebar.slider("Employee contribution %", 5.0, 15.0, 5.0, 0.5) if pen_on else 0.0
pen_er   = st.sidebar.slider("Employer contribution %", 3.0, 30.0, 3.0, 0.5) if pen_on else 0.0

# ---------------------------------------------------------------------------
# Calculations
# ---------------------------------------------------------------------------
gross   = salary * (1 + bonus_pct / 100)
d       = calculate_take_home(gross, pen_ee if pen_on else 0)
er      = gross * pen_er / 100 if pen_on else 0
bonus   = salary * bonus_pct / 100

day_rate   = gross / 260
leave_adj  = (leave_days - 25) * day_rate
hours_adj  = (37.5 - hours_pw) * (gross / (52 * 37.5)) * 52
net_commute = d["take_home"] - commute

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
st.title("UK Take-Home Calculator")
st.caption(f"2026/27 tax year · England, Wales & Northern Ireland · {date.today().strftime('%d %b %Y')}")

def row(label, value, strong=False, note="", deduction=False):
    lbl  = f"<strong>{label}</strong>" if strong else label
    val  = f"{'−' if deduction else ''}{fmt(abs(value))}"
    val  = f"<strong>{val}</strong>" if strong else val
    note_html = f"<br><small style='color:#888;'>{note}</small>" if note else ""
    return f"<tr><td style='padding:9px 16px;color:#222;'>{lbl}</td><td style='padding:9px 16px;text-align:right;color:#1a3c5e;'>{val}{note_html}</td></tr>"

def sep():
    return '<tr><td colspan="2" style="padding:0;"><hr style="margin:3px 0;border:none;border-top:1px solid #ccd6e0;"></td></tr>'

rows_html = ""

if bonus_pct:
    rows_html += row("Base Salary", salary)
    rows_html += row("Annual Bonus", bonus, note=f"{bonus_pct:.1f}% of base")
    rows_html += row("Total Gross", gross, strong=True)
else:
    rows_html += row("Base Salary", salary, strong=True)

if pen_on:
    rows_html += row("Employer Pension", er, note=f"{pen_er:.1f}% of gross")

rows_html += row("Total Compensation", gross + er, strong=True)
rows_html += sep()

leave_note = f"{leave_days}d — {'+' if leave_days > 25 else ''}{leave_days - 25:+.0f} vs 25d standard" if leave_days != 25 else f"{leave_days}d (standard)"
hours_note = f"{hours_pw:.1f} hrs — {hours_pw - 37.5:+.1f} vs 37.5 standard"   if abs(hours_pw - 37.5) > 0.01 else "37.5 hrs (standard)"

rows_html += row("Leave Adjustment", leave_adj,  note=leave_note)
rows_html += row("Hours Adjustment", hours_adj,  note=hours_note)
rows_html += row("Adjusted Compensation", gross + er + leave_adj + hours_adj, strong=True)
rows_html += sep()

rows_html += row("Income Tax",         d["income_tax"], deduction=True)
rows_html += row("National Insurance", d["ni"],          deduction=True)
if pen_on:
    rows_html += row("Employee Pension", d["pension_ee"], deduction=True, note=f"{pen_ee:.1f}% of gross")
rows_html += sep()

rows_html += row("Take-Home / year",  d["take_home"],       strong=True)
rows_html += row("Take-Home / month", d["take_home"] / 12)

if commute:
    rows_html += row("Commuting Cost", commute, deduction=True)
    rows_html += row("Net after Commuting / year",  net_commute,       strong=True)
    rows_html += row("Net after Commuting / month", net_commute / 12)

rows_html += sep()
rows_html += f"<tr><td style='padding:9px 16px;color:#222;'>Tax Rate (IT + NI)</td><td style='padding:9px 16px;text-align:right;color:#1a3c5e;'>{d['tax_rate']:.1f}%</td></tr>"
rows_html += f"<tr><td style='padding:9px 16px;color:#222;'>Total Deduction Rate</td><td style='padding:9px 16px;text-align:right;color:#1a3c5e;'>{d['deduction_rate']:.1f}%</td></tr>"

st.markdown(f"""
<table style="width:100%;border-collapse:collapse;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.10);">
  <thead>
    <tr style="background:#1a3c5e;color:white;">
      <th style="padding:12px 16px;text-align:left;font-weight:600;width:55%;">Component</th>
      <th style="padding:12px 16px;text-align:right;font-weight:600;">Amount</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
""", unsafe_allow_html=True)

st.markdown("---")
st.caption(
    "2026/27 rates: Personal allowance £12,570 · Basic 20% to £50,270 · Higher 40% to £125,140 · "
    "Additional 45% above · NI 8% (PT–UEL) / 2% above UEL · PA tapers from £100,000. "
    "Pension contributions treated as salary sacrifice (reduce NI-able pay). "
    "Leave adjustment: 1 day = gross ÷ 260. Hours adjustment normalised to 37.5 hr/wk."
)
