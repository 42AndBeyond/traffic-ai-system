import os
import io
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List

import bcrypt
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import (
    SessionLocal,
    init_db,
    Organization,
    User,
    AccidentRecord,
    RoadEdge,
    JUNCTIONS,
)
from ml_engine import predict_condition, compute_routes

SECRET_KEY = os.getenv("JWT_SECRET", "lab-traffic-ai-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 240

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

app = FastAPI(title="Smart Traffic Monitoring & Accident Prediction API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://path-wise-app.onrender.com",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def hash_password(plain: str) -> str:
    # Pre-hash with SHA-256 so bcrypt 72-byte limit never causes an error
    digest = hashlib.sha256(plain.encode("utf-8")).hexdigest().encode("utf-8")
    return bcrypt.hashpw(digest, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    digest = hashlib.sha256(plain.encode("utf-8")).hexdigest().encode("utf-8")
    return bcrypt.checkpw(digest, hashed.encode("utf-8"))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    init_db(hash_password)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "authority"
    station_name: Optional[str] = None
    station_code: Optional[str] = None
    city: Optional[str] = "Hanamkonda"


class PredictionRequest(BaseModel):
    junction: str = "Nakkalagutta X Road"
    hour: int = 18
    day_of_week: int = 4
    weather: str = "Rain"
    road_type: str = "Junction"
    vehicle_type: str = "Two-Wheeler"
    traffic_volume: int = 950


class RouteRequest(BaseModel):
    source: str
    destination: str
    hour: int = 18
    weather: str = "Clear"
    vehicle_type: str = "Two-Wheeler"


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/auth/register")
def register_user(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    role = req.role if req.role in ("authority", "driver") else "authority"
    org_id = None

    if role == "authority":
        org_name = req.station_name or f"{req.username} Traffic PS"
        if db.query(Organization).filter(Organization.name == org_name).first():
            org_name = f"{org_name} ({req.username})"
        org = Organization(
            name=org_name,
            station_code=req.station_code or f"PS-{abs(hash(req.username)) % 900 + 100}",
            city=req.city or "Hanamkonda",
            state="Telangana",
            active_dataset_label="Default Baseline Dataset",
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        org_id = org.id

        # Seed baseline records from Hanamkonda PS so a new station has immediate analytics
        seed_source = db.query(AccidentRecord).filter(AccidentRecord.org_id == 1).limit(150).all()
        for r in seed_source:
            db.add(AccidentRecord(
                org_id=org.id,
                dataset_label=org.active_dataset_label,
                junction=r.junction,
                lat=r.lat,
                lon=r.lon,
                hour=r.hour,
                day_of_week=r.day_of_week,
                weather=r.weather,
                road_type=r.road_type,
                vehicle_type=r.vehicle_type,
                traffic_volume=r.traffic_volume,
                severity=r.severity,
            ))
        db.commit()

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        role=role,
        org_id=org_id,
    )
    db.add(user)
    db.commit()
    return {"message": "Account created", "username": user.username, "role": user.role}


@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    org = db.query(Organization).filter(Organization.id == user.org_id).first() if user.org_id else None
    token = create_access_token({"sub": user.username, "role": user.role, "org_id": user.org_id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role,
        "org_id": user.org_id,
        "station_name": org.name if org else "Driver Portal",
        "active_dataset": org.active_dataset_label if org else None,
    }


@app.post("/datasets/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    dataset_name: str = Query("Uploaded Station CSV"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "authority" or not current_user.org_id:
        raise HTTPException(status_code=403, detail="Only authority accounts can upload station datasets")

    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV file")

    # Flexible column alias mapping
    rename_map = {}
    for col in df.columns:
        c = col.strip().lower()
        if c in ("junction", "location", "spot", "intersection"):
            rename_map[col] = "junction"
        elif c in ("lat", "latitude"):
            rename_map[col] = "lat"
        elif c in ("lon", "lng", "longitude"):
            rename_map[col] = "lon"
        elif c in ("hour", "hr"):
            rename_map[col] = "hour"
        elif c in ("day_of_week", "dow", "weekday", "day"):
            rename_map[col] = "day_of_week"
        elif c in ("weather", "condition"):
            rename_map[col] = "weather"
        elif c in ("road_type", "road"):
            rename_map[col] = "road_type"
        elif c in ("vehicle_type", "vehicle"):
            rename_map[col] = "vehicle_type"
        elif c in ("traffic_volume", "volume", "count"):
            rename_map[col] = "traffic_volume"
        elif c in ("severity", "risk_severity", "level"):
            rename_map[col] = "severity"

    df = df.rename(columns=rename_map)
    if "junction" not in df.columns:
        raise HTTPException(status_code=400, detail="CSV must include a 'junction' (or 'location') column")

    new_records = []
    for idx, row in df.iterrows():
        j_name = str(row.get("junction", "Hanamkonda Chowrasta")).strip()
        base_lat, base_lon = JUNCTIONS.get(j_name, JUNCTIONS["Hanamkonda Chowrasta"])
        lat = float(row["lat"]) if "lat" in df.columns and pd.notna(row["lat"]) else base_lat
        lon = float(row["lon"]) if "lon" in df.columns and pd.notna(row["lon"]) else base_lon
        hour = int(row["hour"]) if "hour" in df.columns and pd.notna(row["hour"]) else 18
        dow = int(row["day_of_week"]) if "day_of_week" in df.columns and pd.notna(row["day_of_week"]) else 4
        weather = str(row["weather"]) if "weather" in df.columns and pd.notna(row["weather"]) else "Clear"
        road_type = str(row["road_type"]) if "road_type" in df.columns and pd.notna(row["road_type"]) else "Arterial"
        vehicle_type = str(row["vehicle_type"]) if "vehicle_type" in df.columns and pd.notna(row["vehicle_type"]) else "Two-Wheeler"
        vol = int(row["traffic_volume"]) if "traffic_volume" in df.columns and pd.notna(row["traffic_volume"]) else 650
        sev = int(row["severity"]) if "severity" in df.columns and pd.notna(row["severity"]) else 2

        new_records.append(AccidentRecord(
            org_id=current_user.org_id,
            dataset_label=dataset_name,
            junction=j_name,
            lat=lat,
            lon=lon,
            hour=max(0, min(23, hour)),
            day_of_week=max(0, min(6, dow)),
            weather=weather,
            road_type=road_type,
            vehicle_type=vehicle_type,
            traffic_volume=max(10, vol),
            severity=max(1, min(3, sev)),
        ))

    if not new_records:
        raise HTTPException(status_code=400, detail="CSV contained no valid rows")

    # Replace previous records for this org_id so the uploaded dataset becomes active
    db.query(AccidentRecord).filter(AccidentRecord.org_id == current_user.org_id).delete()
    db.add_all(new_records)
    org = db.query(Organization).filter(Organization.id == current_user.org_id).first()
    if org:
        org.active_dataset_label = dataset_name
    db.commit()

    return {
        "message": "Dataset uploaded and isolated to your station",
        "dataset_label": dataset_name,
        "records_loaded": len(new_records),
    }


@app.get("/analytics/overview")
def analytics_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_org_id = current_user.org_id if current_user.org_id else 1
    org = db.query(Organization).filter(Organization.id == target_org_id).first()
    records = db.query(AccidentRecord).filter(AccidentRecord.org_id == target_org_id).all()

    total = len(records)
    high_sev = sum(1 for r in records if r.severity == 3)
    avg_vol = round(sum(r.traffic_volume for r in records) / total, 1) if total else 0.0

    by_junction = {}
    by_hour = {h: 0 for h in range(24)}
    points = []

    for r in records:
        by_junction[r.junction] = by_junction.get(r.junction, 0) + 1
        by_hour[r.hour] = by_hour.get(r.hour, 0) + 1
        if len(points) < 250:
            points.append({
                "id": r.id,
                "junction": r.junction,
                "lat": r.lat,
                "lon": r.lon,
                "hour": r.hour,
                "weather": r.weather,
                "vehicle_type": r.vehicle_type,
                "severity": r.severity,
                "traffic_volume": r.traffic_volume,
            })

    hotspots = [
        {"junction": k, "incidents": v, "coords": list(JUNCTIONS.get(k, (17.99, 79.57)))}
        for k, v in sorted(by_junction.items(), key=lambda x: x[1], reverse=True)
    ]

    recommendations = []
    for hs in hotspots[:3]:
        spot = hs["junction"]
        inc = hs["incidents"]
        if inc >= 60:
            action = f"Deploy PCR/traffic patrol & extend green signal phase at {spot}; issue wet/peak-hour speed advisory."
            priority = "High"
        elif inc >= 25:
            action = f"Position dynamic warning signage and monitor two-wheeler lane discipline near {spot}."
            priority = "Medium"
        else:
            action = f"Maintain routine camera/beat surveillance around {spot}."
            priority = "Normal"
        recommendations.append({"junction": spot, "incidents": inc, "priority": priority, "action": action})

    hourly_series = [{"hour": f"{h:02d}:00", "incidents": by_hour[h]} for h in range(24)]

    return {
        "org_id": target_org_id,
        "station_name": org.name if org else "Demo Station",
        "active_dataset": org.active_dataset_label if org else "Demo v1",
        "total_records": total,
        "high_severity_count": high_sev,
        "avg_traffic_volume": avg_vol,
        "hotspots": hotspots,
        "hourly_series": hourly_series,
        "recommendations": recommendations,
        "map_points": points,
    }


@app.post("/predict")
def predict_endpoint(req: PredictionRequest):
    return predict_condition(
        hour=req.hour,
        day_of_week=req.day_of_week,
        weather=req.weather,
        road_type=req.road_type,
        vehicle_type=req.vehicle_type,
        traffic_volume=req.traffic_volume,
    )


@app.get("/junctions")
def get_junctions(db: Session = Depends(get_db)):
    edges = db.query(RoadEdge).all()
    edge_list = [
        {
            "source": e.source_junction,
            "target": e.target_junction,
            "distance_km": e.distance_km,
            "base_risk": e.base_risk,
            "road_type": e.road_type,
        }
        for e in edges
    ]
    return {
        "junctions": [{"name": name, "lat": lat, "lon": lon} for name, (lat, lon) in JUNCTIONS.items()],
        "edges": edge_list,
    }


@app.post("/routes/optimize")
def optimize_routes(req: RouteRequest, db: Session = Depends(get_db)):
    edges = db.query(RoadEdge).all()
    result = compute_routes(
        road_edges=edges,
        source=req.source,
        destination=req.destination,
        hour=req.hour,
        weather=req.weather,
        vehicle_type=req.vehicle_type,
    )
    if not result:
        raise HTTPException(status_code=400, detail="Select two distinct valid junctions")
    return result