# Chemical Equipment Parameter Visualizer (Hybrid Web + Desktop)

A production-style hybrid analytics app for chemical equipment parameters. The same Django + DRF backend powers both **Web (React + Chart.js)** and **Desktop (PyQt5 + Matplotlib)** UIs with consistent summaries, charts, and PDF reports.

## Why This Project Stands Out
- Single source of truth: one backend serves both web and desktop.
- Consistent visuals: equipment mix, pressure vs flowrate, temperature profile, flowrate distribution.
- Last-5 dataset history with rich summaries.
- PDF report with branding, full table, and charts.
- Offline-capable desktop (local parsing + analytics if backend is unreachable).
- Light/Dark themes across both clients.

## Tech Stack
- **Backend:** Django + Django REST Framework
- **Data:** Pandas
- **Database:** SQLite (stores last 5 datasets)
- **Web:** React + Chart.js (Vite)
- **Desktop:** PyQt5 + Matplotlib

## Required CSV Columns
The CSV must include these columns (case-insensitive, extra columns allowed):
- `Equipment Name`
- `Type`
- `Flowrate`
- `Pressure`
- `Temperature`

Sample file: `sample_equipment_data.csv`

## Architecture Overview
1. **Upload** CSV from web or desktop.
2. **Backend** validates columns, normalizes data, computes summary + insights.
3. **Storage**: dataset metadata + CSV stored, last 5 retained.
4. **Clients** render:
   - Summary cards
   - Process intelligence
   - Charts
   - Full equipment table
5. **Reports**: PDF generated on backend, downloadable or email-able.

## Quickstart (Windows)
### 1) Backend
```cmd
cd /d C:\Users\HP\Downloads\Fossee_Task
C:\Users\HP\Downloads\Fossee_Task\.venv\Scripts\activate.bat
pip install -r requirements.txt
python backend\manage.py migrate
python backend\manage.py runserver
```

### 2) Web Frontend
```cmd
cd /d C:\Users\HP\Downloads\Fossee_Task\frontend-web
npm install
npm run dev
```
Web runs at: `http://localhost:5173`

### 3) Desktop App
```cmd
cd /d C:\Users\HP\Downloads\Fossee_Task
C:\Users\HP\Downloads\Fossee_Task\.venv\Scripts\activate.bat
python frontend-desktop\app.py
```

### If PowerShell blocks activation
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Environment Variables
**Backend (optional)**
- `REQUIRE_AUTH=1` to enable Basic Auth for write endpoints
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` for email reports

**Desktop (optional)**
- `CHEMVIZ_API_URL` (default: `http://localhost:8000/api`)

**Web (optional)**
- `VITE_API_URL` (default: `/api` via Vite proxy)

## API Endpoints
- `POST /api/upload/`
- `GET /api/datasets/`
- `GET /api/datasets/<id>/?include_rows=1`
- `GET /api/datasets/<id>/report/`
- `POST /api/datasets/<id>/email/`
- `GET /api/datasets/<id>/live/` (web live telemetry)

## Offline Desktop Mode
If the backend is unreachable, the desktop app:
- Parses CSV locally with Pandas
- Computes identical summaries + insights
- Renders the same chart set

## PDF Report
The report includes:
- Dataset metadata (name, timestamp)
- Summary statistics
- Operational insights
- Full table (multi-page)
- Charts with explanations

## Project Structure
```
backend/
  api/
  backend/
  db.sqlite3
frontend-web/
  src/
  vite.config.js
frontend-desktop/
  app.py
sample_equipment_data.csv
```

## Troubleshooting
- **Web can?t reach backend**: ensure `python backend\manage.py runserver` is running.
- **Desktop preview empty**: verify backend URL or set `CHEMVIZ_API_URL`.
- **Auth errors**: set `REQUIRE_AUTH=0` or supply credentials.
- **Email errors**: verify SMTP settings and app password.

