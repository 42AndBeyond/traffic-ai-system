import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

import database
import main
import ml_engine


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'traffic_test.db'}",
        connect_args={"check_same_thread": False},
    )
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    database.Base.metadata.create_all(bind=engine)
    yield session_factory
    engine.dispose()


@pytest.fixture
def client(test_db, monkeypatch):
    monkeypatch.setattr(main, "init_db", lambda hash_password_fn: None)
    database.init_db(main.hash_password)

    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_get_db
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.pop(main.get_db, None)


def _login(client, username):
    response = client.post(
        "/auth/login",
        data={"username": username, "password": "pass123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_init_db_seeds_expected_data_once_and_repairs_partial_seed(test_db):
    db = test_db()
    existing_org = database.Organization(
        name="Hanamkonda Traffic PS",
        station_code="WGL-HNK-01",
        city="Hanamkonda",
        state="Telangana",
        active_dataset_label="Hanamkonda Sector Demo v1",
    )
    db.add(existing_org)
    db.commit()
    db.close()

    database.init_db(main.hash_password)
    database.init_db(main.hash_password)

    db = test_db()
    orgs = db.query(database.Organization).order_by(database.Organization.id).all()
    users = db.query(database.User).all()
    accidents = db.query(database.AccidentRecord).all()
    edges = db.query(database.RoadEdge).all()
    assert [(org.name, org.city) for org in orgs] == [
        ("Hanamkonda Traffic PS", "Hanamkonda"),
        ("Kazipet & Station Corridor PS", "Warangal / Kazipet"),
    ]
    assert {
        (user.username, user.role, user.org_id)
        for user in users
    } == {
        ("police_hnk", "authority", orgs[0].id),
        ("police_kzp", "authority", orgs[1].id),
        ("driver_demo", "driver", orgs[0].id),
    }
    assert len(accidents) == 1600
    assert {record.org_id for record in accidents} == {orgs[0].id, orgs[1].id}
    assert all(record.junction in database.JUNCTIONS for record in accidents)
    assert len(edges) == len(database.ROAD_LINKS)
    assert {
        (
            edge.source_junction,
            edge.target_junction,
            edge.distance_km,
            edge.base_risk,
            edge.road_type,
        )
        for edge in edges
    } == set(database.ROAD_LINKS)
    for edge in edges:
        assert edge.source_junction in database.JUNCTIONS
        assert edge.target_junction in database.JUNCTIONS
        assert edge.distance_km > 0
        assert 0 <= edge.base_risk <= 1
        waypoints = json.loads(edge.waypoints_json)
        assert len(waypoints) == 6
        assert all(len(point) == 2 for point in waypoints)
    db.close()


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "timestamp" in response.json()


def test_register_and_login(client, test_db):
    register = client.post(
        "/auth/register",
        json={
            "username": "new_authority",
            "password": "secure-pass",
            "station_name": "New Hanamkonda Station",
            "station_code": "WGL-NEW-03",
            "city": "Hanamkonda",
        },
    )
    assert register.status_code == 200
    assert register.json() == {
        "message": "Account created",
        "username": "new_authority",
        "role": "authority",
    }

    login = client.post(
        "/auth/login",
        data={"username": "new_authority", "password": "secure-pass"},
    )
    assert login.status_code == 200
    payload = login.json()
    assert payload["token_type"] == "bearer"
    assert payload["username"] == "new_authority"
    assert payload["station_name"] == "New Hanamkonda Station"
    assert payload["org_id"] is not None
    assert payload["access_token"]

    duplicate = client.post(
        "/auth/register",
        json={"username": "new_authority", "password": "another-pass"},
    )
    assert duplicate.status_code == 400


def test_analytics_and_upload_are_isolated_by_org_id(client, test_db):
    hnk_headers = _login(client, "police_hnk")
    kzp_headers = _login(client, "police_kzp")

    hnk_before = client.get("/analytics/overview", headers=hnk_headers).json()
    kzp_before = client.get("/analytics/overview", headers=kzp_headers).json()
    assert hnk_before["org_id"] != kzp_before["org_id"]
    assert hnk_before["total_records"] == 800
    assert kzp_before["total_records"] == 800

    hnk_upload = client.post(
        "/datasets/upload?dataset_name=HNK%20Upload",
        headers=hnk_headers,
        files={"file": ("hnk.csv", "junction,hour,severity\nHanamkonda Chowrasta,9,3\n", "text/csv")},
    )
    assert hnk_upload.status_code == 200
    assert hnk_upload.json()["records_loaded"] == 1
    hnk_after = client.get("/analytics/overview", headers=hnk_headers).json()
    kzp_unchanged = client.get("/analytics/overview", headers=kzp_headers).json()
    assert hnk_after["total_records"] == 1
    assert hnk_after["active_dataset"] == "HNK Upload"
    assert {point["junction"] for point in hnk_after["map_points"]} == {"Hanamkonda Chowrasta"}
    assert kzp_unchanged["total_records"] == 800
    assert kzp_unchanged["active_dataset"] == kzp_before["active_dataset"]

    kzp_upload = client.post(
        "/datasets/upload?dataset_name=KZP%20Upload",
        headers=kzp_headers,
        files={"file": ("kzp.csv", "junction,hour,severity\nKazipet X Road,18,2\n", "text/csv")},
    )
    assert kzp_upload.status_code == 200
    hnk_unchanged = client.get("/analytics/overview", headers=hnk_headers).json()
    kzp_after = client.get("/analytics/overview", headers=kzp_headers).json()
    assert hnk_unchanged["total_records"] == 1
    assert hnk_unchanged["active_dataset"] == "HNK Upload"
    assert kzp_after["total_records"] == 1
    assert kzp_after["active_dataset"] == "KZP Upload"
    assert {point["junction"] for point in kzp_after["map_points"]} == {"Kazipet X Road"}

    db = test_db()
    counts = dict(
        db.query(database.AccidentRecord.org_id, func.count(database.AccidentRecord.id))
        .group_by(database.AccidentRecord.org_id)
        .all()
    )
    assert counts == {hnk_after["org_id"]: 1, kzp_after["org_id"]: 1}
    db.close()


def test_predict(client, tmp_path, monkeypatch):
    monkeypatch.setattr(ml_engine, "RISK_MODEL_PATH", str(tmp_path / "risk.joblib"))
    monkeypatch.setattr(ml_engine, "CONG_MODEL_PATH", str(tmp_path / "congestion.joblib"))
    response = client.post(
        "/predict",
        json={
            "junction": "Nakkalagutta X Road",
            "hour": 18,
            "day_of_week": 4,
            "weather": "Rain",
            "road_type": "Junction",
            "vehicle_type": "Two-Wheeler",
            "traffic_volume": 950,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert 0 <= result["accident_risk_score"] <= 1
    assert result["risk_level"] in {"Low", "Medium", "High"}
    assert 0 <= result["congestion_index"] <= 100
    assert result["congestion_level"] in {"Smooth", "Moderate", "Heavy"}
    assert result["key_factors"]


def test_routes_optimize(client):
    response = client.post(
        "/routes/optimize",
        json={
            "source": "Kazipet X Road",
            "destination": "Warangal Station Road",
            "hour": 18,
            "weather": "Rain",
            "vehicle_type": "Two-Wheeler",
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert set(result) == {"fastest", "safest"}
    for route in result.values():
        assert route["path"][0] == "Kazipet X Road"
        assert route["path"][-1] == "Warangal Station Road"
        assert route["distance_km"] > 0
        assert route["segments"]
        assert route["coordinates"]