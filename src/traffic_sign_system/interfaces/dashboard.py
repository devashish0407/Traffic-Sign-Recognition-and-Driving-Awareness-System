import time
import threading
import uuid
from pathlib import Path

from flask import (
    Flask,
    Response,
    render_template_string,
    jsonify,
    request,
    send_file,
    abort,
)
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename

from traffic_sign_system.paths import project_path
from traffic_sign_system.config.sign_classes import SIGN_LABELS, HAZARD_RULES

ALLOWED_VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"}


# -- HTML template (inline for portability) ------------------------------------
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TrafficLens - Live Hazard Dashboard</title>
<script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:            #090b12;
    --bg-grad:       radial-gradient(circle at 15% -10%, rgba(99,102,241,.16), transparent 45%),
                      radial-gradient(circle at 85% 0%, rgba(34,211,238,.10), transparent 40%);
    --surface:       #12141f;
    --surface-alt:   #171a28;
    --surface-hover: #1c2033;
    --border:        rgba(255,255,255,.08);
    --border-strong: rgba(255,255,255,.14);
    --text:          #eef0f8;
    --muted:         #8b90a8;
    --muted-dim:     #5b5f76;

    --accent:        #6366f1;
    --accent-2:      #22d3ee;
    --accent-grad:   linear-gradient(135deg, #6366f1, #22d3ee);

    --blue:          #3B8BD4;
    --green:         #1FBE7A;
    --amber:         #EF9F27;
    --red:           #F0464B;

    --shadow:        0 10px 30px rgba(0,0,0,.35);
    --radius:         14px;
    --radius-sm:      9px;
    --font:          'Inter', system-ui, sans-serif;
    --mono:          'JetBrains Mono', 'Consolas', monospace;
  }

  html[data-theme="light"] {
    --bg:            #eef1f8;
    --bg-grad:       radial-gradient(circle at 15% -10%, rgba(99,102,241,.10), transparent 45%),
                      radial-gradient(circle at 85% 0%, rgba(34,211,238,.08), transparent 40%);
    --surface:       #ffffff;
    --surface-alt:   #f5f6fb;
    --surface-hover: #eceefa;
    --border:        rgba(20,22,40,.09);
    --border-strong: rgba(20,22,40,.16);
    --text:          #14162a;
    --muted:         #676c85;
    --muted-dim:     #9498ab;
    --shadow:        0 10px 30px rgba(30,34,70,.08);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; }
  body {
    background: var(--bg-grad), var(--bg);
    color: var(--text);
    font-family: var(--font);
    min-height: 100vh;
    transition: background-color .35s ease, color .35s ease;
  }
  ::selection { background: rgba(99,102,241,.35); }
  a { color: var(--accent-2); }

  /* -- Header ------------------------------------------------------------ */
  header {
    padding: 14px 28px;
    background: color-mix(in srgb, var(--surface) 92%, transparent);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between;
    position: sticky; top: 0; z-index: 20;
  }
  .brand { display: flex; align-items: center; gap: 10px; }
  .brand-mark {
    width: 32px; height: 32px; border-radius: 9px;
    background: var(--accent-grad);
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 0 0 1px var(--border-strong), 0 4px 14px rgba(99,102,241,.35);
  }
  .brand-mark svg { width: 18px; height: 18px; }
  .brand h1 { font-size: 16px; font-weight: 700; letter-spacing: .2px; }
  .brand span.sub { display:block; font-size: 11px; color: var(--muted); font-weight: 500; margin-top: 1px; }

  .header-right { display: flex; align-items: center; gap: 18px; }

  .status-pill {
    display: flex; align-items: center; gap: 7px;
    font-size: 12px; color: var(--muted); font-family: var(--mono);
    background: var(--surface-alt); border: 1px solid var(--border);
    padding: 6px 12px; border-radius: 999px;
  }
  .status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--muted-dim); display: inline-block;
  }
  .status-dot.live { background: var(--green); animation: pulse 1.6s ease-in-out infinite; }
  .status-dot.off  { background: var(--red); }
  @keyframes pulse { 0%,100%{opacity:1; box-shadow:0 0 0 0 rgba(31,190,122,.5);} 50%{opacity:.55; box-shadow:0 0 0 5px rgba(31,190,122,0);} }

  /* Theme toggle switch */
  .theme-toggle {
    width: 52px; height: 28px; border-radius: 999px;
    background: var(--surface-alt); border: 1px solid var(--border);
    position: relative; cursor: pointer; flex-shrink: 0;
    transition: background .25s ease;
  }
  .theme-toggle .knob {
    position: absolute; top: 3px; left: 3px;
    width: 20px; height: 20px; border-radius: 50%;
    background: var(--accent-grad);
    display: flex; align-items: center; justify-content: center;
    transition: transform .3s cubic-bezier(.4,0,.2,1);
    font-size: 11px;
  }
  html[data-theme="light"] .theme-toggle .knob { transform: translateX(24px); }

  /* -- Layout ------------------------------------------------------------ */
  .shell { max-width: 1440px; margin: 0 auto; padding: 22px 24px 40px; }
  .grid {
    display: grid;
    grid-template-columns: 1fr 380px;
    gap: 18px;
  }
  @media (max-width: 980px) { .grid { grid-template-columns: 1fr; } }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow: var(--shadow);
    animation: fadeInUp .5s ease both;
  }
  @keyframes fadeInUp { from { opacity:0; transform: translateY(10px);} to { opacity:1; transform:none; } }

  .card-header {
    padding: 12px 16px;
    font-size: 11.5px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .8px; color: var(--muted);
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between;
  }
  .card-body { padding: 14px 16px; }

  /* -- Source tabs --------------------------------------------------------*/
  .tabs { display: flex; gap: 6px; }
  .tab-btn {
    font-family: var(--font); font-size: 12px; font-weight: 600;
    color: var(--muted); background: transparent; border: 1px solid transparent;
    padding: 5px 10px; border-radius: 7px; cursor: pointer;
    transition: all .2s ease;
  }
  .tab-btn:hover { color: var(--text); background: var(--surface-hover); }
  .tab-btn.active { color: var(--text); background: var(--surface-alt); border-color: var(--border-strong); }

  /* -- Video card ---------------------------------------------------------*/
  .video-wrap { position: relative; background: #000; min-height: 340px; }
  #video-feed { width: 100%; display: block; }
  #video-feed.hidden { display: none; }

  .video-badge {
    position: absolute; z-index: 5;
    font-family: var(--mono); font-size: 11px; font-weight: 600;
    padding: 4px 9px; border-radius: 6px;
    background: rgba(10,12,20,.6); backdrop-filter: blur(4px);
    color: #fff; letter-spacing: .3px;
    display: flex; align-items: center; gap: 6px;
  }
  .video-badge.rec { top: 12px; left: 12px; }
  .video-badge.rec .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--red); animation: pulse 1.2s infinite; }
  .video-badge.fps { top: 12px; right: 12px; }

  .dropzone {
    min-height: 340px; display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 10px; text-align: center; padding: 30px; cursor: pointer;
    border: 1.5px dashed var(--border-strong);
    background: var(--surface-alt);
    transition: border-color .2s ease, background .2s ease;
  }
  .dropzone.drag-over { border-color: var(--accent-2); background: var(--surface-hover); }
  .dropzone .icon-circle {
    width: 52px; height: 52px; border-radius: 50%;
    background: var(--accent-grad); opacity: .9;
    display: flex; align-items: center; justify-content: center;
  }
  .dropzone .icon-circle svg { width: 24px; height: 24px; color: #fff; }
  .dropzone h3 { font-size: 14.5px; font-weight: 700; }
  .dropzone p { font-size: 12.5px; color: var(--muted); max-width: 320px; }
  .dropzone input[type=file] { display: none; }
  .dz-btn {
    margin-top: 4px; font-family: var(--font); font-weight: 600; font-size: 12.5px;
    color: #fff; background: var(--accent-grad); border: none; border-radius: 8px;
    padding: 9px 18px; cursor: pointer; transition: transform .15s ease, filter .15s ease;
  }
  .dz-btn:hover { filter: brightness(1.08); transform: translateY(-1px); }
  .upload-progress { width: 220px; height: 6px; border-radius: 4px; background: var(--border); overflow: hidden; margin-top: 4px; display:none; }
  .upload-progress.show { display: block; }
  .upload-progress > div { height: 100%; width: 0%; background: var(--accent-grad); transition: width .2s ease; }

  /* -- Stats row -----------------------------------------------------------*/
  .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 16px; }
  .stat {
    background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 14px 16px; box-shadow: var(--shadow);
    animation: fadeInUp .5s ease both;
  }
  .stat-value { font-family: var(--mono); font-size: 24px; font-weight: 700; letter-spacing: -.5px; }
  .stat-label { font-size: 11px; color: var(--muted); margin-top: 3px; font-weight: 500; }
  .stat-accent-1 .stat-value { color: var(--accent-2); }
  .stat-accent-2 .stat-value { color: var(--amber); }
  .stat-accent-3 .stat-value { color: var(--red); }

  /* -- Alert / detection lists ----------------------------------------------*/
  #alert-list, #det-list { list-style: none; display: flex; flex-direction: column; gap: 8px; }
  #alert-list li {
    padding: 10px 12px; border-radius: var(--radius-sm);
    border-left: 4px solid var(--muted-dim);
    background: var(--surface-alt);
    font-size: 13px;
    animation: fadeInUp .35s ease both;
    transition: background .2s ease;
  }
  #alert-list li:hover { background: var(--surface-hover); }
  .alert-level {
    font-size: 9.5px; font-weight: 800; text-transform: uppercase;
    letter-spacing: .7px; margin-bottom: 3px; display:flex; align-items:center; gap:5px;
  }
  .alert-level .swatch { width: 7px; height: 7px; border-radius: 50%; }
  .alert-msg  { font-weight: 600; font-size: 13px; }
  .alert-action { font-size: 11.5px; color: var(--muted); margin-top: 2px; }

  #det-list li {
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 10px; border-radius: var(--radius-sm);
    background: var(--surface-alt);
    font-size: 12.5px;
  }
  .det-label { display: flex; align-items: center; gap: 8px; }
  .det-label .swatch { width: 8px; height: 8px; border-radius: 50%; flex-shrink:0; }
  .conf-bar-wrap {
    width: 70px; height: 5px; background: var(--border); border-radius: 3px;
    overflow: hidden; margin-left: 10px;
  }
  .conf-bar { height: 100%; background: var(--accent-grad); border-radius: 3px; transition: width .3s ease; }

  .empty-msg { color: var(--muted-dim); font-size: 12.5px; text-align: center; padding: 22px 0; }

  /* -- Legend --------------------------------------------------------------*/
  .legend { display: flex; flex-wrap: wrap; gap: 10px; padding: 0 16px 14px; font-size: 11px; color: var(--muted); }
  .legend span { display: flex; align-items: center; gap: 5px; }
  .legend .swatch { width: 8px; height: 8px; border-radius: 50%; }

  /* -- Session summary -------------------------------------------------------*/
  #summary-card { display: none; margin-top: 16px; }
  #summary-card.show { display: block; }
  .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
  .summary-tile { background: var(--surface-alt); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 12px 14px; }
  .summary-tile .v { font-family: var(--mono); font-size: 19px; font-weight: 700; }
  .summary-tile .l { font-size: 10.5px; color: var(--muted); margin-top: 2px; }
  .summary-bars { margin-top: 14px; display: flex; flex-direction: column; gap: 8px; }
  .summary-bar-row { display:flex; align-items:center; gap: 10px; font-size: 12px; }
  .summary-bar-row .name { width: 150px; color: var(--muted); flex-shrink: 0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .summary-bar-track { flex: 1; height: 8px; border-radius: 4px; background: var(--border); overflow:hidden; }
  .summary-bar-fill { height: 100%; background: var(--accent-grad); border-radius: 4px; transition: width .5s ease; }
  .summary-bar-row .count { width: 30px; text-align: right; font-family: var(--mono); color: var(--text); font-size: 11.5px; }

  /* -- Footer ----------------------------------------------------------------*/
  footer { margin-top: 22px; }
  .footer-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
  @media (max-width: 980px) { .footer-grid { grid-template-columns: 1fr; } }
  .footer-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px 18px; box-shadow: var(--shadow); }
  .footer-card h4 { font-size: 12.5px; font-weight: 700; margin-bottom: 4px; }
  .footer-card p { font-size: 12px; color: var(--muted); margin-bottom: 12px; line-height: 1.5; }
  .link-row { display: flex; flex-wrap: wrap; gap: 8px; }
  .pill-link {
    font-size: 12px; font-weight: 600; text-decoration: none;
    color: var(--text); background: var(--surface-alt); border: 1px solid var(--border);
    padding: 8px 13px; border-radius: 8px; display: inline-flex; align-items: center; gap: 6px;
    transition: all .18s ease;
  }
  .pill-link:hover { border-color: var(--accent-2); color: var(--accent-2); transform: translateY(-1px); }
  .btn-primary {
    font-family: var(--font); font-weight: 700; font-size: 12.5px;
    color: #fff; background: var(--accent-grad); border: none; border-radius: 8px;
    padding: 10px 16px; cursor: pointer; display: inline-flex; align-items: center; gap: 7px;
    transition: transform .15s ease, filter .15s ease;
  }
  .btn-primary:hover { filter: brightness(1.08); transform: translateY(-1px); }
  .btn-primary:disabled { opacity: .5; cursor: not-allowed; transform:none; }
  .foot-note { font-size: 11px; color: var(--muted-dim); margin-top: 10px; }

  .toast {
    position: fixed; bottom: 20px; right: 20px; z-index: 50;
    background: var(--surface); border: 1px solid var(--border-strong); box-shadow: var(--shadow);
    padding: 12px 16px; border-radius: 10px; font-size: 12.5px; max-width: 280px;
    animation: fadeInUp .3s ease both;
  }
</style>
</head>
<body>

<header>
  <div class="brand">
    <div class="brand-mark">
      <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2 3 6v6c0 5 3.8 8.7 9 10 5.2-1.3 9-5 9-10V6l-9-4Z" stroke="white" stroke-width="1.6" stroke-linejoin="round"/>
        <path d="m8.5 12 2.4 2.4L15.7 9" stroke="white" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </div>
    <div>
      <h1>TrafficLens</h1>
      <span class="sub">Real-time road hazard detection</span>
    </div>
  </div>
  <div class="header-right">
    
    <div class="theme-toggle" id="theme-toggle" title="Toggle theme"><div class="knob" id="theme-knob">🌙</div></div>
  </div>
</header>

<div class="shell">
  <div class="grid">

    <!-- LEFT COLUMN -->
    <div>
      <div class="card" style="animation-delay:.02s">
        <div class="card-header">
          <span>Video source</span>
          <div class="tabs">
            <button class="tab-btn active" id="tab-live">Live camera</button>
            <button class="tab-btn" id="tab-upload">Upload video</button>
          </div>
        </div>
        <div class="video-wrap" id="video-wrap">
          <img id="video-feed" class="hidden" alt="Annotated feed">
          <div class="video-badge rec" id="badge-rec" style="display:none;"><span class="dot"></span>LIVE</div>
          <div class="video-badge fps" id="badge-fps" style="display:none;">-- FPS</div>

          <div class="dropzone" id="dropzone">
            <div class="icon-circle">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 16V4m0 0-4 4m4-4 4 4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" stroke="white" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </div>
            <h3 id="dz-title">Start the live camera feed</h3>
            <p id="dz-sub">Click below to connect to the configured camera source, or switch to "Upload video" to test with a dashcam clip.</p>
            <button class="dz-btn" id="dz-action">Connect camera</button>
            <input type="file" id="file-input" accept="video/*">
            <div class="upload-progress" id="upload-progress"><div id="upload-progress-bar"></div></div>
          </div>
        </div>
      </div>

      <div class="stats-row">
        <div class="stat"><div class="stat-value" id="stat-fps">-</div><div class="stat-label">Frames / sec</div></div>
        <div class="stat"><div class="stat-value" id="stat-signs">0</div><div class="stat-label">Signs this frame</div></div>
        <div class="stat stat-accent-2"><div class="stat-value" id="stat-alerts">0</div><div class="stat-label">Active alerts</div></div>
        <div class="stat"><div class="stat-value" id="stat-frames">0</div><div class="stat-label">Total frames</div></div>
      </div>

      <div class="card" id="summary-card">
        <div class="card-header"><span>Session summary</span><span id="summary-duration" style="font-family:var(--mono); font-weight:600;"></span></div>
        <div class="card-body">
          <div class="summary-grid">
            <div class="summary-tile"><div class="v" id="sum-frames">0</div><div class="l">Frames processed</div></div>
            <div class="summary-tile"><div class="v" id="sum-fps">0</div><div class="l">Average FPS</div></div>
            <div class="summary-tile"><div class="v" id="sum-hits">0</div><div class="l">Sign detections</div></div>
            <div class="summary-tile"><div class="v" id="sum-critical">0</div><div class="l">Critical alerts</div></div>
          </div>
          <div class="summary-bars" id="summary-bars"></div>
        </div>
      </div>

      <footer>
        <div class="footer-grid">
          <div class="footer-card">
            <h4>Need a sample dashcam clip?</h4>
            <p>No dashcam handy? Grab a free, no-login-required clip from one of these libraries, then drop it into "Upload video" above.</p>
            <div class="link-row">
              <a class="pill-link" href="https://pixabay.com/videos/search/dashcam/" target="_blank" rel="noopener">Pixabay ↗</a>
              <a class="pill-link" href="https://mixkit.co/free-stock-video/dashcam/" target="_blank" rel="noopener">Mixkit ↗</a>
              <a class="pill-link" href="https://www.pexels.com/search/videos/dash%20cam/" target="_blank" rel="noopener">Pexels ↗</a>
            </div>
          </div>
          <div class="footer-card">
            <h4>Export session data</h4>
            <p>Download the CSV telemetry log (per-frame FPS, detections, and hazard timings) for the most recent session.</p>
            <button class="btn-primary" id="download-csv">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M12 16V4m0 12-4-4m4 4 4-4M4 18v1a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-1" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              Download CSV log
            </button>
            <div class="foot-note" id="csv-note">A log file is generated as soon as a stream starts.</div>
          </div>
        </div>
      </footer>
    </div>

    <!-- RIGHT COLUMN -->
    <div style="display:flex; flex-direction:column; gap:18px;">
      <div class="card" style="animation-delay:.06s">
        <div class="card-header">Active threats</div>
        <div class="card-body"><ul id="alert-list"><li class="empty-msg" id="no-alert">No alerts</li></ul></div>
        <div class="legend">
          <span><span class="swatch" style="background:var(--green)"></span>Advisory</span>
          <span><span class="swatch" style="background:var(--blue)"></span>Informational</span>
          <span><span class="swatch" style="background:var(--amber)"></span>Caution</span>
          <span><span class="swatch" style="background:var(--red)"></span>Critical</span>
        </div>
      </div>

      <div class="card" style="animation-delay:.1s">
        <div class="card-header">Detected signs</div>
        <div class="card-body"><ul id="det-list"><li class="empty-msg" id="no-det">No signs detected</li></ul></div>
      </div>
    </div>

  </div>
</div>

<script>
const socket = io();
let hazardRules = {};      // class_id -> {level, color, label, ...}
let currentSource = null;  // null = live camera, string = uploaded file path
let videoActive = false;

// -- Theme toggle --------------------------------------------------------
const root = document.documentElement;
const themeToggle = document.getElementById('theme-toggle');
const themeKnob = document.getElementById('theme-knob');
function applyTheme(t) {
  root.setAttribute('data-theme', t);
  themeKnob.textContent = t === 'dark' ? '🌙' : '☀️';
  try { localStorage.setItem('tsr-theme', t); } catch (e) {}
}
(function initTheme() {
  let saved = null;
  try { saved = localStorage.getItem('tsr-theme'); } catch (e) {}
  applyTheme(saved || 'dark');
})();
themeToggle.addEventListener('click', () => {
  applyTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
});

// -- Load hazard color/level rules (read-only, for client-side coloring) --
fetch('/api/hazard_rules').then(r => r.json()).then(d => { hazardRules = d.rules || {}; });

function ruleFor(classId) {
  return hazardRules[classId] || { level: 'info', color: '#8b90a8' };
}

// -- Tabs / source switching ----------------------------------------------
const tabLive = document.getElementById('tab-live');
const tabUpload = document.getElementById('tab-upload');
const dropzone = document.getElementById('dropzone');
const dzTitle = document.getElementById('dz-title');
const dzSub = document.getElementById('dz-sub');
const dzAction = document.getElementById('dz-action');
const fileInput = document.getElementById('file-input');
const videoFeed = document.getElementById('video-feed');
const badgeRec = document.getElementById('badge-rec');
const badgeFps = document.getElementById('badge-fps');
const uploadProgress = document.getElementById('upload-progress');
const uploadProgressBar = document.getElementById('upload-progress-bar');

function showToast(msg) {
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

function setTab(mode) {
  tabLive.classList.toggle('active', mode === 'live');
  tabUpload.classList.toggle('active', mode === 'upload');
  if (mode === 'live') {
    dzTitle.textContent = 'Start the live camera feed';
    dzSub.textContent = 'Click below to connect to the configured camera source.';
    dzAction.style.display = 'inline-flex';
    dzAction.textContent = 'Connect camera';
    fileInput.style.display = 'none';
  } else {
    dzTitle.textContent = 'Upload a dashcam video';
    dzSub.textContent = 'Drag & drop a video file here, or click to browse. It will play back through the detector exactly like a live camera.';
    dzAction.style.display = 'inline-flex';
    dzAction.textContent = 'Choose a video file';
  }
}
tabLive.addEventListener('click', () => { setTab('live'); resetVideo(); });
tabUpload.addEventListener('click', () => { setTab('upload'); resetVideo(); });

function resetVideo() {
  videoActive = false;
  videoFeed.classList.add('hidden');
  videoFeed.removeAttribute('src');
  dropzone.style.display = 'flex';
  badgeRec.style.display = 'none';
  badgeFps.style.display = 'none';
  document.getElementById('summary-card').classList.remove('show');
}

dzAction.addEventListener('click', () => {
  if (tabUpload.classList.contains('active')) {
    fileInput.click();
  } else {
    startStream(null);
  }
});

function startStream(sourcePath) {
  currentSource = sourcePath;
  videoActive = true;
  dropzone.style.display = 'none';
  videoFeed.classList.remove('hidden');
  badgeRec.style.display = 'flex';
  badgeFps.style.display = 'block';
  document.getElementById('summary-card').classList.remove('show');
  const qs = sourcePath ? ('?source=' + encodeURIComponent(sourcePath) + '&t=' + Date.now()) : ('?t=' + Date.now());
  videoFeed.src = '/video_feed' + qs;
}

// -- Drag & drop / file upload ---------------------------------------------
['dragover', 'dragenter'].forEach(evt => dropzone.addEventListener(evt, e => {
  if (!tabUpload.classList.contains('active')) return;
  e.preventDefault(); dropzone.classList.add('drag-over');
}));
['dragleave', 'drop'].forEach(evt => dropzone.addEventListener(evt, e => {
  e.preventDefault(); dropzone.classList.remove('drag-over');
}));
dropzone.addEventListener('drop', e => {
  if (!tabUpload.classList.contains('active')) return;
  const f = e.dataTransfer.files[0];
  if (f) uploadFile(f);
});
fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) uploadFile(fileInput.files[0]);
});

function uploadFile(file) {
  const form = new FormData();
  form.append('video', file);
  uploadProgress.classList.add('show');
  uploadProgressBar.style.width = '10%';

  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/upload');
  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) {
      uploadProgressBar.style.width = Math.max(10, (e.loaded / e.total) * 100) + '%';
    }
  };
  xhr.onload = () => {
    uploadProgress.classList.remove('show');
    uploadProgressBar.style.width = '0%';
    if (xhr.status === 200) {
      const data = JSON.parse(xhr.responseText);
      showToast('Video uploaded - starting playback');
      startStream(data.source);
    } else {
      showToast('Upload failed: ' + (JSON.parse(xhr.responseText || '{}').error || xhr.statusText));
    }
  };
  xhr.onerror = () => { uploadProgress.classList.remove('show'); showToast('Upload failed - network error'); };
  xhr.send(form);
}

// -- CSV download -----------------------------------------------------------
document.getElementById('download-csv').addEventListener('click', () => {
  window.location.href = '/api/download/csv';
});

// -- Socket.IO live stats ----------------------------------------------------
socket.on('connect', () => {
  document.getElementById('status-dot').className = 'status-dot live';
});
socket.on('disconnect', () => {
  document.getElementById('status-dot').className = 'status-dot off';
});

let lastVideoEnded = false;

socket.on('stats', (data) => {
  document.getElementById('stat-fps').textContent    = data.fps.toFixed(1);
  document.getElementById('stat-signs').textContent  = data.detections;
  document.getElementById('stat-alerts').textContent = data.alerts.length;
  document.getElementById('stat-frames').textContent = data.frame_count;
  document.getElementById('frame-counter').textContent = `Frame ${data.frame_count}`;
  badgeFps.textContent = data.fps.toFixed(1) + ' FPS';

  // Alerts (4-tier colour coded straight from the hazard rule config)
  const alertList = document.getElementById('alert-list');
  const noAlert   = document.getElementById('no-alert');
  if (data.alerts.length) {
    noAlert.style.display = 'none';
    alertList.innerHTML = '';
    data.alerts.forEach(a => {
      const li = document.createElement('li');
      const color = a.color || '#8b90a8';
      li.style.borderLeftColor = color;
      li.innerHTML = `
        <div class="alert-level"><span class="swatch" style="background:${color}"></span>${a.level}</div>
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
      const rule = ruleFor(d.class_id);
      li.innerHTML = `
        <span class="det-label"><span class="swatch" style="background:${rule.color || '#8b90a8'}"></span>${d.label}</span>
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

  // Detect end-of-video (uploaded clip finished) -> reveal session summary
  if (videoActive && data.video_ended && !lastVideoEnded) {
    lastVideoEnded = true;
    badgeRec.style.display = 'none';
    fetch('/api/summary').then(r => r.json()).then(renderSummary);
  }
  if (data.stream_active) { lastVideoEnded = false; }
});

function renderSummary(s) {
  const card = document.getElementById('summary-card');
  card.classList.add('show');
  document.getElementById('summary-duration').textContent = s.duration_sec ? s.duration_sec + 's' : '';
  document.getElementById('sum-frames').textContent = s.frames_processed;
  document.getElementById('sum-fps').textContent = s.avg_fps;
  document.getElementById('sum-hits').textContent = s.sign_hits;
  document.getElementById('sum-critical').textContent = (s.alert_counts && s.alert_counts.critical) || 0;

  const bars = document.getElementById('summary-bars');
  bars.innerHTML = '';
  const maxCount = (s.top_labels && s.top_labels.length) ? s.top_labels[0][1] : 1;
  (s.top_labels || []).forEach(([label, count]) => {
    const row = document.createElement('div');
    row.className = 'summary-bar-row';
    const pct = Math.round((count / maxCount) * 100);
    row.innerHTML = `<div class="name">${label}</div><div class="summary-bar-track"><div class="summary-bar-fill" style="width:${pct}%"></div></div><div class="count">${count}</div>`;
    bars.appendChild(row);
  });
}
</script>
</body>
</html>
"""


# -- Flask app factory ---------------------------------------------------------
def create_app(pipeline):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "tsr_secret"
    app.config["MAX_CONTENT_LENGTH"] = 512 * 1024 * 1024  # 512 MB upload ceiling
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

    upload_dir = project_path("artifacts/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    @app.route("/")
    def index():
        return render_template_string(DASHBOARD_HTML)

    @app.route("/video_feed")
    def video_feed():
        # Optional ?source=<path> lets the browser play back an uploaded
        # dashcam clip through the exact same detect -> classify -> hazard
        # pipeline used for the live camera. When omitted, behaviour is
        # identical to the original implementation (configured camera_index).
        source = request.args.get("source")
        if source:
            candidate = Path(source)
            try:
                candidate = candidate.resolve()
                upload_dir_resolved = upload_dir.resolve()
                if upload_dir_resolved not in candidate.parents:
                    abort(400, "Invalid source path")
            except Exception:
                abort(400, "Invalid source path")
            source = str(candidate)
        else:
            source = None

        def generate():
            for jpeg_bytes in pipeline.iter_frames(source=source):
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n"
                       + jpeg_bytes + b"\r\n")
        return Response(generate(),
                        mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.route("/api/stats")
    def api_stats():
        return jsonify(pipeline.get_stats())

    @app.route("/api/summary")
    def api_summary():
        return jsonify(pipeline.get_session_summary())

    @app.route("/api/hazard_rules")
    def api_hazard_rules():
        # Read-only view of the existing hazard config (level + colour per
        # sign class) so the UI can colour-code alerts/detections using the
        # same rules already defined in config/sign_classes.py - no new
        # hazard logic is introduced here.
        rules = {}
        for cid, label in SIGN_LABELS.items():
            rule = HAZARD_RULES.get(cid, {"level": "info", "color": "#8b90a8"})
            rules[cid] = {
                "label": label,
                "level": rule.get("level", "info"),
                "color": rule.get("color", "#8b90a8"),
                "message": rule.get("message", label),
                "action": rule.get("action", ""),
            }
        return jsonify({"rules": rules})

    @app.route("/api/upload", methods=["POST"])
    def api_upload():
        file = request.files.get("video")
        if not file or file.filename == "":
            return jsonify({"error": "No file provided"}), 400

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_VIDEO_EXT:
            return jsonify({"error": f"Unsupported file type: {ext}"}), 400

        safe_name = secure_filename(file.filename) or "clip"
        stored_name = f"{uuid.uuid4().hex[:10]}_{safe_name}"
        dest = upload_dir / stored_name
        file.save(dest)

        return jsonify({"source": str(dest), "filename": file.filename})

    @app.route("/api/download/csv")
    def api_download_csv():
        logs_dir = project_path(pipeline.cfg.get("paths", {}).get("logs", "artifacts/logs/"))
        csv_files = sorted(Path(logs_dir).glob("session_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not csv_files:
            return jsonify({"error": "No session log available yet"}), 404
        latest = csv_files[0]
        return send_file(latest, as_attachment=True, download_name=latest.name, mimetype="text/csv")

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