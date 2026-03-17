# UK Total Compensation Comparison

A Streamlit web app to help understand and compare the full value of job offers.

**Tax year:** 2026/27 · **Jurisdiction:** England, Wales, Northern Ireland & Scotland

> **Live app:** https://takehomepaye.streamlit.app/

---

## Use cases

### Comparing job offers
Headline salaries can hide wide a very wide variation in total effective compensation. This tool aims to help understand what a role offers, and to compare two roles more fairly, by taking account of pension, leave, and other conditions of employment. Configure to see total package value, take-home pay, and the key deduction breakdown side by side.

### Understanding concealed package value
Employer pension contributions (especially in the public sector) can add 15–30% on top of gross salary in value. This tool shows:
- **DC schemes:** employer contribution alongside employee contribution
- **DB schemes:** accrual rate (e.g. 1/57th) and notional employer cost %, so you can better compare against a DC offer
- **Total Package Value** = gross salary + employer pension : what the role actually costs the employer and what the employee receives in total

### Pitching salary expectations
Many roles require applicants to propse a salary expectation.  To do this effectively it helps to understand take-home salary and the value of other benefits that the spec outlines.

### Understanding differences in gross salary
The tax breakdown chart shows Income Tax, National Insurance, employee pension, and take-home as a **percentage of gross salary** across the full salary range — making it clear how the proportions shift as salary rises, including the 60% effective marginal rate trap between £100,000 and £125,140. This helps to understand the practical value of differences in gross salary.  Is it worth taking a higher offer for a less attractive role?

---

## Features

- Compare two positions side by side in a single table (row labels appear once)
- Per-position pension configuration — fully independent between the two roles
- DC pension: configurable employee % and employer %
- DB pension: accrual rate selector plus employer notional cost % for package comparison
- Pension config is optional — disable per position if not applicable
- Total Package Value including employer pension contributions
- Annual leave and hours-per-week adjustments to normalise packages
- Scotland income tax support (2025/26 bands — 2026/27 not yet confirmed)
- Tax breakdown chart as % of gross salary (not £ amounts)
- Gross vs take-home and effective rate charts across salary range
- Configurable position labels
- Export comparison as HTML or PDF
- Detailed data table (optional)

---

## Local development

**Requirements:** Python 3.9+

```bash
# Clone the repo
git clone https://github.com/ay/paye_calc.git
cd paye_calc

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Deploy to Streamlit Community Cloud

1. Fork or clone this repo to your GitHub account.
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your GitHub account.
3. Click **New app**, select the repo and `app.py`, and deploy.
4. Your app will be live at a `*.streamlit.app` URL.

---

## Notes

- **England, Wales & Northern Ireland** rates are 2026/27.
- **Scotland** income tax uses 2025/26 bands as 2026/27 bands were not confirmed at time of writing. NI rates are the same across the UK.
- Does not account for student loan repayments, salary sacrifice, childcare vouchers, or Marriage Allowance.
- DB employer cost % is a notional figure entered by the user for comparison purposes — actual scheme costs vary by scheme and employer.

---

## Licence

[PolyForm Noncommercial License 1.0.0](LICENSE) — free for personal, educational, and non-commercial use. Commercial use is not permitted.
