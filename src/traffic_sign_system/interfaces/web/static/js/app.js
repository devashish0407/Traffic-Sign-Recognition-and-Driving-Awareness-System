/**
 * Main application orchestrator for the Traffic Lens dashboard.
 */

import { fetchHazardRules, uploadVideo, exportCSV } from './api.js';
import { connectSocket } from './socket.js';
import { initChart, updateChartWithLiveStats } from './charts.js';
import { 
  setupEventListeners, 
  updateDashboardUI, 
  showUploadProgress, 
  showUploadStatus, 
  resetUploadUI,
  triggerVideoFeedChange,
  sessionId
} from './ui.js';

// Application State
const state = {
  hazardRules: {},
  stats: null,
  socket: null,
  chart: null
};

// Document lifecycle hook
window.addEventListener('DOMContentLoaded', async () => {
  console.log('[App] Initializing Traffic Lens client...');

  // 1. Initialize Analytics Chart
  state.chart = initChart('traffic-chart');

  // 2. Fetch Static Hazard Configs from APIs
  try {
    const data = await fetchHazardRules();
    state.hazardRules = data.rules || {};
    console.log('[App] Hazard rules loaded');
  } catch (err) {
    console.error('[App] Failed to load hazard rules configuration:', err);
  }

  // 3. Connect Socket.IO Stream and Link Telemetry Handlers
  state.socket = connectSocket((stats) => {
    state.stats = stats;
    updateDashboardUI(stats);
    updateChartWithLiveStats(stats);
  });

  // 4. Bind UI Event Handlers
  setupEventListeners({
    onExportCSV: () => {
      exportCSV(sessionId);
    },
    
    onSourceChange: (sourcePath) => {
      resetUploadUI();
      state.stats = null;
    },
    
    onFileUpload: async (file) => {
      resetUploadUI();
      showUploadStatus('Preparing upload...', false);
      
      try {
        const data = await uploadVideo(file, (percent) => {
          showUploadProgress(percent);
        });
        
        showUploadStatus('Upload successful! Initializing video feed...', false);
        console.log('[Upload] Video path configured on backend:', data.source);
        
        // Brief timeout so user can visually verify completed upload progress bar
        setTimeout(() => {
          triggerVideoFeedChange(data.source);
          resetUploadUI();
        }, 1200);
        
      } catch (err) {
        showUploadStatus(err.message, true);
        console.error('[Upload Error]', err);
      }
    }
  });
});
