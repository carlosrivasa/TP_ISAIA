const API_BASE = "http://localhost:8000";

const promptEl  = document.getElementById("prompt");
const charCount = document.getElementById("char-count");
const submitBtn = document.getElementById("submit-btn");
const userIdEl  = document.getElementById("user-id");
const errorDiv  = document.getElementById("error-region");
const resultEl  = document.getElementById("result-panel");

promptEl.addEventListener("input", () => {
  charCount.textContent = promptEl.value.length;
});

submitBtn.addEventListener("click", async () => {
  const prompt  = promptEl.value.trim();
  const user_id = userIdEl.value.trim();
  if (!prompt || !user_id) return;

  setLoading(true);
  clearError();
  resultEl.classList.add("hidden");

  try {
    const res = await fetch(`${API_BASE}/ambiences`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, user_id }),
    });

    if (!res.ok) { await handleError(res); return; }

    const ambience = await res.json();
    renderAmbience(ambience);
  } catch {
    showError("Network error. Is the backend running?");
  } finally {
    setLoading(false);
  }
});

async function handleError(res) {
  const retryAfter = res.headers.get("Retry-After") || "60";
  if (res.status === 429) {
    showError(`Too many requests. Try again in ${retryAfter}s.`);
  } else if (res.status === 422) {
    showError("Check your prompt — must be 3 to 2000 characters, and User ID is required.");
  } else {
    showError("Generation service is busy. Please try again in a moment.");
  }
}

function setLoading(on) {
  submitBtn.disabled = on;
  submitBtn.textContent = on ? "Generating…" : "Generate Ambience";
}

function clearError() {
  errorDiv.classList.add("hidden");
  errorDiv.textContent = "";
}

function showError(msg) {
  errorDiv.textContent = msg;
  errorDiv.classList.remove("hidden");
}

// ── Rendering ──────────────────────────────────────────────────────────────

function renderAmbience(a) {
  const shuffleBadge = badge(a.shuffle_rule ? "Shuffle ON" : "Shuffle OFF", a.shuffle_rule ? "on" : "");
  let html = `
    <div class="ambience-header">
      <h2>${esc(a.name)}</h2>
      ${shuffleBadge}
    </div>
    <p class="field"><strong>Intension:</strong> ${esc(a.intension)}</p>
    <p class="field"><strong>Público:</strong> ${esc(a.publico)}</p>
  `;

  a.filters.forEach((f, i) => {
    html += `<div class="filter"><h3>Filter ${i + 1}</h3>`;
    html += badge(f.shuffle_rule ? "Shuffle ON" : "Shuffle OFF", f.shuffle_rule ? "on" : "");
    html += badge(f.explicit ? "Explicit YES" : "Explicit NO", f.explicit ? "warn" : "");

    if (f.genres?.length)               html += chips("Genres", f.genres);
    if (f.moods?.length)                html += chips("Moods", f.moods);
    if (f.album_release_dates?.length)  html += chips("Decades", f.album_release_dates);
    if (f.artist_origin_regions?.length)   html += chips("Regions", f.artist_origin_regions);
    if (f.artist_origin_countries?.length) html += chips("Countries", f.artist_origin_countries);

    const FEATURES = [
      "popularity","energy","danceability","valence","tempo",
      "acousticness","instrumentalness","liveness","loudness","speechiness",
    ];
    const rangeLabels = FEATURES.map(k => rangeLabel(k, f[k])).filter(Boolean);
    if (rangeLabels.length) {
      html += `<p class="ranges">${rangeLabels.join(" &nbsp;·&nbsp; ")}</p>`;
    }
    html += "</div>";
  });

  html += `
    <details class="meta">
      <summary>Metadata</summary>
      <p>uuid: ${esc(a.uuid)}</p>
      <p>fingerprint: ${esc(a.fingerprint)}</p>
      <p>created: ${esc(a.created_at)}</p>
    </details>
    <details class="raw">
      <summary>Raw JSON</summary>
      <pre>${esc(JSON.stringify(a, null, 2))}</pre>
    </details>
  `;

  resultEl.innerHTML = html;
  resultEl.classList.remove("hidden");
}

function badge(text, cls = "") {
  return `<span class="badge${cls ? " " + cls : ""}">${esc(text)}</span>`;
}

function chips(label, items) {
  const chipHtml = items.map(i => `<span class="chip">${esc(i)}</span>`).join("");
  return `<div class="chip-group"><strong>${esc(label)}:</strong> ${chipHtml}</div>`;
}

function rangeLabel(key, r) {
  if (!r || (r.min == null && r.max == null)) return "";
  const label = key.charAt(0).toUpperCase() + key.slice(1);
  if (r.min != null && r.max != null) return `${label}&nbsp;${r.min}–${r.max}`;
  if (r.min != null) return `${label}&nbsp;≥${r.min}`;
  return `${label}&nbsp;≤${r.max}`;
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}
