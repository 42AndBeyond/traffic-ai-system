# PathWise — AI Smart Traffic & Accident Prediction System

**Don't just find the fastest route. Find the safer one.**

A full-stack FastAPI and React web platform that predicts traffic congestion and accident risk, and optimizes safer routes across the Hanamkonda–Kazipet–Warangal road network.

- **Live Web App:** https://path-wise-app.onrender.com/ 
- **Live API Docs:** https://path-wise.onrender.com/docs 
- **Interactive Architecture Diagram:** https://gitdiagram.com 
- **Interactive Code Documentation:** https://deepwiki.com 

## Features

| Driver / Commuter View | Traffic Police / Authority View |
| :--- | :--- |
| **Safe vs. Fastest Route Finder:** Compares routes across 10 junctions by distance, time, and risk | **Station-Isolated Analytics:** Tracks logged incidents, severe crashes, and average traffic volume |
| **Context-Aware Risk Scoring:** Adjusts risk dynamically for weather conditions and vehicle type | **Hotspot & Hourly Charts:** Maps accident blackspots and visualizes 24-hour incident peaks |
| **Interactive Route Map:** Highlights safest paths and junction markers on Leaflet / OpenStreetMap | **ML Risk Simulator:** Runs "what-if" scenarios with targeted enforcement recommendations |

---

## Tech Stack

- **Frontend:** React, Vite, JavaScript, Leaflet (OpenStreetMap)
- **Backend:** Python, FastAPI, Uvicorn, JWT Authentication
- **Machine Learning & Data:** Scikit-learn, Pandas, NumPy, SQLite
- **Deployment:** Render (Static Site + Web Service)

---

## System Architecture

```text
User -> React Frontend (Vite) -> FastAPI Backend -> ML Engine & Auth -> SQLite Database
```

### How it works

- `backend/main.py` — Runs the FastAPI server, JWT role-based authentication, and REST endpoints (`/auth`, `/junctions`, `/routes/optimize`, `/analytics/overview`, `/predict`).
- `backend/ml_engine.py` — Trains and runs the machine learning models to score accident risk and congestion levels.
- `backend/database.py` — Manages the SQLite database (`traffic_system.db`) storing junctions, road edges, historical records, and station accounts.
- `frontend/src/App.jsx` — Renders the role-based React dashboard, Leaflet maps, and analytics charts.

---

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

---

## Demo Tips

- **Driver View:** Create a `Driver / Commuter` account, pick two junctions (such as `NIT Gate / Fatimanagar` to `MGM Hospital Junction`), switch weather to `Rain` and vehicle to `Two-Wheeler`, and compare risk scores.
- **Police Authority View:** Create a `Traffic Police / Authority` account (e.g., `Subedari Traffic PS`) to unlock the **Authority & Analytics** tab, hotspot map, and ML simulator.
- **API Testing:** Visit `/docs` on the backend URL to test endpoints directly in Swagger UI.

---

## Scope & Limitations

- **Current Coverage:** Covers 10 major junctions across Hanamkonda, Kazipet, and Warangal in Telangana, India.
- **Future Scope:** Multi-city road network integration, live GPS traffic feeds, and automated incident alerts.
- **Hosting Note:** Deployed on Render's free tier; the first request after inactivity may take up to 50 seconds to wake up.
 
## Project Links 
- LinkedIn Demo Video: https://lnkd.in/p/d4796gSQ 
