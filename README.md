# Philia — Film Accounting & Investment Analytics Platform

A digital ledger platform for independent film production companies: multi-currency
production cost tracking, GAAP-style revenue recognition, automated investor
distribution waterfalls, and budget variance / impairment risk analytics.

## Architecture

Pure Python: Django (ORM + admin as the data-entry/back-office layer) + Plotly
(server-rendered charts, no hand-written JS) + pandas/Decimal for financial math.

Five apps, each owning one piece of the accounting model:

- **`core`** — `Project` (a title), `Currency`, `ExchangeRate` (functional-currency conversion)
- **`ledger`** — `Account` (chart of accounts), `JournalEntry` / `JournalLine` — a real
  double-entry general ledger. Every line converts to USD (the functional currency) at
  the entry date's exchange rate; `JournalEntry.clean()` enforces debits == credits.
- **`revenue`** — `RevenueContract`, `RevenueMilestone`, `RevenueRecognitionEntry`.
  Simplified ASC 606: **point-in-time** (recognize on delivery), **straight-line**
  (spread evenly over a license term), or **milestone-based** recognition. Each
  recognized dollar posts a real journal entry (Dr A/R, Cr Revenue) via `revenue/services.py`.
- **`investors`** — `Investor`, `Investment`, `WaterfallTier`, `Distribution`,
  `DistributionLineItem`. `investors/services.py` runs an ordered recoupment waterfall
  (return of capital → preferred return → profit split), tracking what's already been
  paid per tier so repeated distribution runs never double-pay.
- **`budgeting`** — `Budget`, `BudgetLine`. `budgeting/services.py` computes actual
  spend straight from the ledger (not a duplicated number), rolls variance up by cost
  category (ATL/BTL/Post/Marketing/Overhead), and blends cost-overrun % with a
  revenue-shortfall % into a 0–100 impairment risk score.
- **`dashboard`** — read-only views that pull from the above and render Plotly charts:
  budget vs. actual, revenue recognized vs. contracted, investor ROI, and the
  distribution waterfall breakdown.

## Running it

```bash
source venv/bin/activate
python manage.py migrate
python manage.py seed_demo        # loads one realistic sample project
python manage.py runserver
```

Then visit `http://localhost:8000/` for the dashboard, or `http://localhost:8000/admin/`
(log in with the superuser you created above) to enter data directly: journal entries,
revenue contracts, investments, budgets, and distribution runs.

## What the seed data demonstrates

One project ("The Last Reel") with:
- A capital raise and production costs posted in **USD, GBP, and EUR**, converted to
  USD at the ledger level via `ExchangeRate`.
- All three revenue recognition methods, each posting real GL entries.
- Three investors (fund, individual, LLC) across equity and gap financing, three
  ordered waterfall tiers, and one finalized distribution run.
- A budget with an intentional BTL overrun (from the multi-currency location costs),
  visible in the variance dashboard and reflected in the risk score.

## Deploying to Render

This repo includes `render.yaml`, so Render can provision both the web service and a
free Postgres database from a single Blueprint:

1. Push this repo to GitHub.
2. On [render.com](https://render.com), click **New > Blueprint**, connect the repo,
   and accept the defaults — it reads `render.yaml` and creates the `philia` web
   service plus the `philia-db` Postgres database automatically.
3. Once deployed, open a shell for the service in the Render dashboard and run:
   ```bash
   python manage.py createsuperuser
   python manage.py seed_demo   # optional, loads the sample project
   ```
4. Your app is live at `https://philia-<random>.onrender.com`.

Free-tier note: the web service spins down after 15 minutes of inactivity and takes
~30-60s to wake back up on the next request — expected on a free plan, not a bug.

## Where this goes next

This is a working core, not the finished platform the resume bullet describes — it's
built to extend in the direction of whichever piece matters most:
- Real ASC 606 with contract modifications and variable consideration
- Multi-tier waterfalls with GP catch-up and carried interest
- Monte Carlo / scenario modeling for budget variance (pandas is already a dependency)
- Multi-user auth with investor-facing read-only portals
- Postgres + proper migrations-based deploy (swap `DATABASES` in `philia/settings.py`)
