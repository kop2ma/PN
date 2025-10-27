#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NTP.py - NTP Management compatible with main.py
"""

import os
import json
import requests
from bs4 import BeautifulSoup

# ===========================
# Configuration - Compatible with main.py
# ===========================
DEFAULT_NTP_SERVERS = ["ir.pool.ntp.org"]

def _get_miner_base(miner_name):
    """Get miner base URL - Compatible with main.py"""
    try:
        from main import port_map, MINER_IP
        miner_port = port_map.get(miner_name)
        
        if not miner_port:
            return None, None, f"Port not found for miner {miner_name}"
        
        if not MINER_IP:
            return None, None, "MINER_IP not set"
        
        base = f"https://{MINER_IP}:{miner_port}"
        return base, miner_port, None
        
    except Exception as e:
        return None, None, f"Error: {str(e)}"

def _session_noverify():
    """Create session without verify - Compatible with main.py"""
    s = requests.Session()
    s.verify = False
    requests.packages.urllib3.disable_warnings()
    return s

def login_to_miner(miner_name, username, password):
    """Login to miner - Compatible with main.py"""
    base, port, err = _get_miner_base(miner_name)
    if err:
        return None, err
    
    login_url = f"{base}/cgi-bin/luci"
    session = _session_noverify()
    
    try:
        # Initial GET to get cookies
        session.get(login_url, timeout=10)
    except Exception as e:
        return None, f"GET login page failed: {e}"
    
    # Different payloads for compatibility
    payloads = [
        {"luci_username": username, "luci_password": password},
        {"username": username, "password": password},
    ]
    
    for payload in payloads:
        try:
            resp = session.post(login_url, data=payload, timeout=10, allow_redirects=False)
            if resp.status_code in (200, 302, 303):
                return session, None
        except Exception as e:
            continue
    
    return None, "Login failed with all payloads"

def super_ntp_update(miner_name, enable_ntp=True, custom_servers=None, timezone="Asia/Tehran", username="admin", password="admin"):
    """
    🚀 Super NTP Update - Compatible with main.py
    """
    try:
        # 1. Login to miner
        session, err = login_to_miner(miner_name, username, password)
        if not session:
            return {"success": False, "message": f"❌ Login error: {err}"}
        
        # 2. Get base URL
        base, port, err2 = _get_miner_base(miner_name)
        if err2:
            return {"success": False, "message": f"❌ {err2}"}
        
        system_url = f"{base}/cgi-bin/luci/admin/system/system"
        
        # 3. Get system page
        try:
            response = session.get(system_url, timeout=10)
            if response.status_code != 200:
                return {"success": False, "message": f"❌ Page load error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"❌ Page load error: {e}"}
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 4. Get security token
        token_input = soup.find("input", {"name": "token"})
        token = token_input["value"] if token_input and token_input.has_attr("value") else ""
        
        if not token:
            return {"success": False, "message": "❌ Security token not found"}
        
        # 5. Prepare data
        servers = custom_servers or DEFAULT_NTP_SERVERS
        form_data = {
            "token": token,
            "cbi.submit": "1",
            "cbi.apply": "Save & Apply",
        }
        
        # Set timezone
        tz_keys = [
            "cbid.system.cfg02e48a.zonename",
            "cbid.system.system.zonename", 
            "cbid.system.timezone"
        ]
        for key in tz_keys:
            form_data[key] = timezone
        
        # Enable/disable NTP
        ntp_value = "1" if enable_ntp else "0"
        form_data.update({
            "cbid.system.ntp.enabled": ntp_value,
            "cbi.cbe.system.ntp.enabled": ntp_value,
        })
        
        # Add NTP servers (only one server)
        if servers:
            form_data["cbid.system.ntp.server"] = servers[0]
            form_data["cbid.system.ntp.server.1"] = servers[0]
        
        # 6. Send request
        try:
            post_response = session.post(system_url, data=form_data, timeout=15)
            
            if post_response.status_code in (200, 302):
                return {
                    "success": True, 
                    "message": f"✅ NTP updated for miner {miner_name}",
                    "ntp_enabled": enable_ntp,
                    "servers": servers,
                    "timezone": timezone,
                    "miner": miner_name
                }
            else:
                return {"success": False, "message": f"❌ Server error: {post_response.status_code}"}
                
        except Exception as e:
            return {"success": False, "message": f"❌ Send error: {e}"}
        
    except Exception as e:
        return {"success": False, "message": f"❌ Unknown error: {str(e)}"}

def bulk_super_ntp_update(miner_names, enable_ntp=True, custom_servers=None, timezone="Asia/Tehran", username="admin", password="admin"):
    """
    Bulk update miners - Compatible with main.py
    """
    results = []
    for miner in miner_names:
        result = super_ntp_update(miner, enable_ntp, custom_servers, timezone, username, password)
        results.append({
            "miner": miner,
            "success": result.get("success", False),
            "message": result.get("message", "")
        })
    
    return results

# ===========================
# Existing functions for compatibility
# ===========================
def update_ntp_settings(miner_name, timezone, ntp_servers, ntp_enabled, username, password):
    """
    Main function for main.py - Compatible with existing route
    """
    return super_ntp_update(
        miner_name=miner_name,
        enable_ntp=ntp_enabled,
        custom_servers=ntp_servers,
        timezone=timezone,
        username=username,
        password=password
    )

def get_ntp_html():
    """
    NTP Modal HTML - Better feedback and English
    """
    return '''
<!-- NTP Modal -->
<div id="ntpModalOverlay" style="display:none; position:fixed; left:0; top:0; right:0; bottom:0; background:rgba(0,0,0,0.6); z-index:10000;" onclick="closeNtpModal()"></div>
<div id="ntpModal" class="modal" style="display:none; position:fixed; z-index:10001; left:50%; top:50%; transform:translate(-50%,-50%); width: min(500px, 96%); background:linear-gradient(135deg, #1e3a8a 0%, #3730a3 100%); padding:25px; border-radius:20px; border:2px solid #4f46e5; box-shadow:0 20px 60px rgba(0,0,0,0.5); color:white;">
    
    <!-- Header -->
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:25px; border-bottom:2px solid rgba(255,255,255,0.2); padding-bottom:15px;">
        <h3 style="margin:0; color:white; font-size:24px; font-weight:800;">🚀 SUPER NTP UPDATE</h3>
        <button onclick="closeNtpModal()" style="background:#ef4444; color:white; border:none; width:35px; height:35px; border-radius:50%; cursor:pointer; font-size:18px; font-weight:bold;">×</button>
    </div>

    <!-- Settings -->
    <div style="margin-bottom:25px;">
        <!-- Enable NTP -->
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:20px; padding:15px; background:rgba(255,255,255,0.1); border-radius:12px;">
            <input type="checkbox" id="enableNTP" checked style="width:20px; height:20px;">
            <label style="font-weight:700; color:white; cursor:pointer;">Enable NTP Sync</label>
        </div>

        <!-- NTP Server (Single server) -->
        <div style="margin-bottom:20px;">
            <label style="display:block; margin-bottom:8px; font-weight:700; color:white;">🌐 NTP Server:</label>
            <input type="text" id="ntpServer" value="ir.pool.ntp.org" 
                   style="width:100%; padding:15px; border-radius:10px; border:1px solid rgba(255,255,255,0.3); background:rgba(255,255,255,0.1); color:white; font-family:monospace; font-size:16px;">
            <div style="display:flex; gap:10px; margin-top:12px;">
                <button onclick="setIranianServer()" style="flex:1; padding:12px; background:#3b82f6; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:700;">🇮🇷 Iranian Server</button>
                <button onclick="clearServer()" style="flex:1; padding:12px; background:#6b7280; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:700;">🗑️ Clear</button>
            </div>
        </div>

        <!-- Timezone -->
        <div style="margin-bottom:20px;">
            <label style="display:block; margin-bottom:8px; font-weight:700; color:white;">🌍 Timezone:</label>
            <select id="timezoneSelect" style="width:100%; padding:15px; border-radius:10px; border:1px solid rgba(255,255,255,0.3); background:rgba(255,255,255,0.1); color:white; font-size:16px;">
                <option value="Asia/Tehran">Asia/Tehran - Iran</option>
                <option value="UTC">UTC - Universal Time</option>
                <option value="Europe/Istanbul">Europe/Istanbul - Turkey</option>
                <option value="Asia/Dubai">Asia/Dubai - Dubai</option>
            </select>
        </div>
    </div>

    <!-- Progress -->
    <div style="margin-bottom:25px; background:rgba(255,255,255,0.1); padding:20px; border-radius:12px;">
        <div style="display:flex; justify-content:space-between; margin-bottom:12px; font-weight:700;">
            <span style="color:white;">Progress:</span>
            <span id="ntpProgressText" style="color:#60a5fa;">0%</span>
        </div>
        <div style="background:rgba(255,255,255,0.2); height:12px; border-radius:10px; overflow:hidden;">
            <div id="ntpProgressBar" style="height:100%; width:0%; background:linear-gradient(90deg,#10b981,#3b82f6); transition:width 0.3s;"></div>
        </div>
        <div id="currentStatus" style="margin-top:10px; font-size:14px; color:#93c5fd; text-align:center; min-height:20px; font-weight:600;">Ready to start...</div>
    </div>

    <!-- Buttons -->
    <div style="display:flex; gap:12px;">
        <button onclick="closeNtpModal()" style="flex:1; padding:16px; background:#6b7280; color:white; border:none; border-radius:10px; cursor:pointer; font-weight:700; font-size:16px;">❌ Cancel</button>
        <button onclick="runSuperUpdate()" style="flex:1; padding:16px; background:linear-gradient(135deg,#10b981,#3b82f6); color:white; border:none; border-radius:10px; cursor:pointer; font-weight:800; font-size:16px;">🚀 RUN SUPER UPDATE</button>
    </div>
</div>

<script>
// Same working functions - updated for single server and better feedback
let isUpdating = false;

function showNtpModal() {
    console.log('🚀 Opening NTP Modal...');
    document.getElementById('ntpModalOverlay').style.display = 'block';
    document.getElementById('ntpModal').style.display = 'block';
}

function closeNtpModal() {
    if (isUpdating) {
        if (!confirm('Update is in progress! Are you sure you want to cancel?')) {
            return;
        }
    }
    document.getElementById('ntpModalOverlay').style.display = 'none';
    document.getElementById('ntpModal').style.display = 'none';
    isUpdating = false;
}

function setIranianServer() {
    document.getElementById('ntpServer').value = 'ir.pool.ntp.org';
}

function clearServer() {
    document.getElementById('ntpServer').value = '';
}

function runSuperUpdate() {
    if (isUpdating) {
        alert('⚠️ Update is already running!');
        return;
    }

    const enableNTP = document.getElementById('enableNTP').checked;
    const ntpServer = document.getElementById('ntpServer').value.trim();
    const timezone = document.getElementById('timezoneSelect').value;
    
    if (enableNTP && !ntpServer) {
        alert('⚠️ Please enter NTP server address');
        return;
    }

    // Use miners defined in main.py
    const miners = ['131', '132', '133', '65', '66', '70'];
    const progressBar = document.getElementById('ntpProgressBar');
    const progressText = document.getElementById('ntpProgressText');
    const statusText = document.getElementById('currentStatus');
    
    let completed = 0;
    const total = miners.length;
    
    // Reset progress
    progressBar.style.width = '0%';
    progressText.textContent = '0%';
    statusText.textContent = '🔄 Starting update...';
    statusText.style.color = '#fbbf24';
    
    isUpdating = true;
    
    console.log(`🚀 Starting super update for ${total} miners...`);
    
    // Show immediate feedback
    setTimeout(() => {
        statusText.textContent = '⏳ Connecting to miners...';
    }, 100);
    
    miners.forEach((miner, index) => {
        setTimeout(() => {
            statusText.textContent = `🔄 Updating miner ${miner}...`;
            statusText.style.color = '#fbbf24';
            
            fetch('/update_ntp', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    miner: miner,
                    ntp_enabled: enableNTP,
                    ntp_servers: ntpServer ? [ntpServer] : [], // Single server
                    timezone: timezone
                })
            })
            .then(r => r.json())
            .then(data => {
                completed++;
                const progress = Math.round((completed / total) * 100);
                progressBar.style.width = progress + '%';
                progressText.textContent = progress + '%';
                
                console.log(`✅ Miner ${miner}:`, data);
                
                if (data.success) {
                    statusText.textContent = `✅ ${miner}: ${data.message}`;
                    statusText.style.color = '#86efac';
                } else {
                    statusText.textContent = `❌ ${miner}: ${data.message}`;
                    statusText.style.color = '#fca5a5';
                }
                
                if (completed === total) {
                    isUpdating = false;
                    setTimeout(() => {
                        statusText.textContent = '🎉 All miners updated successfully!';
                        statusText.style.color = '#86efac';
                        setTimeout(() => {
                            alert('✅ Super NTP Update completed successfully!');
                            closeNtpModal();
                        }, 1000);
                    }, 500);
                }
            })
            .catch(err => {
                completed++;
                const progress = Math.round((completed / total) * 100);
                progressBar.style.width = progress + '%';
                progressText.textContent = progress + '%';
                
                console.error(`❌ Miner ${miner}:`, err);
                statusText.textContent = `❌ Error on ${miner}`;
                statusText.style.color = '#fca5a5';
                
                if (completed === total) {
                    isUpdating = false;
                    setTimeout(() => {
                        alert('⚠️ Some miners may not be updated');
                        closeNtpModal();
                    }, 500);
                }
            });
        }, index * 800); // 800ms delay between requests
    });
}
</script>
'''
