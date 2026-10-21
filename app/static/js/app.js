async function fetchAdvisorData() {
  try {
    const res = await fetch('/api/advisor/sell-first');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderRankingsTable(data.ranked_batches);
    renderBatchCards(data.ranked_batches);
  } catch (err) {
    console.error("Failed to fetch advisor data:", err);
  }
}

function renderRankingsTable(batches) {
  const tbody = document.getElementById('ranked-batches-tbody');
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

// Initial fetch and 10s polling interval
document.addEventListener('DOMContentLoaded', () => {
  fetchAdvisorData();
  setInterval(fetchAdvisorData, 10000);
});
