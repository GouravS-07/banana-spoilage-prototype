/**
 * Banana Spoilage Advisor Frontend Logic
 * Supports real-time prioritization ranking, gas-sensor monitoring, baseline tracking,
 * interactive SVG historical graphing, and CSV export.
 */

let currentActiveBatches = [];
let currentTelemetryPoints = [];
let currentGasMetrics = null;

async function fetchAdvisorData() {
  try {
    const res = await fetch('/api/advisor/sell-first');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    currentActiveBatches = data.ranked_batches || [];
    renderRankingsTable(currentActiveBatches);
    renderBatchCards(currentActiveBatches);
    updateBatchDropdowns(currentActiveBatches);
  } catch (err) {
    console.error("Failed to fetch advisor data:", err);
  }
}

function updateBatchDropdowns(batches) {
  if (!batches || batches.length === 0) return;
  const selectIds = ['analytics-batch-select', 'sim-batch-id', 'vis-batch-id'];
  selectIds.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const currentVal = el.value;
    const currentOptions = Array.from(el.options).map(o => o.value);
    const newOptions = batches.map(b => b.batch_id);
    // Only update if options changed to prevent interrupting user interaction
    const optionsChanged = currentOptions.length !== newOptions.length ||
      currentOptions.some((val, idx) => val !== newOptions[idx]);
    if (optionsChanged) {
      const optionsHtml = batches.map(b => `<option value="${b.batch_id}">${b.batch_id} (${b.variety})</option>`).join('');
      el.innerHTML = optionsHtml;
      if (currentVal && batches.some(b => b.batch_id === currentVal)) {
        el.value = currentVal;
      }
    }
  });
}

function renderRankingsTable(batches) {
  const tbody = document.getElementById('ranked-batches-tbody');
  if (!tbody) return;
  if (!batches || batches.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">No active batches found.</td></tr>';
    return;
  }

  tbody.innerHTML = batches.map(b => {
    const tierBadgeClass = `badge-tier-${b.risk_tier.toLowerCase()}`;
    const rankClass = b.rank === 1 ? 'rank-pill rank-1' : 'rank-pill';
    
    // Sensor Provenance badge
    const isSim = b.data_provenance.sensor_provenance === 'SIMULATED';
    const sensorBadge = isSim 
      ? '<span class="badge badge-simulated" title="Simulated time-series sensor telemetry">SENSOR: SIMULATED</span>' 
      : '<span class="badge badge-hardware" title="Physical hardware authenticated via device token">SENSOR: HARDWARE</span>';

    // Vision Provenance badge
    const vProv = b.data_provenance.vision_provenance;
    let visionBadge = '<span class="badge badge-vision-none">VISION: NONE</span>';
    if (vProv === 'REAL_MODEL') {
      visionBadge = '<span class="badge badge-vision-real" title="Real Color-RF Model Inference (Uncalibrated model agreement)">VISION: COLOR-RF</span>';
    } else if (vProv === 'PLACEHOLDER_MOCK') {
      visionBadge = '<span class="badge badge-vision-mock" title="Demonstration placeholder heuristic">VISION: MOCK</span>';
    }

    const completenessTag = b.assessment_completeness !== 'COMPLETE'
      ? `<br><small style="color:#d97706; font-size:11px;">⚠️ ${b.assessment_completeness}</small>`
      : '';

    return `
      <tr>
        <td><span class="${rankClass}">${b.rank}</span></td>
        <td><strong>${b.batch_id}</strong></td>
        <td>${b.variety}</td>
        <td><span style="font-weight:700; font-size:15px;">${b.risk_score}</span> / 100</td>
        <td><span class="badge ${tierBadgeClass}">${b.risk_tier}</span></td>
        <td><code>${b.recommendation}</code></td>
        <td>
          <div>${b.primary_driver}</div>
          ${completenessTag}
        </td>
        <td>
          <div style="display:flex; flex-direction:column; gap:4px;">
            ${sensorBadge}
            ${visionBadge}
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function renderBatchCards(batches) {
  const container = document.getElementById('batch-cards-container');
  if (!container) return;
  if (!batches || batches.length === 0) {
    container.innerHTML = '<p>No batch telemetry records available.</p>';
    return;
  }

  container.innerHTML = batches.map(b => {
    const tier = b.risk_tier.toLowerCase();
    const lr = b.latest_readings;
    const isSim = b.data_provenance.sensor_provenance === 'SIMULATED';
    const sensorBadge = isSim 
      ? '<span class="badge badge-simulated">SENSOR: SIMULATED</span>' 
      : '<span class="badge badge-hardware">SENSOR: HARDWARE</span>';

    const vProv = b.data_provenance.vision_provenance;
    let visionBadge = '<span class="badge badge-vision-none">VISION: NONE</span>';
    if (vProv === 'REAL_MODEL') {
      visionBadge = '<span class="badge badge-vision-real">VISION: COLOR-RF</span>';
    } else if (vProv === 'PLACEHOLDER_MOCK') {
      visionBadge = '<span class="badge badge-vision-mock">VISION: MOCK</span>';
    }

    return `
      <div class="batch-card ${tier}">
        <div class="batch-header">
          <div>
            <strong>${b.batch_id}</strong> (${b.variety})
          </div>
          <div style="display:flex; flex-direction:column; gap:2px; align-items:flex-end;">
            ${sensorBadge}
            ${visionBadge}
          </div>
        </div>
        <div class="metric-row">
          <span class="metric-label">Composite Risk:</span>
          <span class="metric-value">${b.risk_score} <span class="badge badge-tier-${tier}">${b.risk_tier}</span></span>
        </div>
        <div class="metric-row">
          <span class="metric-label">Temperature:</span>
          <span class="metric-value">${lr.temperature_c !== null ? lr.temperature_c + ' °C' : 'N/A'}</span>
        </div>
        <div class="metric-row">
          <span class="metric-label">Humidity:</span>
          <span class="metric-value">${lr.relative_humidity_pct !== null ? lr.relative_humidity_pct + ' %' : 'N/A'}</span>
        </div>
        <div class="metric-row">
          <span class="metric-label">Gas Ratio (Rs/R0):</span>
          <span class="metric-value">${lr.gas_raw !== null ? lr.gas_raw : 'N/A'}</span>
        </div>
        <div class="metric-row">
          <span class="metric-label">Ripeness Stage:</span>
          <span class="metric-value">${lr.ripeness_stage !== null ? lr.ripeness_stage : 'Pending / Missing'}</span>
        </div>
        <div class="metric-row" style="border:none; margin-top: 6px;">
          <span class="metric-label">Status:</span>
          <span style="font-size:11px; color:#475569;">${b.assessment_completeness}</span>
        </div>
      </div>
    `;
  }).join('');
}

// =============================================================================
// GAS MONITORING, HISTORICAL ANALYTICS & SVG GRAPHING
// =============================================================================

async function loadAnalyticsForSelectedBatch() {
  const select = document.getElementById('analytics-batch-select');
  const batchId = select ? select.value : 'BATCH-001-COLD';

  try {
    const res = await fetch(`/api/telemetry/history?batch_id=${encodeURIComponent(batchId)}&limit=150`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    
    currentTelemetryPoints = data.points || [];
    currentGasMetrics = data.gas_metrics || null;

    renderGasKPIs(data.gas_metrics);
    renderGasChart(data.points, data.gas_metrics);
    renderClimateChart(data.points);
  } catch (err) {
    console.error("Failed to load historical analytics:", err);
  }
}

function renderGasKPIs(metrics) {
  const container = document.getElementById('gas-kpi-container');
  if (!container || !metrics) return;

  let statusBadge = '<span class="badge badge-tier-low">BASELINE STABLE</span>';
  if (metrics.trend_status === 'CRITICAL_FERMENTATION_RISK') {
    statusBadge = '<span class="badge badge-tier-critical">CRITICAL FERMENTATION RISK</span>';
  } else if (metrics.trend_status === 'ELEVATED_VOLATILE_SURGE') {
    statusBadge = '<span class="badge badge-tier-high">ELEVATED VOLATILE SURGE</span>';
  } else if (metrics.trend_status === 'MILD_VOLATILE_ACTIVITY') {
    statusBadge = '<span class="badge badge-tier-moderate">MILD VOLATILE ACTIVITY</span>';
  }

  const curVal = metrics.current_ratio !== null ? metrics.current_ratio.toFixed(3) : 'N/A';
  const baseVal = metrics.baseline_ratio !== null ? metrics.baseline_ratio.toFixed(3) : '0.980';
  const devVal = metrics.deviation_pct !== null ? `${metrics.deviation_pct.toFixed(1)}%` : '0.0%';

  container.innerHTML = `
    <div class="kpi-card">
      <div class="kpi-title">Current Gas Ratio (Rs/R0)</div>
      <div class="kpi-value" style="color:#0284c7;">${curVal}</div>
      <div class="kpi-subtext">Direction: <strong>${metrics.trend_direction || 'STABLE'}</strong></div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Initial Baseline Reference (R0)</div>
      <div class="kpi-value">${baseVal}</div>
      <div class="kpi-subtext">Established from batch onset</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Volatile Deviation (Δ%)</div>
      <div class="kpi-value" style="color: ${metrics.deviation_pct > 20 ? '#ef4444' : '#059669'};">-${devVal}</div>
      <div class="kpi-subtext">Resistance reduction from baseline</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Volatiles Status</div>
      <div style="margin: 6px 0;">${statusBadge}</div>
      <div class="kpi-subtext">${metrics.sample_count || 0} simulated samples</div>
    </div>
  `;
}

function renderGasChart(points, metrics) {
  const svg = document.getElementById('gas-chart-svg');
  const tooltip = document.getElementById('gas-chart-tooltip');
  if (!svg) return;

  const width = svg.clientWidth || 500;
  const height = 240;
  const padding = { top: 20, right: 30, bottom: 35, left: 45 };

  if (!points || points.length === 0) {
    svg.innerHTML = `<text x="${width/2}" y="${height/2}" text-anchor="middle" fill="#94a3b8" font-size="13">No historical telemetry points available</text>`;
    return;
  }

  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;

  // Gas ratio range typically [0.50, 1.05]
  const minY = 0.50;
  const maxY = 1.05;

  const scaleX = (idx) => padding.left + (idx / Math.max(1, points.length - 1)) * plotW;
  const scaleY = (val) => padding.top + plotH - ((val - minY) / (maxY - minY)) * plotH;

  // Build grid lines
  let gridHtml = '';
  [0.6, 0.75, 0.9, 1.0].forEach(v => {
    const y = scaleY(v);
    gridHtml += `<line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" stroke="#f1f5f9" stroke-width="1" />`;
    gridHtml += `<text x="${padding.left - 6}" y="${y + 4}" text-anchor="end" font-size="10" fill="#94a3b8">${v.toFixed(2)}</text>`;
  });

  // Reference lines: Baseline R0 (Green dashed), Surge threshold 0.75 (Red dashed)
  const baseVal = metrics && metrics.baseline_ratio ? metrics.baseline_ratio : 0.98;
  const baseY = scaleY(baseVal);
  const surgeY = scaleY(0.75);

  const baselineRefLine = `<line x1="${padding.left}" y1="${baseY}" x2="${width - padding.right}" y2="${baseY}" stroke="#10b981" stroke-width="1.5" stroke-dasharray="4 3" />`;
  const surgeRefLine = `<line x1="${padding.left}" y1="${surgeY}" x2="${width - padding.right}" y2="${surgeY}" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="4 3" />`;

  // Build path
  const lineCoords = points.map((p, idx) => `${scaleX(idx)},${scaleY(p.gas_resistance_raw)}`).join(' L ');
  const pathHtml = `<path d="M ${lineCoords}" fill="none" stroke="#0284c7" stroke-width="2.5" />`;

  // Build hover dots
  let dotsHtml = '';
  points.forEach((p, idx) => {
    const cx = scaleX(idx);
    const cy = scaleY(p.gas_resistance_raw);
    dotsHtml += `
      <circle cx="${cx}" cy="${cy}" r="4" fill="#0284c7" stroke="#ffffff" stroke-width="1.5" class="chart-point"
        data-time="${p.timestamp ? p.timestamp.substring(11, 19) : ''}"
        data-val="${p.gas_resistance_raw.toFixed(3)}"
        data-prov="${p.provenance}"
      />
    `;
  });

  svg.innerHTML = `
    ${gridHtml}
    ${baselineRefLine}
    ${surgeRefLine}
    ${pathHtml}
    ${dotsHtml}
    <text x="${padding.left}" y="${height - 8}" font-size="10" fill="#94a3b8">Earliest Record</text>
    <text x="${width - padding.right}" y="${height - 8}" text-anchor="end" font-size="10" fill="#94a3b8">Latest (${points.length} pts)</text>
  `;

  // Attach hover events
  svg.querySelectorAll('.chart-point').forEach(pt => {
    pt.addEventListener('mouseenter', (e) => {
      const time = pt.getAttribute('data-time');
      const val = pt.getAttribute('data-val');
      const prov = pt.getAttribute('data-prov');
      const cx = parseFloat(pt.getAttribute('cx')) || 0;
      const cy = parseFloat(pt.getAttribute('cy')) || 0;
      const tipLeft = Math.max(10, Math.min(width - 200, cx - 30));
      const tipTop = Math.max(10, cy - 35);
      tooltip.style.display = 'block';
      tooltip.style.left = `${tipLeft}px`;
      tooltip.style.top = `${tipTop}px`;
      tooltip.innerHTML = `Time: ${time} | Gas: <strong>${val}</strong> [${prov}]`;
    });
    pt.addEventListener('mouseleave', () => {
      tooltip.style.display = 'none';
    });
  });
}

function renderClimateChart(points) {
  const svg = document.getElementById('climate-chart-svg');
  const tooltip = document.getElementById('climate-chart-tooltip');
  if (!svg) return;

  const width = svg.clientWidth || 500;
  const height = 240;
  const padding = { top: 20, right: 35, bottom: 35, left: 40 };

  if (!points || points.length === 0) {
    svg.innerHTML = `<text x="${width/2}" y="${height/2}" text-anchor="middle" fill="#94a3b8" font-size="13">No climate telemetry points available</text>`;
    return;
  }

  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;

  // Temperature axis: [10°C, 35°C]
  const minT = 10.0;
  const maxT = 35.0;
  // Humidity axis: [50%, 100%]
  const minH = 50.0;
  const maxH = 100.0;

  const scaleX = (idx) => padding.left + (idx / Math.max(1, points.length - 1)) * plotW;
  const scaleTemp = (val) => padding.top + plotH - ((val - minT) / (maxT - minT)) * plotH;
  const scaleHum = (val) => padding.top + plotH - ((val - minH) / (maxH - minH)) * plotH;

  // Grid
  let gridHtml = '';
  [15, 20, 25, 30].forEach(t => {
    const y = scaleTemp(t);
    gridHtml += `<line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" stroke="#f1f5f9" stroke-width="1" />`;
    gridHtml += `<text x="${padding.left - 6}" y="${y + 4}" text-anchor="end" font-size="10" fill="#f97316">${t}°</text>`;
  });
  [60, 80, 95].forEach(h => {
    const y = scaleHum(h);
    gridHtml += `<text x="${width - padding.right + 6}" y="${y + 4}" font-size="10" fill="#06b6d4">${h}%</text>`;
  });

  // Target safe zone for Temp (13-15°C) shaded
  const yOptMin = scaleTemp(13.0);
  const yOptMax = scaleTemp(15.0);
  const optZone = `<rect x="${padding.left}" y="${yOptMax}" width="${plotW}" height="${yOptMin - yOptMax}" fill="#10b981" fill-opacity="0.08" />`;

  // Paths
  const tempCoords = points.map((p, idx) => `${scaleX(idx)},${scaleTemp(p.temperature_c)}`).join(' L ');
  const humCoords = points.map((p, idx) => `${scaleX(idx)},${scaleHum(p.relative_humidity_pct)}`).join(' L ');

  const tempPath = `<path d="M ${tempCoords}" fill="none" stroke="#f97316" stroke-width="2" />`;
  const humPath = `<path d="M ${humCoords}" fill="none" stroke="#06b6d4" stroke-width="2" stroke-dasharray="3 2" />`;

  // Dots
  let dotsHtml = '';
  points.forEach((p, idx) => {
    const cx = scaleX(idx);
    const cyT = scaleTemp(p.temperature_c);
    dotsHtml += `
      <circle cx="${cx}" cy="${cyT}" r="3.5" fill="#f97316" class="climate-point"
        data-time="${p.timestamp ? p.timestamp.substring(11, 19) : ''}"
        data-temp="${p.temperature_c.toFixed(1)}"
        data-hum="${p.relative_humidity_pct.toFixed(1)}"
        data-prov="${p.provenance}"
      />
    `;
  });

  svg.innerHTML = `
    ${gridHtml}
    ${optZone}
    ${tempPath}
    ${humPath}
    ${dotsHtml}
    <text x="${padding.left}" y="${height - 8}" font-size="10" fill="#94a3b8">Past Records</text>
    <text x="${width - padding.right}" y="${height - 8}" text-anchor="end" font-size="10" fill="#94a3b8">Latest</text>
  `;

  svg.querySelectorAll('.climate-point').forEach(pt => {
    pt.addEventListener('mouseenter', (e) => {
      const time = pt.getAttribute('data-time');
      const temp = pt.getAttribute('data-temp');
      const hum = pt.getAttribute('data-hum');
      const prov = pt.getAttribute('data-prov');
      const cx = parseFloat(pt.getAttribute('cx')) || 0;
      const cy = parseFloat(pt.getAttribute('cy')) || 0;
      const tipLeft = Math.max(10, Math.min(width - 240, cx - 40));
      const tipTop = Math.max(10, cy - 35);
      tooltip.style.display = 'block';
      tooltip.style.left = `${tipLeft}px`;
      tooltip.style.top = `${tipTop}px`;
      tooltip.innerHTML = `Time: ${time} | Temp: <strong>${temp}°C</strong> | RH: <strong>${hum}%</strong> [${prov}]`;
    });
    pt.addEventListener('mouseleave', () => {
      tooltip.style.display = 'none';
    });
  });
}

// =============================================================================
// CSV EXPORT ENGINE (ASYNC BLOB STREAMING & UI PROTECTION)
// =============================================================================

let isExporting = false;

async function downloadCSV(url, fallbackFilename, buttonEl) {
  if (isExporting) {
    console.warn("CSV export already in progress. Ignoring duplicate request.");
    return;
  }
  isExporting = true;
  const originalHtml = buttonEl ? buttonEl.innerHTML : null;
  if (buttonEl) {
    buttonEl.disabled = true;
    buttonEl.innerHTML = '⏳ Exporting...';
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout guard

    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'text/csv' },
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      let detail = `Server responded with HTTP ${res.status}`;
      try {
        const errData = await res.json();
        if (errData && errData.detail) detail = errData.detail;
      } catch (_) {}
      alert(`Export failed: ${detail}`);
      return;
    }

    // Parse filename from Content-Disposition header if available
    let filename = fallbackFilename;
    const disposition = res.headers.get('Content-Disposition');
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename=["']?([^"';]+)["']?/i);
      if (match && match[1]) {
        filename = match[1].trim();
      }
    }

    const blob = await res.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    // Revoke blob URL after short delay to free memory
    setTimeout(() => {
      window.URL.revokeObjectURL(blobUrl);
    }, 1500);
  } catch (err) {
    if (err.name === 'AbortError') {
      alert("CSV export request timed out. Please try again.");
    } else {
      console.error("Export error:", err);
      alert(`Failed to download CSV: ${err.message || 'Network error'}`);
    }
  } finally {
    isExporting = false;
    if (buttonEl && originalHtml) {
      buttonEl.disabled = false;
      buttonEl.innerHTML = originalHtml;
    }
  }
}

function exportSelectedBatchCSV(e) {
  const select = document.getElementById('analytics-batch-select');
  const batchId = select ? select.value : 'BATCH-001-COLD';
  const btn = (e && e.currentTarget) || document.getElementById('btn-export-batch');
  downloadCSV(`/api/telemetry/export/csv?batch_id=${encodeURIComponent(batchId)}`, `banana_telemetry_${batchId}.csv`, btn);
}

function exportAllBatchesCSV(e) {
  const btn = (e && e.currentTarget) || document.getElementById('btn-export-all');
  downloadCSV('/api/telemetry/export/csv', 'banana_telemetry_all_batches.csv', btn);
}

// =============================================================================
// INGESTION & SUBMISSION HANDLERS
// =============================================================================

async function submitSimulatedTelemetry(e) {
  e.preventDefault();
  const batchId = document.getElementById('sim-batch-id').value;
  const temp = parseFloat(document.getElementById('sim-temp').value);
  const rh = parseFloat(document.getElementById('sim-rh').value);
  const gas = parseFloat(document.getElementById('sim-gas').value);

  try {
    const res = await fetch('/api/telemetry/simulated', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        batch_id: batchId,
        temperature_c: temp,
        relative_humidity_pct: rh,
        gas_resistance_raw: gas,
        sensor_device_id: 'WEB_TEST_SIMULATOR'
      })
    });
    if (!res.ok) {
      const err = await res.json();
      alert(`Error: ${JSON.stringify(err)}`);
      return;
    }
    await fetchAdvisorData();
    await loadAnalyticsForSelectedBatch();
  } catch (err) {
    alert(`Failed to post telemetry: ${err.message}`);
  }
}

async function submitVisionImage(e) {
  e.preventDefault();
  const batchId = document.getElementById('vis-batch-id').value;
  const fileInput = document.getElementById('vis-file');
  const resultDiv = document.getElementById('vis-result');

  if (!fileInput.files || fileInput.files.length === 0) {
    alert("Please select an image file.");
    return;
  }

  const formData = new FormData();
  formData.append('batch_id', batchId);
  formData.append('file', fileInput.files[0]);

  try {
    resultDiv.textContent = "Uploading image...";
    const res = await fetch('/api/vision/assess', {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const err = await res.json();
      resultDiv.textContent = `Upload failed: ${JSON.stringify(err)}`;
      return;
    }
    const data = await res.json();
    const isMock = data.is_mock_inference;
    const modelTag = isMock 
      ? '<span class="badge badge-vision-mock">MOCK PLACEHOLDER</span>' 
      : '<span class="badge badge-vision-real">REAL COLOR-RF MODEL</span>';
    const confDesc = isMock ? 'fixed' : `uncalibrated model agreement: ${(data.confidence_score * 100).toFixed(1)}%`;
    resultDiv.innerHTML = `✅ Assessment complete! Stage: <strong>${data.ripeness_stage}</strong> (${confDesc}) | ${modelTag}`;
    await fetchAdvisorData();
  } catch (err) {
    resultDiv.textContent = `Upload error: ${err.message}`;
  }
}

// Initial fetch, 10s polling interval, and responsive resize listener
let resizeDebounceTimer = null;
window.addEventListener('resize', () => {
  clearTimeout(resizeDebounceTimer);
  resizeDebounceTimer = setTimeout(() => {
    if (currentTelemetryPoints && currentTelemetryPoints.length > 0) {
      renderGasChart(currentTelemetryPoints, currentGasMetrics);
      renderClimateChart(currentTelemetryPoints);
    }
  }, 150);
});

document.addEventListener('DOMContentLoaded', () => {
  fetchAdvisorData().then(() => {
    loadAnalyticsForSelectedBatch();
  });
  setInterval(fetchAdvisorData, 10000);
});
