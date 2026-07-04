/**
 * TruthLens — popup.js
 * All event listeners via addEventListener (no inline onclick).
 * Default API: Hugging Face Spaces public deployment.
 */

let API_URL    = 'https://rafat24-truthlens.hf.space';
let useExplain = true;
let predId     = null;
let activeTab  = 'page';

// ── Boot ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await loadSettings();
  bindEvents();
  checkHealth();
  loadPageInfo();
});

// ── Bind all events ───────────────────────────────────────────
function bindEvents() {
  document.getElementById('tab-page').addEventListener('click', () => switchTab('page'));
  document.getElementById('tab-text').addEventListener('click', () => switchTab('text'));
  document.getElementById('tab-cfg' ).addEventListener('click', () => switchTab('cfg'));

  document.getElementById('btn-scan'     ).addEventListener('click', scanPage);
  document.getElementById('btn-go'       ).addEventListener('click', analyseText);
  document.getElementById('btn-correct'  ).addEventListener('click', () => sendFB(true));
  document.getElementById('btn-incorrect').addEventListener('click', () => sendFB(false));
  document.getElementById('btn-again'    ).addEventListener('click', resetRes);
  document.getElementById('api-pill'     ).addEventListener('click', checkHealth);

  document.getElementById('sapi'    ).addEventListener('click', toggleApi);
  document.getElementById('sexplain').addEventListener('click', toggleExplain);

  document.getElementById('ptxt').addEventListener('input', updateWC);
}

// ── Settings ──────────────────────────────────────────────────
async function loadSettings() {
  try {
    const d = await chrome.storage.local.get(['apiUrl', 'useExplain']);
    if (d.apiUrl !== undefined)     API_URL    = d.apiUrl;
    if (d.useExplain !== undefined) useExplain = d.useExplain;
    updateSettingsUI();
  } catch { /* use defaults */ }
}

async function saveSettings() {
  try { await chrome.storage.local.set({ apiUrl: API_URL, useExplain }); }
  catch { /* ignore */ }
}

function updateSettingsUI() {
  document.getElementById('sapi').textContent =
    API_URL.includes('localhost') ? 'localhost' : 'HF Space';
  document.getElementById('sexplain').textContent = useExplain ? 'ON' : 'OFF';
}

function toggleApi() {
  const opts = ['https://rafat24-truthlens.hf.space', 'http://localhost:8000'];
  const idx  = opts.findIndex(o => API_URL === o);
  API_URL = opts[(idx + 1) % opts.length];
  updateSettingsUI();
  saveSettings();
  checkHealth();
}

function toggleExplain() {
  useExplain = !useExplain;
  updateSettingsUI();
  saveSettings();
}

async function checkHealth() {
  const dot = document.getElementById('api-dot');
  const txt = document.getElementById('api-txt');
  dot.className = 'api-dot';
  txt.textContent = 'checking...';
  try {
    const r = await fetch(API_URL + '/health', { signal: AbortSignal.timeout(8000) });
    if (r.ok) {
      const d = await r.json();
      dot.className = 'api-dot on';
      txt.textContent = (d.total_predictions || 0) + ' checked';
    } else throw new Error();
  } catch {
    dot.className = 'api-dot off';
    txt.textContent = 'offline';
  }
}

function switchTab(tab) {
  activeTab = tab;
  ['page','text','cfg'].forEach(t => {
    document.getElementById('tab-' + t).classList.toggle('active', t === tab);
    document.getElementById('panel-' + t).classList.toggle('active', t === tab);
  });
  clearErrors();
  resetRes();
}

async function loadPageInfo() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url) {
      const url = tab.url;
      document.getElementById('page-url').textContent =
        url.length > 55 ? url.slice(0, 55) + '…' : url;
      if (!url.startsWith('http')) {
        document.getElementById('btn-scan').disabled = true;
        document.getElementById('page-url').textContent =
          'Navigate to a news article to scan it.';
      }
    }
  } catch { /* ignore */ }
}

function updateWC() {
  const t  = document.getElementById('ptxt').value.trim();
  const wc = t ? t.split(/\s+/).filter(w => w).length : 0;
  const el = document.getElementById('wc');
  el.textContent = wc + ' word' + (wc !== 1 ? 's' : '');
  el.className = 'wc ' + (wc >= 50 ? 'ok' : wc > 0 ? 'short' : '');
}

async function scanPage() {
  clearErrors();
  const btn = document.getElementById('btn-scan');
  btn.disabled = true;
  btn.innerHTML = '<div style="width:13px;height:13px;border:2px solid rgba(255,255,255,0.25);border-top-color:#fff;border-radius:50%;animation:sp 0.65s linear infinite;display:inline-block;"></div> Extracting…';

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) throw new Error('Could not get current tab.');

    let resp;
    try {
      resp = await chrome.tabs.sendMessage(tab.id, { action: 'extractText' });
    } catch {
      try {
        await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['content.js'] });
        await new Promise(r => setTimeout(r, 500));
        resp = await chrome.tabs.sendMessage(tab.id, { action: 'extractText' });
      } catch (e2) {
        throw new Error('Cannot inject script on this page. Try the Paste Text tab instead.');
      }
    }

    const text = resp && resp.text ? resp.text.trim() : '';
    const wc   = text.split(/\s+/).filter(w => w).length;
    if (!text || wc < 50) {
      throw new Error('Could not extract enough text from this page (need 50+ words). Use the Paste Text tab instead.');
    }

    btn.innerHTML = '<div style="width:13px;height:13px;border:2px solid rgba(255,255,255,0.25);border-top-color:#fff;border-radius:50%;animation:sp 0.65s linear infinite;display:inline-block;"></div> Analysing…';
    await runAnalysis(text);

  } catch (e) {
    showError('page', e.message || 'Failed to scan page. Use Paste Text tab instead.');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>🔍</span> Scan This Article';
  }
}

async function analyseText() {
  clearErrors();
  const text = document.getElementById('ptxt').value.trim();
  if (!text) { showError('text', 'Please paste some article text first.'); return; }
  const wc = text.split(/\s+/).filter(w => w).length;
  if (wc < 50) { showError('text', 'Please provide at least 50 words for analysis.'); return; }

  const btn = document.getElementById('btn-go');
  btn.classList.add('loading');
  btn.disabled = true;
  try {
    await runAnalysis(text);
  } finally {
    btn.classList.remove('loading');
    btn.disabled = false;
  }
}

async function runAnalysis(text) {
  let res;
  try {
    res = await fetch(API_URL + '/predict', {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify({ text })
    });
  } catch {
    const panel = activeTab === 'page' ? 'page' : 'text';
    showError(panel, 'Cannot connect to API. Check internet connection or API status.');
    return;
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    showError(activeTab === 'page' ? 'page' : 'text', err.detail || 'API error. Please try again.');
    return;
  }

  const data = await res.json();
  predId = data.prediction_id;
  showResult(data);
  if (useExplain) fetchExplain(text);
}

function showResult(d) {
  const isFake = d.is_fake;
  const tier   = d.tier;
  const conf   = d.confidence_pct;

  let cls = 'grey';
  if (tier === 'VERIFIED' || tier === 'PROBABLE') cls = isFake ? 'fake' : 'real';
  else if (tier === 'TENTATIVE') cls = 'warn';
  else if (tier === 'HIGH_CONFIDENCE' || tier === 'MEDIUM_CONFIDENCE') cls = isFake ? 'fake' : 'real';
  else if (tier === 'LOW_CONFIDENCE') cls = 'warn';

  document.getElementById('vbox').className = 'vbox ' + cls;

  const fg = document.getElementById('rfg');
  fg.className = 'rfg ' + cls;
  const offset = 157 - (conf / 100) * 157;
  setTimeout(() => { fg.style.strokeDashoffset = offset; }, 60);

  const pEl = document.getElementById('rpct');
  pEl.textContent = Math.round(conf) + '%';
  const clrMap = { fake:'var(--fake)', real:'var(--real)', warn:'var(--warn)', grey:'var(--grey)' };
  pEl.style.color = clrMap[cls];

  document.getElementById('vtier').textContent  = tier.replace('_CONFIDENCE','').replace(/_/g,' ');
  document.getElementById('vtitle').textContent = d.verdict;
  document.getElementById('vact').textContent   = d.action;
  document.getElementById('mspd').textContent   = Math.round(d.processing_ms);
  document.getElementById('mwds').textContent   = d.text_length_words;
  document.getElementById('mid').textContent    = d.prediction_id;

  const res = document.getElementById('res');
  res.style.display = 'block';
  res.classList.add('show');

  document.getElementById('fbbtns').style.display  = 'flex';
  document.getElementById('fbthanks').className    = 'fbthanks';
  document.getElementById('wsec').style.display    = 'none';
}

async function fetchExplain(text) {
  try {
    const r = await fetch(API_URL + '/explain', {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify({ text })
    });
    if (!r.ok) return;
    const d = await r.json();

    const fe = document.getElementById('wfake');
    const re = document.getElementById('wreal');
    fe.innerHTML = '';
    re.innerHTML = '';

    (d.top_fake_words || []).slice(0,6).forEach(w => {
      const s = document.createElement('span');
      s.className = 'wchip fake';
      s.textContent = w.word;
      fe.appendChild(s);
    });
    (d.top_real_words || []).slice(0,6).forEach(w => {
      const s = document.createElement('span');
      s.className = 'wchip real';
      s.textContent = w.word;
      re.appendChild(s);
    });

    if ((d.top_fake_words||[]).length > 0 || (d.top_real_words||[]).length > 0) {
      document.getElementById('wsec').style.display = 'block';
    }
  } catch { /* silent */ }
}

async function sendFB(correct) {
  if (!predId) return;
  document.getElementById('fbbtns').style.display = 'none';
  document.getElementById('fbthanks').className = 'fbthanks show';
  try {
    await fetch(API_URL + '/feedback', {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify({ prediction_id: predId, correct })
    });
  } catch { /* silent */ }
}

function resetRes() {
  const el = document.getElementById('res');
  el.classList.remove('show');
  el.style.display = 'none';
  document.getElementById('rfg').style.strokeDashoffset = '157';
  document.getElementById('wsec').style.display = 'none';
  predId = null;
}

function showError(panel, msg) {
  const el  = document.getElementById('err-' + panel);
  const txt = document.getElementById('err-' + panel + '-txt');
  if (el && txt) { txt.textContent = msg; el.classList.add('show'); }
}
function clearErrors() {
  document.querySelectorAll('.err').forEach(e => e.classList.remove('show'));
}
