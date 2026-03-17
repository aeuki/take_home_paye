# UK Total Compensation Comparator

A Streamlit web app for comparing the full value of job offers — not just headline salary, but everything that affects what you actually take home and what the employer is actually spending.

**Tax year:** 2026/27 · **Jurisdiction:** England, Wales & Northern Ireland

---

## Use cases

### Comparing job offers
Advertised salaries hide significant variation in real value. A role paying £5,000 less may be worth more once you account for a generous employer pension contribution, and the comparison tool surfaces this directly. Enter two positions, configure their respective packages, and see total package value, take-home pay, and the key deduction breakdown side by side — from a single set of row labels so nothing is repeated.

### Understanding concealed package value
Employer pension contributions (especially in the public sector) can add 15–30% on top of gross salary in value that never appears on a job advert. This tool shows:
- **DC schemes:** concrete employer £ contribution alongside employee contribution
- **DB schemes:** accrual rate (e.g. 1/57th) and notional employer cost %, so you can compare against a DC offer on a like-for-like basis
- **Total Package Value** = gross salary + employer pension — what the role actually costs the employer and what you're receiving in total

### Pitching salary expectations
When negotiating, it helps to frame a request in terms of what you'd actually keep. The "You Keep of Extra Gross" metric shows what fraction of any salary uplift reaches your pocket after tax and NI — useful for quantifying why a £3,000 raise matters less than it sounds, or for justifying a higher ask.

### Seeing where your money goes
The tax breakdown chart shows Income Tax, National Insurance, employee pension, and take-home as a **percentage of gross salary** across the full salary range — making it clear how the proportions shift as salary rises, including the 60% effective marginal rate trap between £100,000 and £125,140.

---

## Features

- Compare two positions side by side in a single table (row labels appear once)
- Per-position pension configuration — fully independent between the two roles
- DC pension: configurable employee % and employer %
- DB pension: accrual rate selector plus employer notional cost % for package comparison
- Pension config is optional — disable per position if not applicable
- Total Package Value including employer pension contributions
- Tax breakdown chart as % of gross salary (not £ amounts)
- Gross vs take-home and effective rate charts across salary range
- Configurable position labels
- Detailed data table (optional)

---

## Local Development

**Requirements:** Python 3.9+

```bash
# Clone the repo
git clone <your-repo-url>
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

## Hosting on Opalstack

Opalstack supports **Custom Apps** that bind to a port and are proxied through nginx. Streamlit fits this model well.

### Step 1 — Create a Custom App in Opalstack

1. Log in to your Opalstack control panel.
2. Go to **Apps → Add App**.
3. Choose **Custom App (Listening on Port)** (not Django or Flask).
4. Give it a name (e.g. `paye_calc`), select your server, and save.
5. Note the **port number** Opalstack assigns — you'll need it in Step 4.

### Step 2 — Add a Site/Route (optional, for a subdomain)

1. Go to **Sites → Add Site**.
2. Point a domain or subdomain at the custom app you just created.

### Step 3 — SSH in and set up the app

```bash
ssh <your-opalstack-username>@<your-server>

# Navigate to the apps directory (path shown in your Opalstack panel)
cd ~/apps/paye_calc

# Clone your repo into the app directory
git clone <your-repo-url> .

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4 — Set the PORT environment variable

Opalstack passes the assigned port via the `$PORT` environment variable when it starts your app.
The `start.sh` script reads `$PORT` automatically — **no edits needed**.

If you ever need to run the app manually (for testing), set it yourself:

```bash
export PORT=<port-from-opalstack-panel>
bash start.sh
```

### Step 5 — Configure the startup command in Opalstack

1. In the Opalstack panel, open your custom app's settings.
2. Set the **startup command** to:
   ```
   /home/<your-username>/apps/paye_calc/start.sh
   ```
3. Save and click **Restart App**.

### Step 6 — Verify

Visit your site URL (or `http://<server-ip>:<port>`) in a browser. You should see the calculator.

### Updating the app

```bash
ssh <your-opalstack-username>@<your-server>
cd ~/apps/paye_calc
git pull
# Restart via the Opalstack panel, or:
# Apps → your app → Restart
```

---

## Notes

- Covers England, Wales, and Northern Ireland tax rates. Scotland has different income tax bands and is out of scope.
- Does not account for student loan repayments, salary sacrifice, childcare vouchers, or Marriage Allowance.
- DB employer cost % is a notional figure entered by the user for comparison purposes — actual scheme costs vary by scheme and employer.
