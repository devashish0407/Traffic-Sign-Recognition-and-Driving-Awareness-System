import { fetchSessionSummary } from './api.js';
import { resetChart } from './charts.js';

export const sessionId = Math.random().toString(36).substring(2, 12);

// DOM Elements cache
const el = {
  pageLoader: document.getElementById('page-loader'),
  navBurger: document.getElementById('nav-burger'),
  navLinks: document.getElementById('nav-links'),
  sysDot: document.getElementById('sys-dot'),
  sysLabel: document.getElementById('sys-label'),
  headerFps: document.getElementById('header-fps'),
  
  tabLive: document.getElementById('tab-live'),
  tabUpload: document.getElementById('tab-upload'),
  panelLive: document.getElementById('panel-live'),
  panelUpload: document.getElementById('panel-upload'),
  
  // The processed video feed runs only on the right panel frame-snap element
  vfeed: document.getElementById('frame-snap'),
  vidCoords: document.getElementById('vid-coords'),
  vidFpsBadge: document.getElementById('vid-fps-badge'),
  visualizerIdleOverlay: document.getElementById('visualizer-idle-overlay'),
  
  dropzone: document.getElementById('dropzone'),
  btnDz: document.getElementById('btn-dz'),
  fileInput: document.getElementById('file-input'),
  dzProgress: document.getElementById('dz-progress'),
  dzFill: document.getElementById('dz-fill'),
  dzStatus: document.getElementById('dz-status'),
  
  signsCount: document.getElementById('signs-count'),
  signsList: document.getElementById('signs-list'),
  noSigns: document.getElementById('no-signs'),
  
  frameSnap: document.getElementById('frame-snap'),
  frameOverlay: document.getElementById('frame-overlay'),
  frameConf: document.getElementById('frame-conf'),
  frameInfer: document.getElementById('frame-infer'),
  
  threatsGrid: document.getElementById('threats-grid'),
  noThreats: document.getElementById('no-threats'),
  
  s1: document.getElementById('s1'),
  s2: document.getElementById('s2'),
  s3: document.getElementById('s3'),
  s4: document.getElementById('s4'),
  
  statFps: document.getElementById('stat-fps'),
  statSigns: document.getElementById('stat-signs'),
  statAlerts: document.getElementById('stat-alerts'),
  statTotal: document.getElementById('stat-total'),
  
  btnCsv: document.getElementById('btn-csv'),
  trafficChart: document.getElementById('traffic-chart'),

  // Overlays & Modal elements
  cameraModal: document.getElementById('camera-modal'),
  btnCameraAllow: document.getElementById('btn-camera-allow'),
  btnCameraDeny: document.getElementById('btn-camera-deny'),
  cameraPermissionDenied: document.getElementById('camera-permission-denied'),
  btnGrantCamera: document.getElementById('btn-grant-camera'),
  
  videoCompletedOverlay: document.getElementById('video-completed-overlay'),
  btnRestartStream: document.getElementById('btn-restart-stream'),
  csFrames: document.getElementById('cs-frames'),
  csFps: document.getElementById('cs-fps'),
  csSigns: document.getElementById('cs-signs'),
  csAlerts: document.getElementById('cs-alerts'),

  // Processing status overlay on the left
  videoProcessingOngoing: document.getElementById('video-processing-ongoing'),
  procFrames: document.getElementById('proc-frames'),
  procFps: document.getElementById('proc-fps'),

  // Playback controls & overlays (on the right panel)
  feedIdleOverlay: document.getElementById('feed-idle-overlay'),
  streamControls: document.getElementById('stream-controls'),
  ctrlStop: document.getElementById('ctrl-stop')
};

let pageLoaded = false;
let activeTab = ''; // Both tabs start inactive on load
let cameraPermission = null; // Request permission every click, do not save in cookies/localStorage
let currentVideoSource = null;
let summaryLoading = false;
let isStreaming = false; // Prevents race conditions from overwriting visualizer src on initial packets

export function setupEventListeners(callbacks) {
  // Mobile Nav Burger
  el.navBurger.addEventListener('click', () => {
    el.navLinks.classList.toggle('active');
  });

  // Tab switching (forces permission check on every click)
  el.tabLive.addEventListener('click', () => {
    currentVideoSource = null;
    cameraPermission = null; // Reset permission to prompt every time
    switchTab('live', callbacks.onSourceChange);
  });
  el.tabUpload.addEventListener('click', () => {
    switchTab('upload', callbacks.onSourceChange);
  });

  // Dropzone file handling
  el.btnDz.addEventListener('click', () => el.fileInput.click());
  el.fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      callbacks.onFileUpload(e.target.files[0]);
    }
  });

  el.dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    el.dropzone.classList.add('dragover');
  });

  el.dropzone.addEventListener('dragleave', () => {
    el.dropzone.classList.remove('dragover');
  });

  el.dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    el.dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      callbacks.onFileUpload(e.dataTransfer.files[0]);
    }
  });

  // Export session CSV
  el.btnCsv.addEventListener('click', () => {
    callbacks.onExportCSV();
  });

  // Camera Permission Modal handlers
  el.btnCameraAllow.addEventListener('click', () => {
    cameraPermission = 'allowed';
    el.cameraModal.classList.remove('active');
    el.cameraPermissionDenied.classList.add('hidden');
    
    // Start camera stream
    startStream(null, callbacks.onSourceChange);
  });

  el.btnCameraDeny.addEventListener('click', () => {
    cameraPermission = 'denied';
    el.cameraModal.classList.remove('active');
    el.cameraPermissionDenied.classList.remove('hidden');
    el.feedIdleOverlay.classList.add('hidden');
    el.vfeed.src = '/api/frame';
  });

  el.btnGrantCamera.addEventListener('click', () => {
    el.cameraModal.classList.add('active');
  });

  // Session completion overlay restart
  el.btnRestartStream.addEventListener('click', () => {
    el.videoCompletedOverlay.classList.add('hidden');
    if (currentVideoSource) {
      triggerVideoFeedChange(currentVideoSource);
    } else {
      cameraPermission = null; // Re-prompt on restart
      switchTab('live', callbacks.onSourceChange);
    }
  });

  // Stop stream processing controls
  el.ctrlStop.addEventListener('click', async () => {
    await stopStreamBackend();
  });
}

async function stopStreamBackend() {
  isStreaming = false;
  try {
    await fetch('/api/stream/stop', { method: 'POST' });
  } catch (err) {
    console.error('Failed to stop stream:', err);
  }
  
  stopStream();
  el.videoProcessingOngoing.classList.add('hidden');
  el.videoCompletedOverlay.classList.add('hidden');
  el.feedIdleOverlay.classList.remove('hidden');
}

function stopStream(onSourceChange) {
  isStreaming = false;
  
  el.tabLive.classList.remove('active');
  el.tabUpload.classList.remove('active');
  activeTab = ''; // Clear tabs highlight
  
  el.sysDot.classList.remove('active');
  el.sysLabel.innerText = 'SYSTEM INACTIVE';
  el.headerFps.innerText = '--';
  el.vidCoords.innerText = 'Cam_08_West | Offline';
  
  el.vfeed.src = '/api/frame';
  el.visualizerIdleOverlay.classList.remove('hidden');
  el.streamControls.classList.add('hidden');
  resetDetectedSigns();
}

function resetDetectedSigns() {
  el.signsCount.innerText = '0 active';
  el.signsList.innerHTML = '';
  el.signsList.classList.add('hidden');
  el.noSigns.classList.remove('hidden');
}

function startStream(sourcePath, onSourceChange) {
  isStreaming = true;
  resetChart(); // Reset analytics chart when starting a new stream
  
  // Clear complete overlays
  el.visualizerIdleOverlay.classList.add('hidden');
  el.videoCompletedOverlay.classList.add('hidden');
  el.feedIdleOverlay.classList.add('hidden');
  el.cameraPermissionDenied.classList.add('hidden');
  el.videoProcessingOngoing.classList.remove('hidden');
  
  // Set ongoing overlay statistics to 0 on start
  el.procFrames.innerText = '0';
  el.procFps.innerText = '--';
  el.vidCoords.innerText = 'Cam_08_West | Processing Ongoing...';
  
  el.streamControls.classList.remove('hidden');
  
  if (sourcePath) {
    el.vfeed.src = `/video_feed?source=${encodeURIComponent(sourcePath)}&session_id=${sessionId}`;
    if (onSourceChange) onSourceChange(sourcePath);
  } else {
    el.vfeed.src = `/video_feed?session_id=${sessionId}`;
    if (onSourceChange) onSourceChange(null);
  }
}

async function switchTab(tab, onSourceChange, specificSource = null) {
  if (activeTab === tab && !specificSource) return;
  activeTab = tab;
  
  // Terminate any previous runs when shifting tabs
  await stopStreamBackend();
  activeTab = tab; // Restore tab variable after reset

  if (tab === 'live') {
    el.tabLive.classList.add('active');
    el.tabUpload.classList.remove('active');
    el.panelLive.classList.remove('hidden');
    el.panelUpload.classList.add('hidden');
    
    if (specificSource) {
      startStream(specificSource, onSourceChange);
    } else {
      if (cameraPermission === 'allowed') {
        startStream(null, onSourceChange);
      } else if (cameraPermission === 'denied') {
        el.cameraPermissionDenied.classList.remove('hidden');
        el.feedIdleOverlay.classList.add('hidden');
        el.vfeed.src = '/api/frame';
      } else {
        el.cameraModal.classList.add('active');
        el.vfeed.src = '/api/frame';
      }
    }
  } else {
    el.tabLive.classList.remove('active');
    el.tabUpload.classList.add('active');
    el.panelLive.classList.add('hidden');
    el.panelUpload.classList.remove('hidden');
  }
}

export function showUploadProgress(percent) {
  el.dzProgress.classList.remove('hidden');
  el.dzFill.style.width = `${percent}%`;
  showUploadStatus(`Uploading: ${percent}%...`, false);
}

export function showUploadStatus(text, isError) {
  el.dzStatus.classList.remove('hidden');
  el.dzStatus.innerText = text;
  
  if (isError) {
    el.dzStatus.className = 'dz-status error';
    el.dzProgress.classList.add('hidden');
  } else if (text.includes('success') || text.includes('Completed')) {
    el.dzStatus.className = 'dz-status success';
  } else {
    el.dzStatus.className = 'dz-status';
  }
}

export function resetUploadUI() {
  el.dzProgress.classList.add('hidden');
  el.dzFill.style.width = '0%';
  el.dzStatus.classList.add('hidden');
}

export function triggerVideoFeedChange(sourcePath) {
  currentVideoSource = sourcePath;
  switchTab('live', null, sourcePath);
}

export function updateDashboardUI(stats) {
  // Dismiss page-level loader on first stats telemetry receipt
  if (!pageLoaded) {
    pageLoaded = true;
    el.pageLoader.classList.add('fade-out');
  }

  const streamActive = stats.stream_active;
  const frameCount = stats.frame_count || 0;

  // Toggle active indicators
  if (streamActive) {
    el.sysDot.classList.add('active');
    el.sysLabel.innerText = 'SYSTEM ACTIVE';
  }

  // Handle Session End
  if (stats.video_ended && stats.frame_count > 0) {
    isStreaming = false;
    el.sysDot.classList.remove('active');
    el.sysLabel.innerText = 'SYSTEM INACTIVE';
    el.videoProcessingOngoing.classList.add('hidden');
    el.vidCoords.innerText = 'Cam_08_West | Processing Completed';
    showSessionCompletedSummary();
  }

  // Header and Stats values updates
  const fpsText = (streamActive && stats.fps) ? stats.fps.toFixed(1) : '0.0';
  el.headerFps.innerText = streamActive ? fpsText : '--';
  el.statFps.innerText = fpsText;
  el.vidFpsBadge.innerText = `${fpsText} FPS`;

  const totalProcessed = stats.frame_count || 0;
  el.statTotal.innerText = totalProcessed;

  // Dynamic GPS Mock coordinates updates
  if (streamActive && totalProcessed > 0) {
    const lat = (37.7749 + Math.sin(totalProcessed / 50) * 0.005).toFixed(4);
    const lon = (-122.4194 + Math.cos(totalProcessed / 50) * 0.005).toFixed(4);
    el.vidCoords.innerText = `Cam_08_West | Lat: ${lat} | Lon: ${lon}`;
    
    // Update processing overlay counters on the left column
    el.procFrames.innerText = totalProcessed;
    el.procFps.innerText = fpsText;
  } else if (!streamActive && totalProcessed > 0 && stats.video_ended) {
    el.vidCoords.innerText = 'Cam_08_West | Processing Completed';
  } else {
    el.vidCoords.innerText = 'Cam_08_West | Offline';
  }

  // Update Frame snapshot and overlays
  if (!streamActive && !isStreaming) {
    // Only query static snapshot frames when the stream is not running
    el.frameSnap.src = `/api/frame?t=${Date.now()}`;
    el.frameSnap.classList.remove('hidden');
  }

  // Render Detected Signs progress items
  const dets = stats.current_dets || [];
  el.statSigns.innerText = dets.length;
  el.signsCount.innerText = `${dets.length} active`;

  if (dets.length === 0) {
    el.signsList.classList.add('hidden');
    el.noSigns.classList.remove('hidden');
  } else {
    el.noSigns.classList.add('hidden');
    el.signsList.classList.remove('hidden');
    
    el.signsList.innerHTML = dets.map((d, index) => {
      const confVal = Math.round((d.confidence || 0.8) * 100);
      const confColor = index % 2 === 0 ? 'var(--color-warning)' : 'var(--color-info)';
      return `
        <li class="sign-item fade-in">
          <div class="sign-meta">
            <span class="sign-name">${d.label || 'Unknown Sign'}</span>
            <span class="sign-conf">${confVal}% Confidence</span>
          </div>
          <div class="sign-bar-outer">
            <div class="sign-bar-inner" style="width: ${confVal}%; background: ${confColor};"></div>
          </div>
        </li>
      `;
    }).join('');

    // Overlay values update based on first sign detection
    const primaryDet = dets[0];
    const topConf = Math.round((primaryDet.confidence || 0.8) * 100);
    el.frameConf.innerText = `CONFIDENCE: ${topConf}%`;
    el.frameInfer.innerText = `${(Math.random() * 5 + 6).toFixed(1)} ms`; // Mock inference latency
  }

  // Render Active Threats Banners
  const alerts = (stats.alerts || []).filter(a => a.level === 'critical' || a.level === 'warning');
  el.statAlerts.innerText = alerts.length;

  if (alerts.length === 0) {
    el.threatsGrid.classList.add('hidden');
    el.noThreats.classList.remove('hidden');
  } else {
    el.noThreats.classList.add('hidden');
    el.threatsGrid.classList.remove('hidden');
    
    el.threatsGrid.innerHTML = alerts.map(a => {
      let cardClass = 'advisory';
      let tagLabel = 'ADVISORY';
      
      if (a.level === 'critical') {
        cardClass = 'critical';
        tagLabel = 'CRITICAL';
      } else if (a.level === 'warning') {
        cardClass = 'caution';
        tagLabel = 'CAUTION';
      }
      
      return `
        <div class="threat-card ${cardClass} fade-in">
          <span class="threat-level ${cardClass}">${tagLabel}</span>
          <span class="threat-title">${a.message}</span>
          <span class="threat-desc">${a.action || 'Observe and adjust driving parameters.'}</span>
        </div>
      `;
    }).join('');
  }
}

async function showSessionCompletedSummary() {
  if (summaryLoading) return;
  summaryLoading = true;
  
  el.vfeed.src = '/api/frame';
  el.visualizerIdleOverlay.classList.remove('hidden');
  el.streamControls.classList.add('hidden');
  resetDetectedSigns();
  
  el.videoCompletedOverlay.classList.remove('hidden');
  
  try {
    const summary = await fetchSessionSummary();
    el.csFrames.innerText = summary.frames_processed || '0';
    el.csFps.innerText = summary.avg_fps ? summary.avg_fps.toFixed(1) : '0.0';
    el.csSigns.innerText = summary.sign_hits || '0';
    
    const totalAlerts = (summary.alert_counts?.critical || 0) + 
                        (summary.alert_counts?.warning || 0) + 
                        (summary.alert_counts?.info || 0);
    el.csAlerts.innerText = totalAlerts;
  } catch (err) {
    console.error('[Summary Loader Error]', err);
  } finally {
    summaryLoading = false;
  }
}

// Scroll reveal for project flow timeline items
export function initTimelineObserver() {
  const items = document.querySelectorAll('.timeline-item');
  if (!items.length) return;
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
      }
    });
  }, {
    threshold: 0.1,
    rootMargin: '0px 0px -40px 0px'
  });
  
  items.forEach(item => observer.observe(item));
}

// Floating Cyber Particle Network Canvas background
function initCyberBackground() {
  const canvas = document.createElement('canvas');
  canvas.id = 'cyber-canvas';
  canvas.style.position = 'fixed';
  canvas.style.top = '0';
  canvas.style.left = '0';
  canvas.style.width = '100vw';
  canvas.style.height = '100vh';
  canvas.style.zIndex = '-2';
  canvas.style.pointerEvents = 'none';
  canvas.style.opacity = '0.3';
  document.body.appendChild(canvas);

  const ctx = canvas.getContext('2d');
  let width = canvas.width = window.innerWidth;
  let height = canvas.height = window.innerHeight;

  window.addEventListener('resize', () => {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
  });

  const particles = [];
  const maxParticles = 65;

  for (let i = 0; i < maxParticles; i++) {
    particles.push({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      size: Math.random() * 2 + 1
    });
  }

  function animate() {
    ctx.clearRect(0, 0, width, height);
    
    // Draw micro-grid lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.015)';
    ctx.lineWidth = 1;
    const gridSize = 45;
    for (let x = 0; x < width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y < height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Update and draw floating neural nodes
    particles.forEach((p, idx) => {
      p.x += p.vx;
      p.y += p.vy;

      if (p.x < 0 || p.x > width) p.vx *= -1;
      if (p.y < 0 || p.y > height) p.vy *= -1;

      ctx.fillStyle = 'rgba(99, 102, 241, 0.45)';
      if (idx % 3 === 0) ctx.fillStyle = 'rgba(34, 197, 94, 0.45)'; // ACCENT COLOR
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();

      // Connect nodes within threshold range
      for (let j = idx + 1; j < particles.length; j++) {
        const p2 = particles[j];
        const dx = p.x - p2.x;
        const dy = p.y - p2.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 110) {
          ctx.strokeStyle = `rgba(99, 102, 241, ${0.12 * (1 - dist / 110)})`;
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();
        }
      }
    });

    requestAnimationFrame(animate);
  }

  animate();
}

// Auto-run animations on DOMContentLoaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    initTimelineObserver();
    initCyberBackground();
  });
} else {
  initTimelineObserver();
  initCyberBackground();
}
