#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
from bs4 import BeautifulSoup

# ---------------- Config ----------------
MINER_IP = os.environ.get("MINER_IP", "185.135.229.121")
MINER_USERNAME = os.environ.get("MINER_USERNAME", "admin")
MINER_PASSWORD = os.environ.get("MINER_PASSWORD", "alihacker")

# miner -> port map
port_map = {
    "131": 201, "132": 202, "133": 203,
    "65": 301, "66": 302, "70": 303
}

MINER_GROUPS = {
    "A": ["131", "132", "133"],
    "B": ["65", "66", "70"]
}

MINER_COLORS = {
    "131": "#3B82F6", "132": "#10B981", "133": "#8B5CF6",
    "65": "#F59E0B", "66": "#EF4444", "70": "#EC4899"
}

MINER_ICONS = {
    "131": "💎", "132": "💎", "133": "💎",
    "65": "💎", "66": "💎", "70": "💎"

}

# ---------------- Miner control (server-side) ----------------
def login_to_miner(miner_name, username=MINER_USERNAME, password=MINER_PASSWORD):
    """
    Open a session to miner and attempt login. Return requests.Session or None.
    """
    miner_port = port_map.get(miner_name)
    if not miner_port:
        return None
    base_url = f"https://{MINER_IP}:{miner_port}"
    login_url = f"{base_url}/cgi-bin/luci"
    session = requests.Session()
    session.verify = False
    requests.packages.urllib3.disable_warnings()
    try:
        # try initial GET (some firmwares need it)
        session.get(login_url, timeout=6)
        payload = {"luci_username": username, "luci_password": password}
        lr = session.post(login_url, data=payload, timeout=8, allow_redirects=False)
        if lr.status_code in (302, 303):
            return session
        # Some firmwares might return 200 but still login — but to be conservative return None
        return None
    except Exception:
        return None

def reboot_miner(miner_name, username=MINER_USERNAME, password=MINER_PASSWORD):
    """
    Perform reboot on miner using session login -> token extraction -> POST reboot.
    Returns dict: {"status":"success","message": "..."} or {"status":"error","message":"..."}
    """
    session = login_to_miner(miner_name, username, password)
    if not session:
        return {"status": "error", "message": "Login failed"}

    miner_port = port_map.get(miner_name)
    if not miner_port:
        return {"status": "error", "message": "Unknown miner port"}

    try:
        reboot_page = f"https://{MINER_IP}:{miner_port}/cgi-bin/luci/admin/system/reboot"
        r = session.get(reboot_page, timeout=8)
        if r.status_code != 200:
            return {"status": "error", "message": f"Failed to load reboot page (status {r.status_code})"}

        soup = BeautifulSoup(r.text, "html.parser")
        token_script = None
        for s in soup.find_all("script"):
            if s.string and "token" in s.string:
                token_script = s.string
                break
        if not token_script:
            return {"status": "error", "message": "Cannot find reboot token in page"}

        start = token_script.find("token: '")
        if start == -1:
            return {"status": "error", "message": "Token pattern not found in script"}
        start += len("token: '")
        end = token_script.find("'", start)
        token = token_script[start:end]
        if not token:
            return {"status": "error", "message": "Token extraction failed"}

        reboot_api = f"https://{MINER_IP}:{miner_port}/cgi-bin/luci/admin/system/reboot/call"
        # try form-encoded first (most luci-like endpoints expect form)
        try:
            resp = session.post(reboot_api, data={"token": token}, timeout=10)
            if resp.status_code == 200:
                return {"status": "success", "message": f"Miner {miner_name} reboot initiated"}
            # fallback: try sending JSON body (some devices may accept)
            resp2 = session.post(reboot_api, json={"token": token}, timeout=10)
            if resp2.status_code == 200:
                return {"status": "success", "message": f"Miner {miner_name} reboot initiated (json)"}
            return {"status": "error", "message": f"Reboot failed: status {resp.status_code}/{resp2.status_code}"}
        except requests.exceptions.ConnectTimeout:
            return {"status": "error", "message": "Connection timed out"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    except requests.exceptions.ConnectTimeout:
        return {"status": "error", "message": "Connection timed out while loading reboot page"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ---------------- HTML/JS/CSS generation (safe strings, no f-strings wrapping full block) ----------------
def generate_miner_groups_html():
    parts = []
    for group_key, miners in MINER_GROUPS.items():
        # group title A/B mapped to readable name
        title = "Group A (131-133)" if group_key == "A" else "Group B (65-70)"
        parts.append('<div class="miner-group" data-group="{}">'.format(group_key))
        parts.append('  <div class="group-title">{}</div>'.format(title))
        parts.append('  <div class="miners-grid">')
        for m in miners:
            color = MINER_COLORS.get(m, "#666")
            icon = MINER_ICONS.get(m, "")
            port = port_map.get(m, "")
            parts.append(
                '<label class="miner-card" id="card_{m}" data-miner="{m}" style="--miner-color:{c}">'.format(m=m, c=color) +
                '<div class="miner-info">' +
                '<div class="miner-icon">{icon}</div>'.format(icon=icon) +
                '<div class="miner-details"><div class="miner-name">MINER {m}</div><div class="miner-port">Port: {p}</div></div>'.format(m=m, p=port) +
                '<input type="checkbox" class="miner-checkbox" id="reboot_miner_{m}" name="reboot_miners" value="{m}" onclick="onCheckboxClick(event, \'{m}\')">'.format(m=m) +
                '</div></label>'
            )
        parts.append('  </div>')
        parts.append('</div>')
    return "\n".join(parts)

def get_reboot_manager_html():
    """
    Returns the full HTML string for inserting into the main site.
    No f-strings around the whole block so JS/CSS braces are safe.
    """
    html_top = """
<div id="poolsRebootContainer">
  <div id="rebootModal" class="modal" aria-hidden="true">
    <div class="modal-header">
      <h3 class="modal-title">🔄 SYSTEM REBOOT</h3>
      <button class="modal-close" onclick="closeRebootModal()">×</button>
    </div>

    <div class="warning-section">
      <strong>⚠️ IMPORTANT</strong>
      <p style="margin:6px 0 0 0">Rebooting will temporarily stop mining operations. Proceed only if necessary.</p>
    </div>

    <div class="miner-selection-section">
      <div class="section-header">
        <div><strong>🎯 SELECT MINERS TO REBOOT</strong></div>
        <div class="group-controls">
          <button type="button" onclick="selectRebootGroup('all')">SELECT ALL</button>
          <button type="button" onclick="selectRebootGroup('A')">GROUP A</button>
          <button type="button" onclick="selectRebootGroup('B')">GROUP B</button>
          <button type="button" onclick="deselectRebootAll()">CLEAR ALL</button>
        </div>
      </div>

      <div class="miner-groups-container">
"""
    html_mid = generate_miner_groups_html()
    html_bottom = """
      </div>
    </div>

    <div class="confirmation-section">
      <div><span id="selectedCount">0</span> miners selected</div>
      <div class="confirmation-actions">
        <button id="confirmRebootBtn" class="btn-confirm" onclick="confirmReboot()" disabled>CONFIRM REBOOT</button>
        <button id="startRebootBtn" class="btn-start" onclick="startRebootProcess()" style="display:none">START REBOOT PROCESS</button>
      </div>
    </div>

    <div class="progress-section">
      <div class="progress-header">
        <span>REBOOT PROGRESS</span>
        <span id="rebootProgressText">0%</span>
      </div>
      <div class="progress-bar">
        <div id="rebootProgress" class="progress-fill" style="width:0%"></div>
      </div>
      <div id="rebootStatus" class="progress-status">Ready to reboot selected miners</div>
    </div>

    <div id="rebootSummary" class="reboot-summary" style="display:none; margin-top:12px;"></div>
  </div>

  <div id="rebootModalOverlay" class="modal-overlay" onclick="onOverlayClick(event)"></div>
</div>

<script>
(function(){
  // state
  let selected = [];
  let results = []; // { miner, ok(bool), msg }

  function checkboxList() { return Array.from(document.querySelectorAll('#poolsRebootContainer .miner-checkbox')); }

  function updateCardVisual(cb) {
    const val = cb.value;
    const card = document.querySelector('#poolsRebootContainer .miner-card[data-miner="' + val + '"]');
    // fallback to id
    const cardById = document.getElementById('card_' + val);
    const chosen = card || cardById;
    if (chosen) {
      if (cb.checked) chosen.classList.add('selected'); else chosen.classList.remove('selected');
    }
  }

  window.onCheckboxClick = function(e, minerId) {
    e.stopPropagation();
    const cb = document.getElementById('reboot_miner_' + minerId);
    if (!cb) return;
    updateCardVisual(cb);
    updateSelection();
  };

  // label click toggling handled by DOM 'click' listener (see init)
  function updateSelection() {
    selected = checkboxList().filter(c => c.checked).map(c => c.value);
    const cnt = document.getElementById('selectedCount');
    if (cnt) cnt.textContent = selected.length;
    const confirmBtn = document.getElementById('confirmRebootBtn');
    if (confirmBtn) confirmBtn.disabled = (selected.length === 0);
    const startBtn = document.getElementById('startRebootBtn');
    if (startBtn) startBtn.style.display = 'none';
  }

  window.toggleCard = function(minerId) {
    const cb = document.getElementById('reboot_miner_' + minerId);
    if (!cb) return;
    cb.checked = !cb.checked;
    updateCardVisual(cb);
    updateSelection();
  };

  window.selectRebootGroup = function(group) {
    const map = {'all':['131','132','133','65','66','70'], 'A': ['131','132','133'], 'B': ['65','66','70']};
    const list = map[group] || [];
    if (group === 'all') {
      checkboxList().forEach(cb => { cb.checked = true; updateCardVisual(cb); });
    } else {
      list.forEach(id => { const cb = document.getElementById('reboot_miner_' + id); if (cb) { cb.checked = true; updateCardVisual(cb); } });
    }
    updateSelection();
  };

  window.deselectRebootAll = function() {
    checkboxList().forEach(cb => { cb.checked = false; updateCardVisual(cb); });
    updateSelection();
  };

  window.confirmReboot = function() {
    updateSelection();
    if (selected.length === 0) { alert('Select at least one miner'); return; }
    if (!confirm('Are you sure to reboot ' + selected.length + ' miners?')) return;
    document.getElementById('confirmRebootBtn').style.display = 'none';
    document.getElementById('startRebootBtn').style.display = 'inline-block';
    document.getElementById('rebootStatus').textContent = 'Ready to start reboot';
    results = [];
    const sumEl = document.getElementById('rebootSummary');
    if (sumEl) { sumEl.style.display = 'none'; sumEl.innerHTML = ''; }
  };

  // fetch with timeout
  function fetchWithTimeout(url, opts, timeout = 12000) {
    const controller = new AbortController();
    const signal = controller.signal;
    const timer = setTimeout(() => controller.abort(), timeout);
    return fetch(url, Object.assign({}, opts, { signal })).finally(() => clearTimeout(timer));
  }

  window.startRebootProcess = function() {
    updateSelection();
    if (selected.length === 0) { alert('No miners selected'); return; }
    const total = selected.length;
    let idx = 0;
    document.getElementById('rebootProgress').style.width = '0%';
    document.getElementById('rebootProgressText').textContent = '0%';
    document.getElementById('rebootStatus').textContent = 'Starting reboot sequence...';

    // prepare status rows
    const progressSection = document.getElementById('rebootSummary');
    progressSection.style.display = 'block';
    progressSection.innerHTML = '';
    selected.forEach(m => {
      const r = document.createElement('div');
      r.id = 'status_row_' + m;
      r.style.padding = '8px 0';
      r.textContent = 'Miner ' + m + ': Pending';
      progressSection.appendChild(r);
    });

    function next() {
      if (idx >= total) {
        document.getElementById('rebootProgress').style.width = '100%';
        document.getElementById('rebootProgressText').textContent = '100%';
        document.getElementById('rebootStatus').textContent = '✅ Finished. See summary below.';
        // show condensed summary (succeeded/failed)
        showSummary();
        setTimeout(() => {
          document.getElementById('startRebootBtn').style.display = 'none';
          const confirmBtn = document.getElementById('confirmRebootBtn');
          if (confirmBtn) confirmBtn.style.display = 'inline-block';
        }, 800);
        return;
      }

      const miner = selected[idx];
      const row = document.getElementById('status_row_' + miner);
      if (row) row.textContent = 'Miner ' + miner + ': Rebooting...';
      // call server endpoint
      fetchWithTimeout('/reboot_miner', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ miner: miner })
      }, 12000).then(res => {
        if (!res || !res.ok) throw new Error('Network/HTTP ' + (res ? res.status : 'unknown'));
        return res.json();
      }).then(data => {
        if (data && data.status === 'success') {
          if (row) row.textContent = 'Miner ' + miner + ': ✅ ' + (data.message || 'OK');
          results.push({ miner: miner, ok: true, msg: data.message || 'OK' });
        } else {
          const msg = (data && (data.message || data.error)) || 'Unknown error';
          if (row) row.textContent = 'Miner ' + miner + ': ❌ ' + msg;
          results.push({ miner: miner, ok: false, msg: msg });
        }
      }).catch(err => {
        const msg = (err && err.name === 'AbortError') ? 'Timeout' : (err && err.message ? err.message : 'Network error');
        if (row) row.textContent = 'Miner ' + miner + ': ❌ ' + msg;
        results.push({ miner: miner, ok: false, msg: msg });
      }).finally(() => {
        idx++;
        const pct = Math.round((idx / total) * 100);
        document.getElementById('rebootProgress').style.width = pct + '%';
        document.getElementById('rebootProgressText').textContent = pct + '%';
        // small safe delay between miners
        setTimeout(next, 1000);
      });
    }

    next();
  };

  function transientNotify(type, text) {
    const box = document.createElement('div');
    box.className = 'reboot-notify ' + type;
    box.textContent = text;
    box.style.position = 'fixed';
    box.style.right = '18px';
    box.style.top = (18 + (document.querySelectorAll('.reboot-notify').length * 56)) + 'px';
    box.style.padding = '10px 14px';
    box.style.borderRadius = '8px';
    box.style.zIndex = 12000;
    box.style.color = '#fff';
    box.style.opacity = '1';
    box.style.transition = 'opacity 0.3s';
    box.style.maxWidth = '320px';
    box.style.background = (type === 'success') ? '#10b981' : '#ef4444';
    document.body.appendChild(box);
    setTimeout(() => { box.style.opacity = '0'; setTimeout(() => box.remove(), 300); }, 3500);
  }

  function showSummary() {
    const el = document.getElementById('rebootSummary');
    if (!el) return;
    // build summary
    const ok = results.filter(r => r.ok).map(r => r.miner);
    const bad = results.filter(r => !r.ok);
    let html = '<div style="padding:10px;background:rgba(255,255,255,0.02);border-radius:8px;">';
    html += '<div style="font-weight:800;margin-bottom:8px">Summary</div>';
    if (ok.length) html += '<div style="color:#10b981;font-weight:700;margin-bottom:6px">Succeeded: ' + ok.join(', ') + '</div>';
    if (bad.length) {
      html += '<div style="color:#ef4444;font-weight:700">Failed:</div><ul style="margin:6px 0 0 14px;color:#f8fafc">';
      bad.forEach(b => { html += '<li>Miner ' + b.miner + ': ' + b.msg + '</li>'; });
      html += '</ul>';
    }
    html += '</div>';
    el.innerHTML = html;
  }

  // overlay click close
  window.onOverlayClick = function(e) {
    if (e.target && e.target.id === 'rebootModalOverlay') closeRebootModal();
  };

  window.showRebootModal = function() {
    document.getElementById('rebootModalOverlay').style.display = 'block';
    document.getElementById('rebootModal').style.display = 'block';
    // attach click handlers for cards (label elements)
    document.querySelectorAll('#poolsRebootContainer .miner-card').forEach(card => {
      card.addEventListener('click', function(e) {
        // toggling handled by the input; wait a tick then update UI
        setTimeout(() => {
          const cb = this.querySelector('input[type="checkbox"]');
          if (cb) { updateCardVisual(cb); updateSelection(); }
        }, 10);
      });
    });
    updateSelection();
  };

  window.closeRebootModal = function() {
    document.getElementById('rebootModalOverlay').style.display = 'none';
    document.getElementById('rebootModal').style.display = 'none';
  };

  // init on DOM ready (in case HTML inserted before)
  document.addEventListener('DOMContentLoaded', function() {
    // ensure checkboxes reflect selection visuals
    document.querySelectorAll('#poolsRebootContainer .miner-checkbox').forEach(cb => {
      updateCardVisual(cb);
    });
    updateSelection();
  });

})();
</script>

<style>
/* scoped styles to avoid touching main site */
#poolsRebootContainer { font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, Arial; }
#poolsRebootContainer .modal { position: fixed; top:50%; left:50%; transform: translate(-50%,-50%); width:92%; max-width:760px; max-height:88vh; overflow:auto;
  background: linear-gradient(180deg,#071025,#0f1724); color:#e6eef8; border-radius:12px; padding:16px; z-index:11000; box-shadow:0 12px 40px rgba(2,6,23,0.7); }
#poolsRebootContainer .modal-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
#poolsRebootContainer .modal-title { font-weight:800; font-size:18px; }
#poolsRebootContainer .modal-close { background:#ef4444; color:white; border:none; padding:6px 10px; border-radius:8px; cursor:pointer; }
#poolsRebootContainer .warning-section { background:#fff8e6; color:#6b4a00; padding:10px; border-radius:8px; margin-bottom:10px; }
#poolsRebootContainer .section-header { display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:8px; }
#poolsRebootContainer .group-controls button { margin:4px; padding:6px 10px; border-radius:8px; border:1px solid rgba(255,255,255,0.04); background:#0b1220; color:#e6eef8; cursor:pointer; }
#poolsRebootContainer .miner-groups-container { display:flex; flex-direction:column; gap:10px; }
#poolsRebootContainer .miners-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(140px,1fr)); gap:10px; }
#poolsRebootContainer .miner-card { display:flex; align-items:center; justify-content:space-between; padding:10px; border-radius:8px; background:#071026; border:2px solid transparent; cursor:pointer; }
#poolsRebootContainer .miner-card.selected { border-color: var(--miner-color); background: linear-gradient(90deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00)); }
#poolsRebootContainer .miner-info { display:flex; align-items:center; gap:10px; }
#poolsRebootContainer .miner-icon { font-size:18px; width:36px; text-align:center; }
#poolsRebootContainer .miner-details { display:flex; flex-direction:column; min-width:0; }
#poolsRebootContainer .miner-name { font-weight:700; font-size:14px; color:#e6eef8; }
#poolsRebootContainer .miner-port { font-size:12px; color:#9ca3af; }
#poolsRebootContainer .miner-checkbox { width:18px; height:18px; margin-left:8px; }
#poolsRebootContainer .confirmation-section { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-top:8px; }
#poolsRebootContainer .btn-confirm, #poolsRebootContainer .btn-start { padding:8px 12px; border-radius:8px; border:none; font-weight:700; cursor:pointer; }
#poolsRebootContainer .btn-confirm { background:#2563eb; color:white; }
#poolsRebootContainer .btn-start { background:#10b981; color:white; }

#poolsRebootContainer .progress-bar { width:100%; height:14px; background:#071426; border-radius:8px; overflow:hidden; margin-top:8px; }
#poolsRebootContainer .progress-fill { height:100%; width:0%; background: linear-gradient(90deg,#ef4444,#f59e0b); transition:width .3s ease; }
#poolsRebootContainer .progress-header { display:flex; justify-content:space-between; align-items:center; margin-top:6px; color:#e6eef8; font-weight:700; }
#rebootModalOverlay { position:fixed; inset:0; background: rgba(0,0,0,0.45); z-index:10990; display:none; }

.reboot-notify { position:fixed; right:18px; top:18px; padding:8px 12px; border-radius:8px; color:#fff; z-index:12000; }
.reboot-notify.success { background:#10b981; } .reboot-notify.error { background:#ef4444; }

@media (max-width: 640px){
  #poolsRebootContainer .modal { width:96%; padding:12px; }
  #poolsRebootContainer .miners-grid { grid-template-columns: 1fr; }
  #poolsRebootContainer .miner-name { font-size:13px; }
  #poolsRebootContainer .miner-port { font-size:11px; }
}
</style>
"""
    return html_top + html_mid + html_bottom

# exported symbols for main.py to import
__all__ = ["reboot_miner", "get_reboot_manager_html"]