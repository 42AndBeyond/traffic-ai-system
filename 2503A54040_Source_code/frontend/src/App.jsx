import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup } from "react-leaflet";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import "leaflet/dist/leaflet.css";

const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [authInfo, setAuthInfo] = useState({
    username: localStorage.getItem("username") || "",
    role: localStorage.getItem("role") || "driver",
    station_name: localStorage.getItem("station_name") || "Driver Portal",
    active_dataset: localStorage.getItem("active_dataset") || "",
  });

  // "login" or "register"
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [roleInput, setRoleInput] = useState("authority");
  const [stationName, setStationName] = useState("");
  const [authMsg, setAuthMsg] = useState("");
  const [authErr, setAuthErr] = useState("");

  const [tab, setTab] = useState(() => (
    localStorage.getItem("role") === "authority" ? "authority" : "driver"
  ));
  const [overview, setOverview] = useState(null);
  const [junctions, setJunctions] = useState([]);

  // ML Predictor state
  const [predForm, setPredForm] = useState({
    junction: "Nakkalagutta X Road",
    hour: 18,
    day_of_week: 4,
    weather: "Rain",
    road_type: "Junction",
    vehicle_type: "Two-Wheeler",
    traffic_volume: 950,
  });
  const [predResult, setPredResult] = useState(null);

  // Driver Route state
  const [routeForm, setRouteForm] = useState({
    source: "Kazipet X Road",
    destination: "Warangal Station Road",
    hour: 18,
    weather: "Rain",
    vehicle_type: "Two-Wheeler",
  });
  const [routeResult, setRouteResult] = useState(null);
  const [routeErr, setRouteErr] = useState("");

  useEffect(() => {
    fetch(`${API_BASE_URL}/junctions`)
      .then((r) => r.json())
      .then((d) => setJunctions(d.junctions || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (token) {
      loadOverview(token);
    }
  }, [token]);

  async function loadOverview(jwtToken) {
    try {
      const res = await fetch(`${API_BASE_URL}/analytics/overview`, {
        headers: { Authorization: `Bearer ${jwtToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        setOverview(data);
        setAuthInfo((prev) => ({
          ...prev,
          active_dataset: data.active_dataset,
          ...(prev.role === "authority" ? { station_name: data.station_name } : {}),
        }));
      }
    } catch {
      // ignore network error during initial load
    }
  }

  async function handleAuthSubmit(e) {
    e.preventDefault();
    setAuthErr("");
    setAuthMsg("");

    if (mode === "register") {
      const res = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username,
          password,
          role: roleInput,
          station_name: stationName || undefined,
          city: "Hanamkonda / Warangal",
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setAuthErr(data.detail || "Registration failed");
        return;
      }
      setAuthMsg("Account created! Signing you in...");
    }

    const form = new URLSearchParams();
    form.append("username", username);
    form.append("password", password);

    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    });
    const data = await res.json();
    if (!res.ok) {
      setAuthErr(data.detail || "Invalid credentials");
      return;
    }

    localStorage.setItem("token", data.access_token);
    localStorage.setItem("username", data.username);
    localStorage.setItem("role", data.role);
    localStorage.setItem("station_name", data.station_name);
    localStorage.setItem("active_dataset", data.active_dataset || "");

    setToken(data.access_token);
    setAuthInfo({
      username: data.username,
      role: data.role,
      station_name: data.station_name,
      active_dataset: data.active_dataset || "",
    });
    setTab(data.role === "driver" ? "driver" : "authority");
  }

  function handleLogout() {
    localStorage.clear();
    setToken("");
    setOverview(null);
  }

  async function handlePredict(e) {
    e.preventDefault();
    const res = await fetch(`${API_BASE_URL}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(predForm),
    });
    if (res.ok) {
      setPredResult(await res.json());
    }
  }

  async function handleOptimizeRoute(e) {
    e.preventDefault();
    setRouteErr("");
    const res = await fetch(`${API_BASE_URL}/routes/optimize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(routeForm),
    });
    const data = await res.json();
    if (!res.ok) {
      setRouteErr(data.detail || "Could not compute route");
      return;
    }
    setRouteResult(data);
  }

  function riskBadge(level) {
    if (level === "High") return <span className="badge-high">High Risk</span>;
    if (level === "Medium") return <span className="badge-med">Medium Risk</span>;
    return <span className="badge-low">Low Risk</span>;
  }

  if (!token) {
    return (
      <div className="app-shell">
        <div className="topbar">
          <div className="brand">AI Smart Traffic &amp; Accident Prediction</div>
          <div style={{ fontSize: 13, color: "#94a3b8" }}>Hanamkonda / Warangal</div>
        </div>
        <div className="container" style={{ maxWidth: 460 }}>
          <div className="card">
            <div className="row" style={{ marginBottom: 14 }}>
              <button
                type="button"
                className={mode === "login" ? "" : "secondary"}
                style={{ flex: 1 }}
                onClick={() => {
                  setMode("login");
                  setAuthErr("");
                  setAuthMsg("");
                }}
              >
                Login
              </button>
              <button
                type="button"
                className={mode === "register" ? "" : "secondary"}
                style={{ flex: 1 }}
                onClick={() => {
                  setMode("register");
                  setAuthErr("");
                  setAuthMsg("");
                }}
              >
                Create Account
              </button>
            </div>

            <h3>{mode === "login" ? "Login to Your Account" : "Create a New Account"}</h3>

            <form onSubmit={handleAuthSubmit}>
              <div style={{ marginBottom: 10 }}>
                <label>Username</label>
                <input
                  style={{ width: "100%" }}
                  placeholder="Enter username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
              </div>

              <div style={{ marginBottom: 10 }}>
                <label>Password</label>
                <input
                  type="password"
                  style={{ width: "100%" }}
                  placeholder="Enter password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              {mode === "register" && (
                <>
                  <div style={{ marginBottom: 10 }}>
                    <label>Account Role</label>
                    <select
                      style={{ width: "100%" }}
                      value={roleInput}
                      onChange={(e) => setRoleInput(e.target.value)}
                    >
                      <option value="authority">Traffic Police / Authority (Own Dataset)</option>
                      <option value="driver">Driver / Commuter</option>
                    </select>
                  </div>

                  {roleInput === "authority" && (
                    <div style={{ marginBottom: 10 }}>
                      <label>Police Station / Authority Name</label>
                      <input
                        style={{ width: "100%" }}
                        placeholder="e.g., Subedari Traffic PS"
                        value={stationName}
                        onChange={(e) => setStationName(e.target.value)}
                      />
                    </div>
                  )}
                </>
              )}

              <div style={{ marginTop: 14 }}>
                <button type="submit" style={{ width: "100%" }}>
                  {mode === "login" ? "Login" : "Create Account"}
                </button>
              </div>

              {authMsg && <div className="ok-text">{authMsg}</div>}
              {authErr && <div className="err-text">{authErr}</div>}
            </form>
          </div>
        </div>
      </div>
    );
  }

  const mapCenter = overview?.hotspots?.[0]?.coords || [17.992, 79.568];

  return (
    <div className="app-shell">
      <div className="topbar">
        <div>
          <span className="brand">AI Smart Traffic &amp; Accident Prediction</span>
          <span style={{ marginLeft: 12, fontSize: 13, color: "#94a3b8" }}>
            {authInfo.role === "authority"
              ? `${authInfo.station_name} (${authInfo.username})`
              : `Driver: ${authInfo.username}`}
          </span>
        </div>
        <div className="row">
          {authInfo.role === "authority" && (
            <button
              className={tab === "authority" ? "" : "secondary"}
              onClick={() => setTab("authority")}
            >
              Authority &amp; Analytics
            </button>
          )}
          <button
            className={tab === "driver" ? "" : "secondary"}
            onClick={() => setTab("driver")}
          >
            Driver Route &amp; Risk
          </button>
          <button className="secondary" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </div>

      <div className="container">
        {tab === "authority" && overview && (
          <>
            <div className="grid-3" style={{ marginBottom: 18 }}>
              <div className="card" style={{ marginBottom: 0 }}>
                <div style={{ fontSize: 12, color: "#94a3b8" }}>ACTIVE STATION DATASET</div>
                <div className="kpi-val" style={{ fontSize: 18 }}>
                  {overview.active_dataset === "Default Baseline Dataset"
                    ? "Hanamkonda–Warangal Traffic Dataset v1"
                    : overview.active_dataset}
                </div>
                <div className="kpi-sub">Isolated to Org #{overview.org_id}</div>
              </div>
              <div className="card" style={{ marginBottom: 0 }}>
                <div style={{ fontSize: 12, color: "#94a3b8" }}>LOGGED INCIDENTS</div>
                <div className="kpi-val">{overview.total_records}</div>
                <div className="kpi-sub">High severity: {overview.high_severity_count}</div>
              </div>
              <div className="card" style={{ marginBottom: 0 }}>
                <div style={{ fontSize: 12, color: "#94a3b8" }}>AVG TRAFFIC VOLUME</div>
                <div className="kpi-val">{overview.avg_traffic_volume}</div>
                <div className="kpi-sub">Vehicles / window</div>
              </div>
            </div>

            <div className="grid-2">
              <div className="card">
                <h3>Hotspot &amp; Incident Map</h3>
                <div style={{ height: 340, borderRadius: 10, overflow: "hidden" }}>
                  <MapContainer center={mapCenter} zoom={13} style={{ height: "100%", width: "100%" }}>
                    <TileLayer
                      attribution="&copy; OpenStreetMap contributors"
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    {overview.hotspots.map((hs) => (
                      <CircleMarker
                        key={hs.junction}
                        center={hs.coords}
                        radius={Math.min(26, Math.max(9, hs.incidents / 8))}
                        pathOptions={{ color: "#ef4444", fillColor: "#ef4444", fillOpacity: 0.45 }}
                      >
                        <Popup>
                          <b>{hs.junction}</b>
                          <br />
                          Incidents: {hs.incidents}
                        </Popup>
                      </CircleMarker>
                    ))}
                  </MapContainer>
                </div>
              </div>

              <div className="card">
                <h3>Hourly Traffic &amp; Incident Pattern</h3>
                <div style={{ height: 340 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={overview.hourly_series}>
                      <XAxis dataKey="hour" stroke="#94a3b8" fontSize={11} />
                      <YAxis stroke="#94a3b8" fontSize={11} />
                      <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
                      <Bar dataKey="incidents" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            <div className="grid-2">
              <div className="card">
                <h3>Predictive Decision Support (Authority Actions)</h3>
                {overview.recommendations.map((rec) => (
                  <div key={rec.junction} className="alert-box">
                    <div className="row" style={{ justifyContent: "space-between" }}>
                      <b>{rec.junction} ({rec.incidents} records)</b>
                      {riskBadge(rec.priority)}
                    </div>
                    <div style={{ fontSize: 13, marginTop: 6, color: "#cbd5e1" }}>{rec.action}</div>
                  </div>
                ))}

              </div>

              <div className="card">
                <h3>ML Accident &amp; Congestion Simulator</h3>
                <form onSubmit={handlePredict}>
                  <div className="grid-2" style={{ gap: 10 }}>
                    <div>
                      <label>Hour (0–23)</label>
                      <input
                        type="number"
                        min={0}
                        max={23}
                        style={{ width: "100%" }}
                        value={predForm.hour}
                        onChange={(e) => setPredForm({ ...predForm, hour: Number(e.target.value) })}
                      />
                    </div>
                    <div>
                      <label>Weather</label>
                      <select
                        style={{ width: "100%" }}
                        value={predForm.weather}
                        onChange={(e) => setPredForm({ ...predForm, weather: e.target.value })}
                      >
                        <option>Clear</option>
                        <option>Rain</option>
                        <option>Fog</option>
                        <option>Haze</option>
                      </select>
                    </div>
                    <div>
                      <label>Road Type</label>
                      <select
                        style={{ width: "100%" }}
                        value={predForm.road_type}
                        onChange={(e) => setPredForm({ ...predForm, road_type: e.target.value })}
                      >
                        <option>Junction</option>
                        <option>Arterial</option>
                        <option>Highway</option>
                        <option>Collector</option>
                        <option>Ring Road</option>
                      </select>
                    </div>
                    <div>
                      <label>Vehicle Type</label>
                      <select
                        style={{ width: "100%" }}
                        value={predForm.vehicle_type}
                        onChange={(e) => setPredForm({ ...predForm, vehicle_type: e.target.value })}
                      >
                        <option>Two-Wheeler</option>
                        <option>Car</option>
                        <option>Auto/Bus</option>
                        <option>Heavy Truck</option>
                      </select>
                    </div>
                  </div>
                  <div style={{ marginTop: 12 }}>
                    <button type="submit">Predict Risk &amp; Congestion</button>
                  </div>
                </form>

                {predResult && (
                  <div className="alert-box" style={{ marginTop: 14 }}>
                    <div className="row" style={{ justifyContent: "space-between" }}>
                      <b>Accident Risk: {(predResult.accident_risk_score * 100).toFixed(1)}%</b>
                      {riskBadge(predResult.risk_level)}
                    </div>
                    <div style={{ fontSize: 13, marginTop: 6 }}>
                      Congestion: <b>{predResult.congestion_level}</b> ({predResult.congestion_index}/100)
                    </div>
                    <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 6 }}>
                      Key drivers: {predResult.key_factors.join(" • ")}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {tab === "driver" && (
          <div className="card">
            <h3>Driver Route Optimizer (Fastest vs. Safest Route)</h3>
            <form onSubmit={handleOptimizeRoute} className="row" style={{ marginBottom: 14 }}>
              <div>
                <label>Start Junction</label>
                <select
                  value={routeForm.source}
                  onChange={(e) => setRouteForm({ ...routeForm, source: e.target.value })}
                >
                  {junctions.map((j) => (
                    <option key={j.name} value={j.name}>{j.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label>Destination</label>
                <select
                  value={routeForm.destination}
                  onChange={(e) => setRouteForm({ ...routeForm, destination: e.target.value })}
                >
                  {junctions.map((j) => (
                    <option key={j.name} value={j.name}>{j.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label>Weather</label>
                <select
                  value={routeForm.weather}
                  onChange={(e) => setRouteForm({ ...routeForm, weather: e.target.value })}
                >
                  <option>Clear</option>
                  <option>Rain</option>
                  <option>Fog</option>
                  <option>Haze</option>
                </select>
              </div>
              <div>
                <label>Vehicle</label>
                <select
                  value={routeForm.vehicle_type}
                  onChange={(e) => setRouteForm({ ...routeForm, vehicle_type: e.target.value })}
                >
                  <option>Two-Wheeler</option>
                  <option>Car</option>
                  <option>Auto/Bus</option>
                  <option>Heavy Truck</option>
                </select>
              </div>
              <div style={{ alignSelf: "flex-end" }}>
                <button type="submit">Find Routes</button>
              </div>
            </form>

            {routeErr && <div className="err-text">{routeErr}</div>}

            {routeResult && (
              <>
                <div className="grid-2" style={{ marginBottom: 14 }}>
                  <div className="alert-box" style={{ borderLeftColor: "#f59e0b" }}>
                    <b>Shortest / Fastest Route</b>
                    <div style={{ fontSize: 13, marginTop: 4 }}>
                      {routeResult.fastest.path.join(" → ")}
                    </div>
                    <div style={{ fontSize: 13, marginTop: 6 }}>
                      Distance: <b>{routeResult.fastest.distance_km} km</b> • Est. Time:{" "}
                      <b>{routeResult.fastest.est_minutes} min</b> • Avg Risk:{" "}
                      <b>{(routeResult.fastest.avg_risk_score * 100).toFixed(1)}%</b>
                    </div>
                  </div>
                  <div className="alert-box" style={{ borderLeftColor: "#22c55e" }}>
                    <b>Recommended Safest Route</b>
                    <div style={{ fontSize: 13, marginTop: 4 }}>
                      {routeResult.safest.path.join(" → ")}
                    </div>
                    <div style={{ fontSize: 13, marginTop: 6 }}>
                      Distance: <b>{routeResult.safest.distance_km} km</b> • Est. Time:{" "}
                      <b>{routeResult.safest.est_minutes} min</b> • Avg Risk:{" "}
                      <b>{(routeResult.safest.avg_risk_score * 100).toFixed(1)}%</b>
                    </div>
                  </div>
                </div>

                <div style={{ height: 380, borderRadius: 10, overflow: "hidden" }}>
                  <MapContainer center={mapCenter} zoom={13} style={{ height: "100%", width: "100%" }}>
                    <TileLayer
                      attribution="&copy; OpenStreetMap contributors"
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    <Polyline
                      positions={routeResult.fastest.coordinates}
                      pathOptions={{ color: "#f59e0b", weight: 4, dashArray: "6 6" }}
                    />
                    <Polyline
                      positions={routeResult.safest.coordinates}
                      pathOptions={{ color: "#22c55e", weight: 5 }}
                    />
                  </MapContainer>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}