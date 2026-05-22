"""Flask and Socket.IO dashboard for real-time pipeline monitoring."""

import threading
import time
from flask import Flask, Response, render_template_string, jsonify
from flask_socketio import SocketIO

# -- HTML template (inline for portability) ------------------------------------
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Traffic Sign Recognition - Live Dashboard</title>
<script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
<style>
  :root {
    --bg:       #0f1117;
    --surface:  #1a1d27;
    --border:   #2a2d3a;
    --text:     #e2e4ed;
    --muted:    #8b8fa8;
    --blue:     #3B8BD4;
    --amber:    #EF9F27;
    --red:      #E24B4A;
    --green:    #639922;
    --teal:     #1D9E75;
    --font:     'Segoe UI', system-ui, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: var(--font); min-height: 100vh; }

  header {
    padding: 14px 28px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between;
  }
  header h1 { font-size: 17px; font-weight: 600; letter-spacing: .3px; }
  .status-dot {
    width: 9px; height: 9px; border-radius: 50%;
    background: var(--green); display: inline-block; margin-right: 8px;
    animation: pulse 1.5s ease-in-out infinite;
  }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

  .grid {
    display: grid;
    grid-template-columns: 1fr 380px;
    grid-template-rows: auto auto;
    gap: 16px;
    padding: 18px 24px;
    max-width: 1400px; margin: 0 auto;
  }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
  }
  .card-header {
    padding: 10px 16px;
    font-size: 12px; font-weight: 600; text-transform: uppercase;
    letter-spacing: .8px; color: var(--muted);
    border-bottom: 1px solid var(--border);
  }
  .card-body { padding: 14px 16px; }

  /* Video feed */
  #video-feed {
    width: 100%; display: block; border-radius: 0;
    background: #000; min-height: 340px;
  }

  /* Stats row */
  .stats-row {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
    grid-column: 1 / -1;
  }
  .stat {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 16px;
  }
  .stat-value { font-size: 26px; font-weight: 700; }
  .stat-label { font-size: 11px; color: var(--muted); margin-top: 2px; }

  /* Alert panel */
  #alert-list { list-style: none; }
  #alert-list li {
    padding: 10px 12px;
    border-radius: 7px;
    margin-bottom: 8px;
    border-left: 4px solid var(--muted);
    background: rgba(255,255,255,.03);
    font-size: 13px;
    transition: background .2s;
  }
  #alert-list li.critical { border-color: var(--red); }
  #alert-list li.warning  { border-color: var(--amber); }
  #alert-list li.info     { border-color: var(--blue); }
  .alert-level {
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .6px; margin-bottom: 3px;
  }
  .critical .alert-level { color: var(--red); }
  .warning  .alert-level { color: var(--amber); }
  .info     .alert-level { color: var(--blue); }
  .alert-msg  { font-weight: 600; font-size: 13px; }
  .alert-action { font-size: 12px; color: var(--muted); margin-top: 2px; }

  /* Detection list */
  #det-list { list-style: none; }
  #det-list li {
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
    font-size: 13px;
  }
  #det-list li:last-child { border-bottom: none; }
  .conf-bar-wrap {
    width: 80px; height: 6px; background: var(--border); border-radius: 3px;
    overflow: hidden; margin-left: 10px;
  }
  .conf-bar {
    height: 100%; background: var(--teal); border-radius: 3px;
    transition: width .3s;
  }

  .empty-msg { color: var(--muted); font-size: 13px; text-align: center; padding: 20px 0; }
</style>
</head>
<body>

<header>
  <h1><span class="status-dot" id="status-dot"></span> Traffic Sign Recognition - Live</h1>
  <span style="font-size:12px;color:var(--muted)" id="frame-counter">Frame 0</span>
</header>

<div class="grid">

  <!-- Video -->
  <div class="card" style="grid-row: 1; grid-column: 1;">
    <div class="card-header">Live camera feed</div>
    <img id="video-feed" src="/video_feed" alt="Camera feed">
  </div>

  <!-- Sidebar -->
  <div style="grid-row: 1; grid-column: 2; display:flex; flex-direction:column; gap:14px;">

    <!-- Alerts -->
    <div class="card">
      <div class="card-header">Active alerts</div>
      <div class="card-body">
        <ul id="alert-list">
          <li class="empty-msg" id="no-alert">No alerts</li>
        </ul>
      </div>
    </div>

    <!-- Detections -->
    <div class="card">
      <div class="card-header">Detected signs</div>
      <div class="card-body">
        <ul id="det-list">
          <li class="empty-msg" id="no-det">No signs detected</li>
        </ul>
      </div>
    </div>

  </div>

  <!-- Stats -->
  <div class="stats-row">
    <div class="stat">
      <div class="stat-value" id="stat-fps">-</div>
      <div class="stat-label">Frames / sec</div>
    </div>
    <div class="stat">
      <div class="stat-value" id="stat-signs">0</div>
      <div class="stat-label">Signs this frame</div>
    </div>
    <div class="stat">
      <div class="stat-value" id="stat-alerts">0</div>
      <div class="stat-label">Active alerts</div>
    </div>
    <div class="stat">
      <div class="stat-value" id="stat-frames">0</div>
      <div class="stat-label">Total frames</div>
    </div>
  </div>

</div>

<script>
const socket = io();

socket.on('connect', () => {
  document.getElementById('status-dot').style.background = 'var(--green)';
});
socket.on('disconnect', () => {
  document.getElementById('status-dot').style.background = 'var(--red)';
});

socket.on('stats', (data) => {
  document.getElementById('stat-fps').textContent    = data.fps.toFixed(1);
  document.getElementById('stat-signs').textContent  = data.detections;
  document.getElementById('stat-alerts').textContent = data.alerts.length;
  document.getElementById('stat-frames').textContent = data.frame_count;
  document.getElementById('frame-counter').textContent = `Frame ${data.frame_count}`;

  // Alerts
  const alertList = document.getElementById('alert-list');
  const noAlert   = document.getElementById('no-alert');
  if (data.alerts.length) {
    noAlert.style.display = 'none';
    alertList.innerHTML = '';
    data.alerts.forEach(a => {
      const li = document.createElement('li');
      li.className = a.level;
      li.innerHTML = `
        <div class="alert-level">${a.level}</div>
        <div class="alert-msg">${a.message}</div>
        <div class="alert-action">${a.action}</div>`;
      alertList.appendChild(li);
    });
  } else {
    alertList.innerHTML = '';
    noAlert.style.display = 'block';
    alertList.appendChild(noAlert);
  }

  // Detections
  const detList = document.getElementById('det-list');
  const noDet   = document.getElementById('no-det');
  if (data.current_dets && data.current_dets.length) {
    noDet.style.display = 'none';
    detList.innerHTML = '';
    data.current_dets.forEach(d => {
      const li = document.createElement('li');
      const pct = Math.round(d.confidence * 100);
      li.innerHTML = `
        <span>${d.label}</span>
        <div style="display:flex;align-items:center;">
          <span style="font-size:11px;color:var(--muted)">${pct}%</span>
          <div class="conf-bar-wrap"><div class="conf-bar" style="width:${pct}%"></div></div>
        </div>`;
      detList.appendChild(li);
    });
  } else {
    detList.innerHTML = '';
    noDet.style.display = 'block';
    detList.appendChild(noDet);
  }
});
</script>
</body>
</html>
"""


# -- Flask app factory ---------------------------------------------------------
def create_app(pipeline):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "tsr_secret"
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

    @app.route("/")
    def index():
        return render_template_string(DASHBOARD_HTML)

    @app.route("/video_feed")
    def video_feed():
        def generate():
            for jpeg_bytes in pipeline.iter_frames():
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n"
                       + jpeg_bytes + b"\r\n")
        return Response(generate(),
                        mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.route("/api/stats")
    def api_stats():
        return jsonify(pipeline.get_stats())

    # -- Background stats emitter ----------------------------------------------
    def emit_stats():
        while True:
            stats = pipeline.get_stats()
            socketio.emit("stats", stats)
            time.sleep(0.25)

    threading.Thread(target=emit_stats, daemon=True).start()

    return app, socketio


def run_dashboard(pipeline, host: str = "0.0.0.0", port: int = 5000):
    app, socketio = create_app(pipeline)
    print(f"[Dashboard] Serving at http://{host}:{port}")
    socketio.run(app, host=host, port=port)
