/**
 * Chart.js controller for traffic density analytics.
 */

let chartInstance = null;

export function initChart(canvasId) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'Cars',
          data: [],
          borderColor: '#5563f2',
          backgroundColor: 'rgba(85, 99, 242, 0.03)',
          borderWidth: 3,
          pointBackgroundColor: '#5563f2',
          pointBorderColor: '#0b0f19',
          pointHoverRadius: 7,
          tension: 0.4,
          fill: true
        },
        {
          label: 'Trucks',
          data: [],
          borderColor: '#06b6d4',
          backgroundColor: 'rgba(6, 182, 212, 0.03)',
          borderWidth: 2,
          pointBackgroundColor: '#06b6d4',
          pointBorderColor: '#0b0f19',
          tension: 0.4,
          fill: true
        },
        {
          label: 'Pedestrians',
          data: [],
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.03)',
          borderWidth: 2,
          pointBackgroundColor: '#10b981',
          pointBorderColor: '#0b0f19',
          tension: 0.4,
          fill: true
        },
        {
          label: 'Active Signs',
          data: [],
          borderColor: '#818cf8',
          backgroundColor: 'rgba(129, 140, 248, 0.03)',
          borderWidth: 2,
          pointBackgroundColor: '#818cf8',
          pointBorderColor: '#0b0f19',
          tension: 0.4,
          fill: true
        },
        {
          label: 'Cautions',
          data: [],
          borderColor: '#f59e0b',
          backgroundColor: 'rgba(245, 158, 11, 0.03)',
          borderWidth: 2,
          pointBackgroundColor: '#f59e0b',
          pointBorderColor: '#0b0f19',
          tension: 0.4,
          fill: true
        },
        {
          label: 'Critical Threats',
          data: [],
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239, 68, 68, 0.03)',
          borderWidth: 2,
          pointBackgroundColor: '#ef4444',
          pointBorderColor: '#0b0f19',
          tension: 0.4,
          fill: true
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false // Use custom HTML legend
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: '#121824',
          titleFont: { family: 'Inter', weight: 'bold' },
          bodyFont: { family: 'Inter' },
          borderColor: '#1e2638',
          borderWidth: 1
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Time Elapsed (Seconds)',
            color: '#8b9bb4',
            font: { family: 'Inter', size: 10, weight: 'bold' }
          },
          grid: {
            color: 'rgba(30, 38, 56, 0.4)',
            borderDash: [5, 5]
          },
          ticks: {
            color: '#8b9bb4',
            font: { family: 'JetBrains Mono', size: 10 }
          }
        },
        y: {
          min: 0,
          suggestedMax: 10,
          title: {
            display: true,
            text: 'Count (Detections & Threat Warnings)',
            color: '#8b9bb4',
            font: { family: 'Inter', size: 10, weight: 'bold' }
          },
          grid: {
            color: 'rgba(30, 38, 56, 0.4)',
            borderDash: [5, 5]
          },
          ticks: {
            color: '#8b9bb4',
            font: { family: 'JetBrains Mono', size: 10 }
          }
        }
      }
    }
  });

  return chartInstance;
}

export function resetChart() {
  if (!chartInstance) return;
  chartInstance.data.labels = [];
  chartInstance.data.datasets.forEach(dataset => {
    dataset.data = [];
  });
  chartInstance.update();
}

export function updateChartWithLiveStats(stats) {
  if (!chartInstance) return;
  
  const frameCount = stats.frame_count || 0;
  if (frameCount === 0) return;
  
  // Throttle updates: Append a new data point once every 30 frames (~1 second)
  if (frameCount % 30 !== 0) return;
  
  const currentDetections = stats.current_dets || [];
  const alerts = stats.alerts || [];
  
  let cars = 0;
  let trucks = 0;
  let peds = 0;

  currentDetections.forEach(d => {
    const lbl = (d.label || '').toLowerCase();
    if (lbl.includes('car') || lbl.includes('vehicle')) cars++;
    else if (lbl.includes('truck') || lbl.includes('bus')) trucks++;
    else if (lbl.includes('pedestrian') || lbl.includes('child')) peds++;
  });

  const numSigns = currentDetections.length;
  
  let cautions = 0;
  let criticals = 0;
  alerts.forEach(a => {
    if (a.level === 'critical') criticals++;
    else if (a.level === 'warning') cautions++;
  });

  const label = Math.floor(frameCount / 30) + 's';
  
  chartInstance.data.labels.push(label);
  chartInstance.data.datasets[0].data.push(cars);
  chartInstance.data.datasets[1].data.push(trucks);
  chartInstance.data.datasets[2].data.push(peds);
  chartInstance.data.datasets[3].data.push(numSigns);
  chartInstance.data.datasets[4].data.push(cautions);
  chartInstance.data.datasets[5].data.push(criticals);
  
  // Maintain a moving window of the last 20 seconds to keep chart legible and scrolling
  if (chartInstance.data.labels.length > 20) {
    chartInstance.data.labels.shift();
    chartInstance.data.datasets.forEach(dataset => {
      dataset.data.shift();
    });
  }
  
  chartInstance.update('none');
}
