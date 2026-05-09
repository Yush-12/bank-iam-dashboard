# IAM Access Review & SoD Violation Detector

This portfolio project demonstrates an automated, intelligent backend and modern frontend designed to enforce Identity and Access Management (IAM) compliance in banking environments. It showcases an architecture that replaces manual, error-prone access reviews (often done in Excel) with a systematic, API-driven detection engine.

### 🌐 [Live Demo →](https://bank-iam-dashboard.vercel.app/)

## Regulatory Context

The core detection rules in this engine are mapped to real-world financial compliance standards:

- **RBI IT Framework for Banks (2011, amended 2023)**:
  - **§3.2 (Segregation of Duties - SoD)**: Enforces that conflicting roles (e.g., Maker and Checker, or Developer and Production Support) are not held by the same user.
  - **§5.1 (User Access Management)**: Mandates timely revocation of access for terminated employees and periodic access reviews.
- **ISO 27001:2022 Annex A.9 (Access Control)**:
  - **A.9.2.3**: Review of user access rights.
  - **A.9.2.5 & A.9.2.6**: Removal or adjustment of access rights upon termination or role change.
  - **A.9.4.1**: Information access restriction.

## What Problem This Solves

In many organizations, especially heavily regulated ones like banks, "access creep" is a major security risk. Employees accumulate permissions over years as they change roles, but old access is rarely revoked. Furthermore, terminated employees often retain access to legacy or siloed systems due to poor offboarding processes. This leads to audit failures, insider threats, and SoD conflicts. This tool automates the discovery of these critical security blind spots.

## Features

- **Modern Dark UI**: A premium, sleek "Banking Dark" aesthetic with high-contrast compliance indicators and smooth transitions.
- **SoD Conflict Detection**: Automatically identifies users holding mutually exclusive roles across multiple systems, complete with regulatory citations.
- **Orphan Account Detection**: Flags active accounts that belong to suspended, terminated, or non-existent employees.
- **Privilege Analysis**: Identifies over-privileged users who hold high-risk administrative access without recent activity.
- **RBAC Consolidation Recommendations**: Analyzes direct role assignments and suggests consolidating them into standardized business roles.
- **Audit Reporting**: Generates downloadable, compliance-ready PDF access certification reports.

## Tech Stack

- **Backend**: Python 3.11, Flask, SQLAlchemy, SQLite, ReportLab.
- **Frontend**: React 18, Vite, Tailwind CSS (Dark Mode), TanStack Query, React Router.
- **Deployment**: Render (Backend), Vercel (Frontend).

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── engine/          # Detection algorithms & report generation
│   │   ├── models.py        # Database schema (IAM domain model)
│   │   ├── routes.py        # REST API endpoints
│   │   └── seeder.py        # Mock banking data generator
│   ├── run.py               # Flask entry point
│   ├── render.yaml          # Infrastructure-as-Code blueprint
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── api/             # API client & Query hooks
│   │   ├── components/      # UI components (Layouts, Tables, Charts)
│   │   ├── pages/           # Dashboard, Violations, RBAC, Users, Report
│   │   └── utils/           # Styling & formatting utilities
│   ├── tailwind.config.js   # Custom dark-theme design tokens
│   └── package.json         # Node dependencies
└── README.md
```

## Local Development

Follow these steps to run the application locally:

### 1. Clone the repository
```bash
git clone <repository_url>
cd bank-iam-dashboard
```

### 2. Backend Setup
Open a terminal and run the following:
```bash
cd backend
python -m venv venv

# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python run.py
```
*Note: The backend runs on `http://localhost:5000` and will auto-seed the SQLite database with mock banking data on startup.*

### 3. Frontend Setup
Open a second terminal and run the following:
```bash
cd frontend
npm install
```

### 4. Configure Frontend Environment
Create a `.env` file in the `frontend` directory and set the local API URL:
```env
VITE_API_URL=http://localhost:5000
```
Then start the development server:
```bash
npm run dev
```

## Deployment

The application is designed for zero-cost deployment using Render and Vercel.

### Step 1: Push to GitHub
Ensure both `backend` and `frontend` folders are pushed to your GitHub repository.

### Step 2: Deploy Backend to Render
1. Create an account on [Render](https://render.com/).
2. Click **New +** and select **Web Service**.
3. Connect your GitHub repository.
4. Render can automatically deploy using the provided `backend/render.yaml` blueprint. If deploying manually:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn run:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`
   - Add Environment Variables:
     - `PYTHON_VERSION`: `3.11.0`
     - `FLASK_ENV`: `production`

> **IMPORTANT RENDER FREE TIER NOTE:**
> Render's free tier web services automatically spin down after 15 minutes of inactivity. The first request after a cold start will take ~30-50 seconds as Render provisions the instance. The frontend includes a "warmup" function that hits the `/api/health` endpoint on load to wake up the backend and display a loading banner to the user.

### Step 3: Deploy Frontend to Vercel
1. Create an account on [Vercel](https://vercel.com/).
2. Click **Add New Project** and import your GitHub repository.
3. Configure the Project:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Environment Variables**: Add `VITE_API_URL` and set it to your Render backend URL (e.g., `https://your-app.onrender.com`).
4. Click **Deploy**.

### Step 4: Secure Backend CORS
Once your frontend is deployed, go back to your Render dashboard for the backend service and add a new Environment Variable:
- `FRONTEND_URL`: `https://your-vercel-app-url.vercel.app`
This ensures the backend only accepts API requests from your specific Vercel frontend.

## Disclaimer

This application uses entirely mock data. It is not connected to any real banking system, CBS (Core Banking System), or Active Directory environment. It is intended solely for demonstration and portfolio purposes.
