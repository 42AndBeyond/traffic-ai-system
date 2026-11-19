import os
import json
import numpy as np
import pandas as pd
import networkx as nx
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
import joblib

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
RISK_MODEL_PATH = os.path.join(MODEL_DIR, "accident_risk_model.joblib")
CONG_MODEL_PATH = os.path.join(MODEL_DIR, "congestion_model.joblib")

WEATHER_MAP = {"Clear": 0, "Haze": 1, "Fog": 2, "Rain": 3}
ROAD_MAP = {"Collector": 0, "Arterial": 1, "Ring Road": 2, "Junction": 3, "Highway": 4}
VEHICLE_MAP = {"Car": 0, "Auto/Bus": 1, "Two-Wheeler": 2, "Heavy Truck": 3}


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["hour"] = df["hour"].astype(int).clip(0, 23)
    out["day_of_week"] = df["day_of_week"].astype(int).clip(0, 6)
    out["is_weekend"] = (out["day_of_week"] >= 5).astype(int)
    out["is_rush_hour"] = out["hour"].isin([8, 9, 10, 17, 18, 19, 20]).astype(int)
    out["is_night"] = ((out["hour"] >= 22) | (out["hour"] <= 4)).astype(int)
    out["weather_code"] = df["weather"].map(WEATHER_MAP).fillna(0).astype(int)
    out["road_code"] = df["road_type"].map(ROAD_MAP).fillna(1).astype(int)
    out["vehicle_code"] = df["vehicle_type"].map(VEHICLE_MAP).fillna(2).astype(int)
    out["traffic_volume"] = df["traffic_volume"].astype(float).clip(10, 5000)
    return out


def train_and_save_models():
    os.makedirs(MODEL_DIR, exist_ok=True)
    rng = np.random.default_rng(42)
    n = 2500

    hours = rng.integers(0, 24, size=n)
    dows = rng.integers(0, 7, size=n)
    weathers = rng.choice(["Clear", "Haze", "Fog", "Rain"], size=n, p=[0.55, 0.15, 0.12, 0.18])
    roads = rng.choice(["Collector", "Arterial", "Ring Road", "Junction", "Highway"], size=n)
    vehicles = rng.choice(["Car", "Auto/Bus", "Two-Wheeler", "Heavy Truck"], size=n, p=[0.25, 0.2, 0.35, 0.2])

    rush = np.isin(hours, [8, 9, 10, 17, 18, 19, 20]).astype(float)
    night = ((hours >= 22) | (hours <= 4)).astype(float)
    w_mult = np.where(np.isin(weathers, ["Rain", "Fog"]), 1.45, 1.0)
    r_mult = np.where(np.isin(roads, ["Highway", "Junction"]), 1.35, 1.0)
    v_mult = np.where(np.isin(vehicles, ["Two-Wheeler", "Heavy Truck"]), 1.2, 1.0)

    congestion_idx = np.clip(
        22.0 + rush * 42.0 + np.where(weathers == "Rain", 14.0, 0.0) + rng.normal(0, 7.5, size=n),
        5.0,
        100.0,
    )
    traffic_vol = np.clip(congestion_idx * 18.0 + rng.normal(0, 90, size=n), 80, 2500)

    risk_prob = np.clip(
        0.18 + 0.25 * rush + 0.18 * night + 0.0002 * traffic_vol,
        0.05,
        0.95,
    ) * (0.65 * w_mult * r_mult * v_mult)
    high_risk = (rng.random(size=n) < np.clip(risk_prob, 0.02, 0.95)).astype(int)

    raw_df = pd.DataFrame({
        "hour": hours,
        "day_of_week": dows,
        "weather": weathers,
        "road_type": roads,
        "vehicle_type": vehicles,
        "traffic_volume": traffic_vol,
    })
    X = _build_features(raw_df)

    risk_clf = RandomForestClassifier(n_estimators=80, max_depth=8, random_state=42)
    risk_clf.fit(X, high_risk)

    cong_reg = RandomForestRegressor(n_estimators=80, max_depth=8, random_state=42)
    cong_reg.fit(X, congestion_idx)

    joblib.dump(risk_clf, RISK_MODEL_PATH)
    joblib.dump(cong_reg, CONG_MODEL_PATH)
    return risk_clf, cong_reg


def load_models():
    if not os.path.exists(RISK_MODEL_PATH) or not os.path.exists(CONG_MODEL_PATH):
        return train_and_save_models()
    return joblib.load(RISK_MODEL_PATH), joblib.load(CONG_MODEL_PATH)


def predict_condition(hour: int, day_of_week: int, weather: str, road_type: str, vehicle_type: str, traffic_volume: int):
    risk_clf, cong_reg = load_models()
    df = pd.DataFrame([{
        "hour": hour,
        "day_of_week": day_of_week,
        "weather": weather,
        "road_type": road_type,
        "vehicle_type": vehicle_type,
        "traffic_volume": traffic_volume,
    }])
    X = _build_features(df)
    risk_score = float(risk_clf.predict_proba(X)[0][1])
    congestion_score = float(np.clip(cong_reg.predict(X)[0], 0.0, 100.0))

    if risk_score >= 0.65:
        risk_level = "High"
    elif risk_score >= 0.40:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    if congestion_score >= 70:
        cong_level = "Heavy"
    elif congestion_score >= 40:
        cong_level = "Moderate"
    else:
        cong_level = "Smooth"

    factors = []
    if hour in (8, 9, 10, 17, 18, 19, 20):
        factors.append("Peak rush-hour flow")
    if (hour >= 22) or (hour <= 4):
        factors.append("Low-light night visibility")
    if weather in ("Rain", "Fog"):
        factors.append(f"Adverse weather ({weather})")
    if road_type in ("Highway", "Junction"):
        factors.append(f"{road_type} conflict zone")
    if vehicle_type in ("Two-Wheeler", "Heavy Truck"):
        factors.append(f"{vehicle_type} stability/blind-spot exposure")
    if not factors:
        factors.append("Baseline traffic & clear road conditions")

    return {
        "accident_risk_score": round(risk_score, 3),
        "risk_level": risk_level,
        "congestion_index": round(congestion_score, 1),
        "congestion_level": cong_level,
        "key_factors": factors,
    }


def compute_routes(road_edges, source: str, destination: str, hour: int, weather: str, vehicle_type: str):
    g_fast = nx.DiGraph()
    g_safe = nx.DiGraph()

    weather_mult = 1.35 if weather in ("Rain", "Fog") else 1.0
    veh_mult = 1.20 if vehicle_type == "Two-Wheeler" else (1.15 if vehicle_type == "Heavy Truck" else 1.0)
    rush_mult = 1.25 if hour in (8, 9, 10, 17, 18, 19) else 1.0

    edge_lookup = {}
    for e in road_edges:
        pts = json.loads(e.waypoints_json)
        seg_risk = min(0.98, round(e.base_risk * weather_mult * veh_mult * rush_mult, 3))
        # Penalty cost combines distance and accident risk
        safety_cost = e.distance_km * (1.0 + seg_risk * 3.2)

        for u, v, path_pts in [(e.source_junction, e.target_junction, pts), (e.target_junction, e.source_junction, list(reversed(pts)))]:
            g_fast.add_edge(u, v, weight=e.distance_km)
            g_safe.add_edge(u, v, weight=safety_cost)
            edge_lookup[(u, v)] = {
                "from": u,
                "to": v,
                "distance_km": e.distance_km,
                "risk_score": seg_risk,
                "road_type": e.road_type,
                "coordinates": path_pts,
            }

    if source == destination or source not in g_fast or destination not in g_fast:
        return None

    def _summarize_path(nodes):
        segments = []
        total_km = 0.0
        weighted_risk_sum = 0.0
        full_coords = []
        for idx in range(len(nodes) - 1):
            seg = edge_lookup[(nodes[idx], nodes[idx + 1])]
            segments.append(seg)
            total_km += seg["distance_km"]
            weighted_risk_sum += seg["risk_score"] * seg["distance_km"]
            coords = seg["coordinates"] if idx == 0 else seg["coordinates"][1:]
            full_coords.extend(coords)
        avg_risk = round(weighted_risk_sum / total_km, 3) if total_km > 0 else 0.0
        est_mins = round((total_km / (24.0 if rush_mult > 1.0 else 36.0)) * 60.0, 1)
        return {
            "path": nodes,
            "distance_km": round(total_km, 2),
            "est_minutes": est_mins,
            "avg_risk_score": avg_risk,
            "coordinates": full_coords,
            "segments": segments,
        }

    fast_nodes = nx.shortest_path(g_fast, source=source, target=destination, weight="weight")
    safe_nodes = nx.shortest_path(g_safe, source=source, target=destination, weight="weight")

    return {
        "fastest": _summarize_path(fast_nodes),
        "safest": _summarize_path(safe_nodes),
    }