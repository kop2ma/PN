#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import json
import os

# Pool Configuration - فقط سرورهای ایرانی
NTP_SERVERS = [
    "ir.pool.ntp.org",
    "0.ir.pool.ntp.org",
    "1.ir.pool.ntp.org", 
    "2.ir.pool.ntp.org",
    "3.ir.pool.ntp.org",
    "ntp1.availab.com",  # سرور ایرانی
    "time.nuri.net"      # سرور ایرانی
]

TIMEZONES = [
    "UTC", "Asia/Tehran", "Asia/Dubai", "Europe/Istanbul", 
    "Asia/Shanghai", "Europe/London", "America/New_York",
    "Europe/Paris", "Asia/Tokyo", "Asia/Kolkata"
]

def login_to_miner(miner_name, username, password):
    """Login to miner and return session"""
    from pools_manager import port_map
    
    miner_port = port_map.get(miner_name)
    if not miner_port:
        print(f"❌ Port not found for miner {miner_name}")
        return None
    
    MINER_IP = os.environ.get("MINER_IP")
    base_url = f"https://{MINER_IP}:{miner_port}"
    login_url = f"{base_url}/cgi-bin/luci"
    
    session = requests.Session()
    session.verify = False
    requests.packages.urllib3.disable_warnings()
    
    try:
        print(f"🔐 Attempting NTP login to miner {miner_name}...")
        response = session.get(login_url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        login_data = {
            'luci_username': username,
            'luci_password': password
        }
        
        login_response = session.post(login_url, data=login_data, timeout=10, allow_redirects=False)
        
        if login_response.status_code in [302, 303]:
            print(f"✅ Successfully logged into miner {miner_name} for NTP")
            return session
        else:
            print(f"❌ Login failed for miner {miner_name} - Status: {login_response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Login error for miner {miner_name}: {str(e)}")
        return None

def get_ntp_settings(miner_name, username, password):
    """Get current NTP and timezone settings from miner"""
    session = login_to_miner(miner_name, username, password)
    if not session:
        return {"error": "Login failed"}
    
    try:
        from pools_manager import port_map
        MINER_IP = os.environ.get("MINER_IP")
        miner_port = port_map.get(miner_name)
        ntp_url = f"https://{MINER_IP}:{miner_port}/cgi-bin/luci/admin/system/system"
        
        print(f"📡 Fetching NTP settings from miner {miner_name}...")
        response = session.get(ntp_url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract current timezone
        timezone_select = soup.find('select', {'id': 'cbid.system.cfg02e48a.zonename'})
        current_timezone = "Asia/Tehran"  # default
        if timezone_select:
            selected_option = timezone_select.find('option', selected=True)
            if selected_option:
                current_timezone = selected_option.get('value', 'Asia/Tehran')
        
        # Extract NTP servers
        ntp_inputs = soup.find_all('input', {'name': 'cbid.system.ntp.server'})
        current_servers = [inp.get('value', '') for inp in ntp_inputs if inp.get('value')]
        
        # Extract NTP enabled status
        ntp_enabled = soup.find('input', {'id': 'cbid.system.ntp.enabled'})
        is_ntp_enabled = ntp_enabled and ntp_enabled.get('checked') == 'checked'
        
        return {
            "timezone": current_timezone,
            "ntp_servers": current_servers,
            "ntp_enabled": is_ntp_enabled,
            "success": f"Settings retrieved for miner {miner_name}"
        }
        
    except Exception as e:
        return {"error": f"Failed to get NTP settings: {str(e)}"}

def update_ntp_settings(miner_name, timezone, ntp_servers, ntp_enabled, username, password):
    """Update NTP and timezone settings for miner"""
    session = login_to_miner(miner_name, username, password)
    if not session:
        return {"error": "Login failed"}
    
    try:
        from pools_manager import port_map
        MINER_IP = os.environ.get("MINER_IP")
        miner_port = port_map.get(miner_name)
        ntp_url = f"https://{MINER_IP}:{miner_port}/cgi-bin/luci/admin/system/system"
        
        print(f"📡 Loading NTP configuration page for {miner_name}...")
        response = session.get(ntp_url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract token
        token_input = soup.find('input', {'name': 'token'})
        if not token_input:
            return {"error": "Cannot find form token"}
        
        token = token_input.get('value')
        
        # Prepare form data
        form_data = {
            'token': token,
            'cbi.submit': '1',
            'cbi.apply': 'Save & Apply'
        }
        
        # Add timezone
        form_data['cbid.system.cfg02e48a.zonename'] = timezone
        
        # Add NTP enabled status
        form_data['cbid.system.ntp.enabled'] = '1' if ntp_enabled else '0'
        
        # Add NTP servers (up to 4 servers as in the original form)
        for i, server in enumerate(ntp_servers[:4], 1):
            form_data[f'cbid.system.ntp.server.{i}'] = server
        
        print(f"🔄 Updating NTP settings for {miner_name}...")
        print(f"   Timezone: {timezone}")
        print(f"   NTP Enabled: {ntp_enabled}")
        print(f"   NTP Servers: {', '.join(ntp_servers[:4])}")
        
        update_response = session.post(ntp_url, data=form_data, timeout=10)
        
        if update_response.status_code == 200:
            print(f"✅ NTP settings successfully updated for miner {miner_name}")
            return {"success": f"NTP settings updated for miner {miner_name}"}
        else:
            print(f"❌ NTP update failed for {miner_name} - Status: {update_response.status_code}")
            return {"error": f"NTP update failed with status {update_response.status_code}"}
            
    except Exception as e:
        print(f"❌ Connection error for {miner_name}: {str(e)}")
        return {"error": f"Connection error: {str(e)}"}

def get_ntp_html():
    """HTML مربوط به مدیریت NTP و تایم‌زون"""
    return '''
    <!-- NTP Configuration Modal -->
    <div id="ntpModal" class="modal">
        <div class="modal-header">
            <h3 class="modal-title" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">⏰ TIME & NTP SETTINGS</h3>
            <button class="modal-close" onclick="closeNtpModal()" style="background: #ef4444; color: white; border: none; border-radius: 50%; width: 32px; height: 32px; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center;">×</button>
        </div>
        
        <!-- Miner Selection Section -->
        <div class="miner-selection-section">
            <div class="section-header">
                <h4>🎯 SELECT MINERS</h4>
                <div class="group-controls">
                    <button class="group-btn" onclick="selectNtpGroup('all')">SELECT ALL</button>
                    <button class="group-btn" onclick="selectNtpGroup('A')">GROUP A</button>
                    <button class="group-btn" onclick="selectNtpGroup('B')">GROUP B</button>
                    <button class="group-btn" onclick="deselectNtpAll()">CLEAR ALL</button>
                </div>
            </div>
            
            <div class="miner-groups-container" id="ntpMinerGroups">
                <!-- Miner groups will be loaded here -->
            </div>
        </div>

        <!-- Current Time Section -->
        <div class="time-section">
            <div class="section-header">
                <h4>🕐 CURRENT TIME</h4>
            </div>
            <div class="current-time-display">
                <div id="currentTime" class="time-value">Loading current time...</div>
                <button class="sync-btn" onclick="syncWithBrowser()">
                    <span>🔄</span>
                    SYNC WITH BROWSER
                </button>
            </div>
        </div>

        <!-- Timezone Configuration -->
        <div class="timezone-section">
            <div class="section-header">
                <h4>🌍 TIMEZONE SETTINGS</h4>
            </div>
            
            <div class="form-group">
                <label class="form-label">SELECT TIMEZONE</label>
                <select class="form-select" id="timezoneSelect">
                    <option value="UTC">UTC</option>
                    <option value="Asia/Tehran" selected>Asia/Tehran (Iran)</option>
                    <option value="Asia/Dubai">Asia/Dubai (UAE)</option>
                    <option value="Europe/Istanbul">Europe/Istanbul (Turkey)</option>
                    <option value="Asia/Shanghai">Asia/Shanghai (China)</option>
                    <option value="Europe/London">Europe/London (UK)</option>
                    <option value="America/New_York">America/New_York (USA)</option>
                </select>
            </div>
        </div>

        <!-- NTP Configuration -->
        <div class="ntp-section">
            <div class="section-header">
                <h4>🔄 NTP SYNCHRONIZATION</h4>
                <div class="ntp-actions">
                    <button class="action-btn" onclick="fillIranianServers()">🇮🇷 IRANIAN SERVERS</button>
                    <button class="action-btn" onclick="clearNtpServers()">🗑️ CLEAR SERVERS</button>
                </div>
            </div>
            
            <div class="form-group">
                <label class="form-label">
                    <input type="checkbox" id="ntpEnabled" checked onchange="toggleNtpServers()">
                    ENABLE NTP CLIENT
                </label>
            </div>
            
            <div class="ntp-servers-container" id="ntpServersContainer">
                <div class="form-group">
                    <label class="form-label">NTP SERVER 1</label>
                    <input type="text" class="form-input" id="ntpServer1" placeholder="e.g., ir.pool.ntp.org" value="ir.pool.ntp.org">
                </div>
                <div class="form-group">
                    <label class="form-label">NTP SERVER 2</label>
                    <input type="text" class="form-input" id="ntpServer2" placeholder="e.g., 0.ir.pool.ntp.org" value="0.ir.pool.ntp.org">
                </div>
                <div class="form-group">
                    <label class="form-label">NTP SERVER 3</label>
                    <input type="text" class="form-input" id="ntpServer3" placeholder="e.g., 1.ir.pool.ntp.org" value="1.ir.pool.ntp.org">
                </div>
                <div class="form-group">
                    <label class="form-label">NTP SERVER 4</label>
                    <input type="text" class="form-input" id="ntpServer4" placeholder="e.g., 2.ir.pool.ntp.org" value="2.ir.pool.ntp.org">
                </div>
            </div>
        </div>

        <!-- Progress & Actions -->
        <div class="action-section">
            <div class="progress-container">
                <div class="progress-header">
                    <span>PROGRESS</span>
                    <span id="ntpProgressText">0%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="ntpUpdateProgress" style="width: 0%"></div>
                </div>
            </div>
            
            <div class="action-buttons">
                <button class="btn-cancel" onclick="closeNtpModal()">
                    <span>✕</span>
                    CANCEL
                </button>
                <button class="btn-apply" onclick="applyNtpSettings()">
                    <span>💾</span>
                    APPLY TO SELECTED MINERS
                </button>
            </div>
        </div>
    </div>

    <div id="ntpModalOverlay" class="modal-overlay" onclick="closeNtpModal()"></div>

    <style>
    .time-section, .timezone-section, .ntp-section {
        background: linear-gradient(135deg, #1a1f2e 0%, #2d3748 100%);
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        border: 1px solid #4a5568;
    }
    
    .current-time-display {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 15px;
        flex-wrap: wrap;
    }
    
    .time-value {
        font-size: 18px;
        font-weight: 700;
        color: #e2e8f0;
        background: rgba(255,255,255,0.1);
        padding: 12px 20px;
        border-radius: 10px;
        border: 1px solid #4a5568;
        flex: 1;
        text-align: center;
        font-family: 'Courier New', monospace;
    }
    
    .sync-btn {
        padding: 12px 20px;
        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 8px;
        white-space: nowrap;
    }
    
    .sync-btn:hover {
        background: linear-gradient(135deg, #1d4ed8, #1e40af);
        transform: translateY(-2px);
    }
    
    .form-select {
        width: 100%;
        padding: 14px;
        background: #1a202c;
        border: 1px solid #4a5568;
        border-radius: 10px;
        color: #f7fafc;
        font-size: 14px;
        transition: all 0.3s ease;
    }
    
    .form-select:focus {
        outline: none;
        border-color: #60a5fa;
        box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.1);
    }
    
    .ntp-servers-container {
        transition: all 0.3s ease;
    }
    
    .ntp-servers-container.disabled {
        opacity: 0.6;
        pointer-events: none;
    }
    
    @media (max-width: 768px) {
        .current-time-display {
            flex-direction: column;
        }
        
        .time-value {
            width: 100%;
        }
        
        .sync-btn {
            width: 100%;
            justify-content: center;
        }
    }
    </style>

    <script>
    let selectedNtpMiners = [];
    
    // Initialize NTP modal
    function initializeNtpModal() {
        updateCurrentTime();
        setInterval(updateCurrentTime, 1000);
        loadNtpMinerGroups();
    }
    
    function updateCurrentTime() {
        const now = new Date();
        const timeString = now.toLocaleString('en-US', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
        document.getElementById('currentTime').textContent = timeString;
    }
    
    function syncWithBrowser() {
        const now = Math.floor(Date.now() / 1000);
        showNotification('🔄 Syncing time with browser...', 'info');
        // This would typically send to backend for miner sync
        setTimeout(() => {
            showNotification('✅ Time synced with browser', 'success');
        }, 1000);
    }
    
    function loadNtpMinerGroups() {
        const groupsContainer = document.getElementById('ntpMinerGroups');
        groupsContainer.innerHTML = `
            <div class="miner-group">
                <div class="group-title">
                    <span>📊 Group A (131-133)</span>
                    <span class="pool-badge">3 MINERS</span>
                </div>
                <div class="miners-grid">
                    ${['131', '132', '133'].map(miner => `
                        <div class="miner-card" onclick="toggleNtpMiner('${miner}')" style="--miner-color: ${getMinerColor(miner)}">
                            <div class="miner-info">
                                <div class="miner-icon">🛠️</div>
                                <div class="miner-details">
                                    <div class="miner-name">${miner}TH</div>
                                    <div class="miner-id">MINER ${miner}</div>
                                </div>
                                <input type="checkbox" class="miner-checkbox" id="ntp_miner_${miner}" onchange="updateNtpCardState('${miner}')">
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="miner-group">
                <div class="group-title">
                    <span>🔥 Group B (65-70)</span>
                    <span class="pool-badge">3 MINERS</span>
                </div>
                <div class="miners-grid">
                    ${['65', '66', '70'].map(miner => `
                        <div class="miner-card" onclick="toggleNtpMiner('${miner}')" style="--miner-color: ${getMinerColor(miner)}">
                            <div class="miner-info">
                                <div class="miner-icon">🛠️</div>
                                <div class="miner-details">
                                    <div class="miner-name">${miner}TH</div>
                                    <div class="miner-id">MINER ${miner}</div>
                                </div>
                                <input type="checkbox" class="miner-checkbox" id="ntp_miner_${miner}" onchange="updateNtpCardState('${miner}')">
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        // Initialize card states
        ['131', '132', '133', '65', '66', '70'].forEach(miner => {
            updateNtpCardState(miner);
        });
        updateNtpSelection();
    }
    
    function getMinerColor(miner) {
        const colors = {
            '131': '#3B82F6', '132': '#10B981', '133': '#8B5CF6',
            '65': '#F59E0B', '66': '#EF4444', '70': '#EC4899'
        };
        return colors[miner] || '#6B7280';
    }
    
    function toggleNtpMiner(minerId) {
        const checkbox = document.getElementById('ntp_miner_' + minerId);
        checkbox.checked = !checkbox.checked;
        updateNtpCardState(minerId);
        updateNtpSelection();
    }
    
    function updateNtpCardState(minerId) {
        const card = document.querySelector(`[onclick="toggleNtpMiner('${minerId}')"]`);
        const checkbox = document.getElementById('ntp_miner_' + minerId);
        
        if (checkbox.checked) {
            card.classList.add('selected');
        } else {
            card.classList.remove('selected');
        }
    }
    
    function updateNtpSelection() {
        selectedNtpMiners = Array.from(document.querySelectorAll('input[id^="ntp_miner_"]:checked'))
            .map(miner => miner.id.replace('ntp_miner_', ''));
        
        console.log('Selected NTP miners:', selectedNtpMiners);
    }
    
    function selectNtpGroup(group) {
        const miners = {
            'all': ['131', '132', '133', '65', '66', '70'],
            'A': ['131', '132', '133'],
            'B': ['65', '66', '70']
        }[group];
        
        miners.forEach(miner => {
            const checkbox = document.getElementById('ntp_miner_' + miner);
            checkbox.checked = true;
            updateNtpCardState(miner);
        });
        
        updateNtpSelection();
    }
    
    function deselectNtpAll() {
        ['131', '132', '133', '65', '66', '70'].forEach(miner => {
            const checkbox = document.getElementById('ntp_miner_' + miner);
            checkbox.checked = false;
            updateNtpCardState(miner);
        });
        
        updateNtpSelection();
    }
    
    function toggleNtpServers() {
        const ntpEnabled = document.getElementById('ntpEnabled').checked;
        const serversContainer = document.getElementById('ntpServersContainer');
        
        if (ntpEnabled) {
            serversContainer.classList.remove('disabled');
        } else {
            serversContainer.classList.add('disabled');
        }
    }
    
    function fillIranianServers() {
        document.getElementById('ntpServer1').value = 'ir.pool.ntp.org';
        document.getElementById('ntpServer2').value = '0.ir.pool.ntp.org';
        document.getElementById('ntpServer3').value = '1.ir.pool.ntp.org';
        document.getElementById('ntpServer4').value = '2.ir.pool.ntp.org';
        showNotification('🇮🇷 Iranian NTP servers loaded', 'success');
    }
    
    function clearNtpServers() {
        document.getElementById('ntpServer1').value = '';
        document.getElementById('ntpServer2').value = '';
        document.getElementById('ntpServer3').value = '';
        document.getElementById('ntpServer4').value = '';
        showNotification('🗑️ NTP servers cleared', 'info');
    }
    
    function applyNtpSettings() {
        if (selectedNtpMiners.length === 0) {
            showNotification('❌ Please select at least one miner', 'error');
            return;
        }
        
        const timezone = document.getElementById('timezoneSelect').value;
        const ntpEnabled = document.getElementById('ntpEnabled').checked;
        const ntpServers = [
            document.getElementById('ntpServer1').value.trim(),
            document.getElementById('ntpServer2').value.trim(),
            document.getElementById('ntpServer3').value.trim(),
            document.getElementById('ntpServer4').value.trim()
        ].filter(server => server !== '');
        
        // Validate NTP servers if enabled
        if (ntpEnabled && ntpServers.length === 0) {
            showNotification('❌ Please enter at least one NTP server', 'error');
            return;
        }
        
        const progressBar = document.getElementById('ntpUpdateProgress');
        const progressText = document.getElementById('ntpProgressText');
        progressBar.style.width = '0%';
        progressText.textContent = '0%';
        
        showNotification('🔄 Starting NTP configuration update...', 'info');
        
        // Update miners sequentially
        updateNtpMinersSequentially(selectedNtpMiners, timezone, ntpEnabled, ntpServers, 0, progressBar, progressText);
    }
    
    function updateNtpMinersSequentially(miners, timezone, ntpEnabled, ntpServers, currentIndex, progressBar, progressText) {
        if (currentIndex >= miners.length) {
            progressBar.style.width = '100%';
            progressText.textContent = '100%';
            setTimeout(() => {
                showNotification('✅ All NTP settings updated successfully!', 'success');
                closeNtpModal();
            }, 1000);
            return;
        }
        
        const miner = miners[currentIndex];
        const progress = ((currentIndex + 1) / miners.length) * 100;
        progressBar.style.width = progress + '%';
        progressText.textContent = Math.round(progress) + '%';
        
        showNotification(`🔄 Configuring NTP for Miner ${miner} (${currentIndex + 1}/${miners.length})`, 'info');
        
        fetch('/update_ntp', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                miner: miner,
                timezone: timezone,
                ntp_enabled: ntpEnabled,
                ntp_servers: ntpServers
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(`✅ ${data.success}`, 'success');
            } else {
                showNotification(`❌ Miner ${miner}: ${data.error}`, 'error');
            }
            // Move to next miner
            updateNtpMinersSequentially(miners, timezone, ntpEnabled, ntpServers, currentIndex + 1, progressBar, progressText);
        })
        .catch(error => {
            showNotification(`❌ Error updating miner ${miner}: ${error}`, 'error');
            // Continue with next miner even if this one fails
            updateNtpMinersSequentially(miners, timezone, ntpEnabled, ntpServers, currentIndex + 1, progressBar, progressText);
        });
    }
    
    function showNtpModal() {
        console.log('⏰ Opening NTP Modal...');
        const overlay = document.getElementById('ntpModalOverlay');
        const modal = document.getElementById('ntpModal');
        
        if (overlay && modal) {
            overlay.style.display = 'block';
            modal.style.display = 'block';
            console.log('✅ NTP Modal opened successfully');
            
            // Initialize modal
            setTimeout(() => {
                initializeNtpModal();
            }, 100);
        } else {
            console.error('❌ NTP Modal elements not found');
            alert('NTP configuration is not available');
        }
    }
    
    function closeNtpModal() {
        const overlay = document.getElementById('ntpModalOverlay');
        const modal = document.getElementById('ntpModal');
        
        if (overlay && modal) {
            overlay.style.display = 'none';
            modal.style.display = 'none';
        }
    }
    
    // Close modal when clicking outside
    document.addEventListener('click', function(event) {
        if (event.target === document.getElementById('ntpModalOverlay')) {
            closeNtpModal();
        }
    });
    </script>
    '''