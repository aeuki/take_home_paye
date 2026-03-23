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
    pension = gross * employee_pension_pct / 100
    ani     = gross - pension

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
        "gross":          gross,
        "pension_ee":     pension,
        "income_tax":     it,
        "ni":             ni,
        "take_home":      take_home,
        "tax_rate":       (it + ni) / gross * 100,
        "deduction_rate": (gross - take_home) / gross * 100,
    }


def fmt(v):
    return f"£{v:,.0f}"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.header("Inputs")

salary    = st.sidebar.number_input("Base Salary (£)", 10_000, 500_000, 35_000, 1_000)
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
pen_on = st.sidebar.checkbox("Include pension", True)
pen_ee = st.sidebar.slider("Employee contribution %", 0.0, 15.0, 5.0, 0.5) if pen_on else 0.0
pen_er = st.sidebar.slider("Employer contribution %", 0.0, 30.0, 3.0, 0.5) if pen_on else 0.0

# ---------------------------------------------------------------------------
# Calculations
# ---------------------------------------------------------------------------
gross      = salary * (1 + bonus_pct / 100)
bonus      = salary * bonus_pct / 100
d          = calculate_take_home(gross, pen_ee if pen_on else 0)
er         = gross * pen_er / 100 if pen_on else 0
day_rate   = gross / 260
leave_adj  = (leave_days - 25) * day_rate
hours_adj  = (37.5 - hours_pw) * (gross / (52 * 37.5)) * 52
net_commute = d["take_home"] - commute

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
st.title("UK Take-home Pay Calc")
st.caption(f"2026/27 · England, Wales & NI · {date.today().strftime('%d %b %Y')}")

# Headline metrics
col1, col2, col3 = st.columns(3)
col1.metric("Take-Home / year",  fmt(d["take_home"]))
col2.metric("Take-Home / month", fmt(d["take_home"] / 12))
col3.metric("Tax Rate (IT + NI)", f"{d['tax_rate']:.1f}%")

if pen_on or commute:
    col4, col5, col6 = st.columns(3)
    if pen_on:
        col4.metric("Total Compensation", fmt(gross + er))
    if commute:
        col5.metric("Net after Commuting", fmt(net_commute))
        col6.metric("Net / month", fmt(net_commute / 12))

st.divider()

# Gross section
st.subheader("Gross Pay")
if bonus_pct:
    c1, c2 = st.columns([3, 1])
    c1.write("Base Salary")
    c2.write(fmt(salary))
    c1, c2 = st.columns([3, 1])
    c1.write(f"Annual Bonus _{bonus_pct:.1f}% of base_")
    c2.write(fmt(bonus))
c1, c2 = st.columns([3, 1])
c1.write("**Total Gross**" if bonus_pct else "**Base Salary**")
c2.write(f"**{fmt(gross)}**")

if pen_on:
    c1, c2 = st.columns([3, 1])
    c1.write(f"Employer Pension _{pen_er:.1f}% of gross_")
    c2.write(fmt(er))
    c1, c2 = st.columns([3, 1])
    c1.write("**Total Compensation**")
    c2.write(f"**{fmt(gross + er)}**")

st.divider()

# Adjustments section
st.subheader("Adjustments")
leave_note = f"{leave_days}d — {leave_days - 25:+d} vs 25d standard" if leave_days != 25 else f"{leave_days}d (standard)"
hours_note = f"{hours_pw:.1f} hrs — {hours_pw - 37.5:+.1f} vs 37.5" if abs(hours_pw - 37.5) > 0.01 else "37.5 hrs (standard)"

c1, c2 = st.columns([3, 1])
c1.write(f"Leave Adjustment _{leave_note}_")
c2.write(fmt(leave_adj))
c1, c2 = st.columns([3, 1])
c1.write(f"Hours Adjustment _{hours_note}_")
c2.write(fmt(hours_adj))
c1, c2 = st.columns([3, 1])
c1.write("**Adjusted Compensation**")
c2.write(f"**{fmt(gross + er + leave_adj + hours_adj)}**")

st.divider()

# Deductions section
st.subheader("Deductions")
c1, c2 = st.columns([3, 1])
c1.write("Income Tax")
c2.write(f"−{fmt(d['income_tax'])}")
c1, c2 = st.columns([3, 1])
c1.write("National Insurance")
c2.write(f"−{fmt(d['ni'])}")
if pen_on:
    c1, c2 = st.columns([3, 1])
    c1.write(f"Employee Pension _{pen_ee:.1f}% of gross_")
    c2.write(f"−{fmt(d['pension_ee'])}")

st.divider()

# Take-home section
st.subheader("Take-Home")
c1, c2 = st.columns([3, 1])
c1.write("**Take-Home / year**")
c2.write(f"**{fmt(d['take_home'])}**")
c1, c2 = st.columns([3, 1])
c1.write("Take-Home / month")
c2.write(fmt(d["take_home"] / 12))

if commute:
    c1, c2 = st.columns([3, 1])
    c1.write("Commuting Cost")
    c2.write(f"−{fmt(commute)}")
    c1, c2 = st.columns([3, 1])
    c1.write("**Net after Commuting / year**")
    c2.write(f"**{fmt(net_commute)}**")
    c1, c2 = st.columns([3, 1])
    c1.write("Net after Commuting / month")
    c2.write(fmt(net_commute / 12))

st.divider()

c1, c2 = st.columns([3, 1])
c1.write("Tax Rate (IT + NI)")
c2.write(f"{d['tax_rate']:.1f}%")
c1, c2 = st.columns([3, 1])
c1.write("Total Deduction Rate")
c2.write(f"{d['deduction_rate']:.1f}%")

st.divider()
st.caption(
    "2026/27 rates: Personal allowance £12,570 · Basic 20% to £50,270 · Higher 40% to £125,140 · "
    "Additional 45% above · NI 8% (PT–UEL) / 2% above UEL · PA tapers from £100,000. "
    "Pension treated as salary sacrifice. Leave: 1 day = gross ÷ 260. Hours normalised to 37.5 hr/wk."
)
