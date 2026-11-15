/*
 * G.O.S. dashboard: live data from the research API (gateway/services/api.py, port 5000).
 * Everything shown comes from the database; nothing is simulated in the browser.
 * All values are inserted with textContent, never innerHTML, so data cannot inject markup.
 */
// The API runs on the same host, port 5000. Not configurable from the URL on purpose: a link
// could otherwise point the dashboard (and the token) at another server.
const API = `${location.protocol}//${location.hostname}:5000`;
const TOKEN_KEY = 'gos_api_token';

function token() {
    try { return localStorage.getItem(TOKEN_KEY) || ''; } catch { return ''; }
}
const REFRESH_MS = 15000;

async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (options.method && options.method !== 'GET' && token()) headers.Authorization = `Bearer ${token()}`;
    const r = await fetch(API + path, { ...options, headers });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(body.message || `${r.status} ${r.statusText}`);
    return body;
}

const fmt = (v, d = 1) => (v === null || v === undefined || Number.isNaN(v)) ? '-' : Number(v).toFixed(d);
const ago = (iso) => {
    if (!iso) return '-';
    const s = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
    if (s < 90) return `${s} s ago`;
    if (s < 5400) return `${Math.round(s / 60)} min ago`;
    return `${Math.round(s / 3600)} h ago`;
};
const time = (iso) => iso ? new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '-';

function fill(tableId, rows, emptyText) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    tbody.replaceChildren();
    if (!rows.length) {
        const tr = tbody.insertRow();
        const td = tr.insertCell();
        td.colSpan = document.querySelectorAll(`#${tableId} th`).length;
        td.className = 'muted';
        td.textContent = emptyText;
        return;
    }
    for (const { cells, cls } of rows) {
        const tr = tbody.insertRow();
        if (cls) tr.className = cls;
        for (const c of cells) tr.insertCell().textContent = c;
    }
}

async function refreshNodes() {
    const nodes = await api('/api/nodes');
    const select = document.getElementById('led-node');
    const known = new Set([...select.options].map(o => o.value));
    for (const n of nodes) {
        if (!known.has(n.node_id)) select.add(new Option(n.node_id, n.node_id));
    }
    fill('nodes', nodes.map(n => ({
        cls: (Date.now() - new Date(n.last_seen).getTime()) > 300000 ? 'stale' : '',
        cells: [n.node_id, fmt(n.temp_c), fmt(n.humidity_pct, 0), fmt(n.light_lux, 0), fmt(n.par_umol, 0),
            n.battery_mv ?? '-', n.charging === null || n.charging === undefined ? '-' : (n.charging ? 'yes' : 'no'),
            ago(n.last_seen)],
    })), 'No node has reported in the last 24 h.');
}

async function refreshPlants() {
    const plants = await api('/api/plant');
    fill('plants', plants.map(p => {
        const sp = p.led_setpoint;
        const f = p.forecast && p.forecast.vpd_kpa;
        return {
            cls: sp && sp.source === 'manual' ? 'manual' : '',
            cells: [p.node_id, `${fmt(p.ppfd_ambient, 0)} + ${fmt(p.ppfd_led, 0)}`,
                `${fmt(100 * p.blue_fraction, 0)} %`, fmt(p.vpd_kpa, 2), fmt(p.photosynthesis_umol_m2_s),
                fmt(p.transpiration_g_m2_h, 0), fmt(p.dli_mol_m2, 2),
                sp ? `${fmt(sp.blue_pct, 0)} / ${fmt(sp.red_pct, 0)} %` : 'off (no setpoint)',
                sp ? sp.source : '-',
                f && f.length ? `${fmt(f[0], 2)} .. ${fmt(f[f.length - 1], 2)} (${p.forecast.backend})` : '-'],
        };
    }), 'No plant state yet: the biology engine writes one row per node per minute.');
}

async function refreshCommands() {
    const cmds = await api('/api/led/commands?limit=15');
    fill('commands', cmds.map(c => ({
        cls: c.safety_notes ? 'flagged' : '',
        cells: [time(c.time), c.node_id, `${c.blue_pct} / ${c.red_pct} %`,
            c.requested_blue === null ? 'none' : `${fmt(c.requested_blue, 0)} / ${fmt(c.requested_red, 0)} %`,
            c.safety_notes || 'ok'],
    })), 'No commands yet: they go out in the reply to each real node packet.');
}

async function refreshEvents() {
    const events = await api('/api/events?limit=10');
    fill('events', events.map(e => ({
        cls: e.severity >= 4 ? 'flagged' : '',
        cells: [time(e.time), e.type || '-', e.severity ?? '-', e.sector || '-', e.description || ''],
    })), 'No events logged.');
}

async function refreshAll() {
    const status = document.getElementById('api-status');
    const results = await Promise.allSettled([refreshNodes(), refreshPlants(), refreshCommands(), refreshEvents()]);
    const failed = results.filter(r => r.status === 'rejected');
    status.textContent = failed.length ? `API error: ${failed[0].reason.message}` : 'live';
    status.className = failed.length ? 'pill bad' : 'pill ok';
    document.getElementById('updated').textContent = `updated ${new Date().toLocaleTimeString()}`;
}

document.getElementById('led-form').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const msg = document.getElementById('led-msg');
    try {
        const r = await api('/api/led', {
            method: 'POST', body: JSON.stringify({
                node: document.getElementById('led-node').value,
                blue_pct: Number(document.getElementById('led-blue').value),
                red_pct: Number(document.getElementById('led-red').value),
                minutes: Number(document.getElementById('led-min').value),
            }),
        });
        msg.textContent = r.message;
        refreshPlants();
    } catch (e) {
        msg.textContent = `Not set: ${e.message}`;
    }
});

document.getElementById('led-auto').addEventListener('click', async () => {
    const node = document.getElementById('led-node').value;
    const msg = document.getElementById('led-msg');
    try {
        const r = await api('/api/led/override' + (node === 'ALL' ? '' : `?node=${encodeURIComponent(node)}`),
            { method: 'DELETE' });
        msg.textContent = `Manual settings ended: ${r.ended}. The controller takes over at its next run.`;
        refreshPlants();
    } catch (e) {
        msg.textContent = `Failed: ${e.message}`;
    }
});

async function sendNote(commit) {
    const out = document.getElementById('note-result');
    const text = document.getElementById('note-text').value.trim();
    if (!text) return;
    out.textContent = 'Reading the note...';
    try {
        const r = await api('/api/assistant', { method: 'POST', body: JSON.stringify({ text, commit }) });
        const e = r.event;
        out.textContent = `${e.event_type}, severity ${e.severity}, ${e.sector}: ${e.summary}  ` +
            `(${r.backend}${r.stored ? ', saved' : ', not saved yet'})`;
        if (r.stored) {
            document.getElementById('note-text').value = '';
            refreshEvents();
        }
    } catch (e) {
        out.textContent = `Failed: ${e.message}`;
    }
}
document.getElementById('note-preview').addEventListener('click', () => sendNote(false));
document.getElementById('note-form').addEventListener('submit', (ev) => { ev.preventDefault(); sendNote(true); });

document.getElementById('token-form').addEventListener('submit', (ev) => {
    ev.preventDefault();
    const field = document.getElementById('token-input');
    try {
        if (field.value) localStorage.setItem(TOKEN_KEY, field.value); else localStorage.removeItem(TOKEN_KEY);
    } catch { /* storage blocked: the token is kept for this page only */ }
    field.value = '';
    document.getElementById('token-state').textContent = token() ? 'token set' : 'read only';
});
document.getElementById('token-state').textContent = token() ? 'token set' : 'read only';

refreshAll();
setInterval(refreshAll, REFRESH_MS);
