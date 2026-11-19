# PathWise — AI Smart Traffic & Accident Prediction System

A full-stack FastAPI and React web dashboard that predicts traffic congestion and accident risk, and optimizes safer routes across the Hanamkonda–Kazipet–Warangal road network.

- **Live Web App:** hhttps://path-wise-app.onrender.com/
- **Live API Docs:** https://path-wise.onrender.com/docs

## Features

- Role-based authentication separating **Driver / Commuter** accounts from **Traffic Police / Authority** accounts
- Safe vs. fastest route optimization based on start/destination junctions, weather conditions, and vehicle type
- Interactive Leaflet / OpenStreetMap view showing safest route paths and accident hotspot markers
- Station-isolated analytics dashboard with logged incident counts, high-severity breakdowns, and average traffic volume
- Hourly traffic and incident pattern charts, predictive enforcement decision support, and an ML "what-if" risk simulator
- Dark UI with clear visual risk indicators

## Setup (VS Code / Windows)

1. Open the `traffic-ai-system` folder in VS Code.
2. Open a terminal and start the backend server:

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

3. Open a second terminal and start the frontend app:

```bash
cd frontend
npm install
npm run dev
```

4. Open http://localhost:5173 in your browser.

## How it works

- `backend/main.py` runs the FastAPI server, JWT authentication, and REST endpoints (`/auth`, `/junctions`, `/routes/optimize`, `/analytics/overview`, `/predict`).
- `backend/ml_engine.py` trains and runs the machine learning models to score accident risk and congestion levels.
- `backend/database.py` manages the SQLite database (`traffic_system.db`) storing junctions, road edges, historical records, and station accounts.
- `frontend/src/App.jsx` renders the role-based React dashboard, Leaflet maps, and analytics charts.

## Demo tips

- **Driver View:** Create a `Driver / Commuter` account, pick two junctions (such as `NIT Gate / Fatimanagar` to `MGM Hospital Junction`), switch weather to `Rain` and vehicle to `Two-Wheeler`, and compare risk scores.
- **Police Authority View:** Create a `Traffic Police / Authority` account (e.g., `Subedari Traffic PS`) to unlock the **Authority & Analytics** tab, hotspot map, and ML simulator.
- **API Testing:** Visit `/docs` on the backend URL to test endpoints directly in Swagger UI.

## Notes

- Hosted on Render's free tier; if inactive, the backend may take ~50 seconds to wake up on the first login or request.
- The current road network covers 10 major junctions across Hanamkonda, Kazipet, and Warangal.
- Live multi-city geocoding and real-time GPS traffic feeds can be added as future upgrades.
