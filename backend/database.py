import json
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = "sqlite:///./traffic_system.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    station_code = Column(String, nullable=False)
    city = Column(String, default="Hanamkonda / Warangal")
    state = Column(String, default="Telangana")
    active_dataset_label = Column(String, default="Synthetic Demo Dataset v1")

    users = relationship("User", back_populates="organization")
    accidents = relationship("AccidentRecord", back_populates="organization")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="authority")  # "authority" or "driver"
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)

    organization = relationship("Organization", back_populates="users")


class AccidentRecord(Base):
    __tablename__ = "accident_records"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True, nullable=False)
    dataset_label = Column(String, default="Synthetic Demo Dataset v1")
    junction = Column(String, index=True, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    hour = Column(Integer, nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Mon .. 6=Sun
    weather = Column(String, default="Clear")
    road_type = Column(String, default="Arterial")
    vehicle_type = Column(String, default="Two-Wheeler")
    traffic_volume = Column(Integer, default=500)
    severity = Column(Integer, default=1)  # 1=Low, 2=Medium, 3=High
    timestamp = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="accidents")


class RoadEdge(Base):
    __tablename__ = "road_edges"
    id = Column(Integer, primary_key=True, index=True)
    source_junction = Column(String, nullable=False)
    target_junction = Column(String, nullable=False)
    distance_km = Column(Float, nullable=False)
    base_risk = Column(Float, default=0.3)
    road_type = Column(String, default="Arterial")
    waypoints_json = Column(Text, nullable=False)  # JSON list of [lat, lon] pairs


JUNCTIONS = {
    "Hanamkonda Chowrasta": (18.0072, 79.5584),
    "Subedari Junction": (17.9921, 79.5523),
    "Nakkalagutta X Road": (17.9815, 79.5632),
    "Kazipet X Road": (18.0156, 79.5289),
    "NIT Gate / Fatimanagar": (18.0018, 79.5356),
    "MGM Hospital Junction": (17.9778, 79.5892),
    "Warangal Station Road": (17.9689, 79.6012),
    "Mulugu X Road": (17.9954, 79.5915),
    "Hunter Road Junction": (17.9862, 79.5754),
    "Bala Samudram / Fort Road": (17.9642, 79.5810),
}

# (source, target, distance_km, base_risk, road_type)
ROAD_LINKS = [
    ("Kazipet X Road", "NIT Gate / Fatimanagar", 2.4, 0.42, "Highway"),
    ("NIT Gate / Fatimanagar", "Hanamkonda Chowrasta", 2.6, 0.55, "Arterial"),
    ("Hanamkonda Chowrasta", "Subedari Junction", 2.1, 0.48, "Arterial"),
    ("Subedari Junction", "Nakkalagutta X Road", 2.2, 0.58, "Junction"),
    ("Nakkalagutta X Road", "Hunter Road Junction", 2.0, 0.45, "Arterial"),
    ("Hunter Road Junction", "Mulugu X Road", 2.3, 0.62, "Junction"),
    ("Mulugu X Road", "MGM Hospital Junction", 2.5, 0.54, "Arterial"),
    ("MGM Hospital Junction", "Warangal Station Road", 1.8, 0.60, "Junction"),
    ("Nakkalagutta X Road", "Bala Samudram / Fort Road", 2.7, 0.36, "Collector"),
    ("Bala Samudram / Fort Road", "Warangal Station Road", 2.4, 0.34, "Collector"),
    ("Subedari Junction", "Hunter Road Junction", 2.9, 0.39, "Collector"),
    ("Hanamkonda Chowrasta", "Mulugu X Road", 4.2, 0.44, "Ring Road"),
]


def _interpolate_path(p1, p2, steps=5, rng=None):
    rng = rng or random
    lat1, lon1 = p1
    lat2, lon2 = p2
    pts = []
    for i in range(steps + 1):
        t = i / steps
        jitter_lat = rng.uniform(-0.0012, 0.0012) if 0 < i < steps else 0.0
        jitter_lon = rng.uniform(-0.0012, 0.0012) if 0 < i < steps else 0.0
        pts.append([round(lat1 + t * (lat2 - lat1) + jitter_lat, 6), round(lon1 + t * (lon2 - lon1) + jitter_lon, 6)])
    return pts


def generate_synthetic_rows(org_id: int, dataset_label: str, count: int = 800, seed: int = 42):
    rng = random.Random(seed + org_id)
    weathers = ["Clear", "Clear", "Clear", "Rain", "Fog", "Haze"]
    vehicles = ["Two-Wheeler", "Two-Wheeler", "Car", "Auto/Bus", "Heavy Truck"]
    high_risk_spots = ["Nakkalagutta X Road", "Mulugu X Road", "Warangal Station Road", "Hanamkonda Chowrasta"]
    junction_names = list(JUNCTIONS.keys())

    rows = []
    now = datetime.utcnow()
    for i in range(count):
        j_name = rng.choice(high_risk_spots) if rng.random() < 0.52 else rng.choice(junction_names)
        base_lat, base_lon = JUNCTIONS[j_name]
        hour = rng.choices(range(24), weights=[
            1, 1, 1, 1, 1, 2, 4, 7, 9, 8, 5, 5,
            6, 5, 5, 6, 8, 10, 10, 8, 6, 4, 2, 1
        ])[0]
        dow = rng.randint(0, 6)
        weather = rng.choice(weathers)
        v_type = rng.choice(vehicles)
        road_type = "Highway" if "Kazipet" in j_name else ("Junction" if "Road" in j_name or "Junction" in j_name else "Arterial")

        rush_boost = 1.6 if hour in (8, 9, 10, 17, 18, 19) else (1.3 if hour in (22, 23, 0, 1, 4) else 0.9)
        weather_boost = 1.65 if weather in ("Rain", "Fog") else 1.0
        spot_boost = 1.45 if j_name in high_risk_spots else 0.95
        vehicle_boost = 1.25 if v_type in ("Two-Wheeler", "Heavy Truck") else 1.0

        score = 0.25 * rush_boost * weather_boost * spot_boost * vehicle_boost + rng.uniform(-0.08, 0.12)
        severity = 3 if score >= 0.68 else (2 if score >= 0.42 else 1)
        traffic_volume = int(min(2400, max(120, (350 if road_type == "Highway" else 550) * rush_boost + rng.randint(-90, 140))))

        rows.append(
            AccidentRecord(
                org_id=org_id,
                dataset_label=dataset_label,
                junction=j_name,
                lat=round(base_lat + rng.uniform(-0.0025, 0.0025), 6),
                lon=round(base_lon + rng.uniform(-0.0025, 0.0025), 6),
                hour=hour,
                day_of_week=dow,
                weather=weather,
                road_type=road_type,
                vehicle_type=v_type,
                traffic_volume=traffic_volume,
                severity=severity,
                timestamp=now - timedelta(hours=rng.randint(1, 720)),
            )
        )
    return rows


def init_db(hash_password_fn):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        demo_orgs = [
            Organization(
                name="Hanamkonda Traffic PS",
                station_code="WGL-HNK-01",
                city="Hanamkonda",
                state="Telangana",
                active_dataset_label="Hanamkonda Sector Demo v1",
            ),
            Organization(
                name="Kazipet & Station Corridor PS",
                station_code="WGL-KZP-02",
                city="Warangal / Kazipet",
                state="Telangana",
                active_dataset_label="Kazipet Corridor Demo v1",
            ),
        ]
        seeded_orgs = []
        for demo_org in demo_orgs:
            org = db.query(Organization).filter(Organization.name == demo_org.name).first()
            if org is None:
                org = demo_org
                db.add(org)
                db.flush()
            seeded_orgs.append(org)

        demo_users = [
            ("police_hnk", seeded_orgs[0], "authority"),
            ("police_kzp", seeded_orgs[1], "authority"),
            ("driver_demo", seeded_orgs[0], "driver"),
        ]
        for username, org, role in demo_users:
            if not db.query(User).filter(User.username == username).first():
                db.add(User(
                    username=username,
                    password_hash=hash_password_fn("pass123"),
                    role=role,
                    org_id=org.id,
                ))

        demo_seeds = [(seeded_orgs[0], 101), (seeded_orgs[1], 202)]
        for org, seed in demo_seeds:
            if not db.query(AccidentRecord).filter(AccidentRecord.org_id == org.id).first():
                db.add_all(generate_synthetic_rows(
                    org.id,
                    org.active_dataset_label,
                    count=800,
                    seed=seed,
                ))

        existing_edges = {
            (edge.source_junction, edge.target_junction)
            for edge in db.query(RoadEdge).all()
        }
        missing_edges = []
        edge_rng = random.Random(42)
        for src, dst, dist, risk, rtype in ROAD_LINKS:
            if (src, dst) in existing_edges:
                continue
            pts = _interpolate_path(JUNCTIONS[src], JUNCTIONS[dst], steps=5, rng=edge_rng)
            missing_edges.append(
                RoadEdge(
                    source_junction=src,
                    target_junction=dst,
                    distance_km=dist,
                    base_risk=risk,
                    road_type=rtype,
                    waypoints_json=json.dumps(pts),
                )
            )
        db.add_all(missing_edges)
        db.commit()
    finally:
        db.close()