# PathWise — AI-Powered Traffic Intelligence & Accident Risk Prediction

**Don't just find the fastest route. Find the safer one.**

PathWise is an AI-powered traffic intelligence platform built around the Hanamkonda–Kazipet–Warangal road network. It combines machine learning, route optimization, traffic analytics, and interactive mapping to assess congestion and accident risk before a journey begins.

- **Live Web Application:** [PathWise Web App](https://path-wise-app.onrender.com/)
- **Backend API Documentation:** [PathWise API Docs](https://path-wise.onrender.com/docs)

---

## Overview

Traditional navigation applications focus primarily on reaching a destination quickly. PathWise evaluates traffic conditions, weather, vehicle type, historical incident records, and road network structure to recommend safer routes for commuters while giving traffic authorities analytical tools to monitor hotspots and simulate risk scenarios.

---

## Key Features

### Driver / Commuter View
- **Route Optimization:** Compares fastest and safer route options across 10 major junctions.
- **Risk Scoring:** Evaluates accident risk based on weather conditions and vehicle type.
- **Interactive Map:** Displays recommended routes and junction markers using Leaflet and OpenStreetMap.

### Traffic Police / Authority View
- **Station Analytics:** Displays isolated incident logs, high-severity breakdowns, and average traffic volume.
- **Hotspot & Pattern Analysis:** Maps accident-prone junctions and visualizes hourly traffic and incident trends.
- **ML Risk Simulator:** Runs what-if scenarios across different hours, weather conditions, road types, and vehicles alongside predictive enforcement recommendations.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript, Leaflet (OpenStreetMap) |
| Backend | Python, FastAPI, Uvicorn |
| Database | SQLite |
| Machine Learning | Scikit-learn, Pandas, NumPy |
| Authentication | JWT, Role-Based Access Control |
| Deployment | Render |

---

## System Architecture

```text
User -> React Frontend (Vite) -> FastAPI Backend -> ML Engine & Auth -> SQLite Database
```

### Core Backend Modules
- `backend/main.py` — FastAPI server, JWT authentication, and REST endpoints (`/auth/register`, `/auth/login`, `/junctions`, `/routes/optimize`, `/analytics/overview`, `/predict`).
- `backend/ml_engine.py` — Machine learning models for congestion and accident risk prediction.
- `backend/database.py` — SQLite database setup and data operations.

---

## Local Setup

### Prerequisites
- Python 3.10+
- Node.js and npm
- Git

### 1. Clone the Repository
```bash
git clone https://github.com
cd traffic-ai-system
```

### 2. Start the Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```
Backend runs at `http://localhost:8000` (API docs at `http://localhost:8000/docs`).

### 3. Start the Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at `http://localhost:5173`.

---

## Quick Demo Guide

- **Driver Demo:** Register as a **Driver / Commuter**, select a route (such as `NIT Gate / Fatimanagar` to `MGM Hospital Junction`), choose `Rain` and `Two-Wheeler`, and compare the suggested routes and risk scores.
- **Authority Demo:** Register as a **Traffic Police / Authority** user (such as `Subedari Traffic PS`) to view station analytics, accident hotspots, hourly charts, and the ML risk simulator.

---

## Scope & Limitations

- **Current Coverage:** Covers 10 major junctions across Hanamkonda, Kazipet, and Warangal in Telangana, India.
- **Future Scope:** Multi-city road network integration, live GPS traffic feeds, and automated incident alerts.
- **Hosting Note:** Deployed on Render's free tier; the first request after inactivity may take up to 50 seconds to wake up.
