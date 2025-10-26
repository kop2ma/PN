#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
from bs4 import BeautifulSoup

# Pool Configuration - Easy to change
POOL1_URL = "stratum+tcp://sha256.poolbinance.com:443"
POOL2_URL = "stratum+tcp://bs.poolbinance.com:3333" 
POOL3_URL = "stratum+tcp://btc.poolbinance.com:1800"
POOL_PASSWORD = "123"

# خواندن تنظیمات از environment
MINER_IP = os.environ.get("MINER_IP")
MINER_USERNAME = "admin"
MINER_PASSWORD = os.environ.get("MINER_PASSWORD")

# Map name -> port
port_map = {
    "131": 201, "132": 202, "133": 203,
    "65": 301, "66": 302, "70": 303
}

# گروه‌بندی ماینرها
MINER_GROUPS = {
    "Group A (131-133)": ["131", "132", "133"],
    "Group B (65-70)": ["65", "66", "70"]
}

# رنگ‌های مخصوص هر ماینر
MINER_COLORS = {
    "131": "#3B82F6", "132": "#10B981", "133": "#8B5CF6",
    "65": "#F59E0B", "66": "#EF4444", "70": "#EC4899"
}

# آیکون‌های مخصوص هر ماینر - جدید و خفن‌تر!
MINER_ICONS = {
    "131": "🛠️", "132": "🛠️", "133": "🛠️",
    "65": "🛠️", "66": "🛠️", "70": "🛠️"
}

# نام‌های فانتزی برای ماینرها
MINER_NAMES = {
    "131": "131TH", "132": "132TH", "133": "133TH",
    "65": "65TH", "66": "66TH", "70": "70TH"
}

def login_to_miner(miner_name, username, password):
    """Login to miner and return session"""
    miner_port = port_map.get(miner_name)
    if not miner_port:
        print(f"❌ Port not found for miner {miner_name}")
        return None
    
    base_url = f"https://{MINER_IP}:{miner_port}"
    login_url = f"{base_url}/cgi-bin/luci"
    
    session = requests.Session()
    session.verify = False
    requests.packages.urllib3.disable_warnings()
    
    try:
        print(f"🔐 Attempting login to miner {miner_name}...")
        response = session.get(login_url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        login_data = {
            'luci_username': username,
            'luci_password': password
        }
        
        login_response = session.post(login_url, data=login_data, timeout=10, allow_redirects=False)
        
        if login_response.status_code in [302, 303]:
            print(f"✅ Successfully logged into miner {miner_name}")
            return session
        else:
            print(f"❌ Login failed for miner {miner_name} - Status: {login_response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Login error for miner {miner_name}: {str(e)}")
        return None

def update_miner_pools(miner_name, pools_data, username, password):
    """Update pool settings for a miner"""
    print(f"🔄 Starting pool update for miner {miner_name}...")
    
    session = login_to_miner(miner_name, username, password)
    if not session:
        return {"error": "Login failed"}
    
    try:
        miner_port = port_map.get(miner_name)
        pool_url_page = f"https://{MINER_IP}:{miner_port}/cgi-bin/luci/admin/network/btminer"
        
        print(f"📄 Loading pool configuration page for {miner_name}...")
        response = session.get(pool_url_page, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        token_input = soup.find('input', {'name': 'token'})
        if not token_input:
            return {"error": "Cannot find form token"}
        
        token = token_input.get('value')
        form_data = {
            'token': token,
            'cbi.submit': '1',
            'cbi.apply': 'Save & Apply'
        }
        
        # Add pool data to form
        print(f"📝 Applying pool settings for {miner_name}...")
        for pool_num, pool_info in pools_data.items():
            form_data[f'cbid.pools.default.pool{pool_num}url'] = pool_info['url']
            form_data[f'cbid.pools.default.pool{pool_num}user'] = pool_info['worker']
            form_data[f'cbid.pools.default.pool{pool_num}pw'] = pool_info['password']
            print(f"   Pool {pool_num}: {pool_info['url']}")
        
        update_response = session.post(pool_url_page, data=form_data, timeout=10)
        
        if update_response.status_code == 200:
            print(f"✅ Pools successfully updated for miner {miner_name}")
            return {"success": f"Pools updated for miner {miner_name}"}
        else:
            print(f"❌ Update failed for {miner_name} - Status: {update_response.status_code}")
            return {"error": f"Update failed with status {update_response.status_code}"}
            
    except Exception as e:
        print(f"❌ Connection error for {miner_name}: {str(e)}")
        return {"error": f"Connection error: {str(e)}"}

def get_pools_manager_html():
    """Return HTML for pools management interface"""
    return f'''
    <!-- Pools Configuration Modal -->
    <div id="poolsModal" class="modal">
        <div class="modal-header">
            <h3 class="modal-title" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">🚀 POOLS CONFIGURATION</h3>
            <button class="modal-close" onclick="closePoolsModal()" style="background: #ef4444; color: white; border: none; border-radius: 50%; width: 32px; height: 32px; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center;">×</button>
        </div>
        
        <!-- Miner Selection Section -->
        <div class="miner-selection-section">
            <div class="section-header">
                <h4>🎯 SELECT MINERS</h4>
                <div class="group-controls">
                    <button class="group-btn" onclick="selectGroup('all')">SELECT ALL</button>
                    <button class="group-btn" onclick="selectGroup('A')">GROUP A</button>
                    <button class="group-btn" onclick="selectGroup('B')">GROUP B</button>
                    <button class="group-btn" onclick="deselectAll()">CLEAR ALL</button>
                </div>
            </div>
            
            <div class="miner-groups-container">
    {generate_miner_groups_html()}
            </div>
        </div>

        <!-- Pools Configuration -->
        <div class="pools-config-section">
            <div class="section-header">
                <h4>🏊 POOLS SETTINGS</h4>
                <div class="pool-actions">
                    <button class="action-btn" onclick="fillSampleData()">📝 FILL SAMPLE</button>
                    <button class="action-btn" onclick="clearAllPools()">🗑️ CLEAR ALL</button>
                    <button class="action-btn" onclick="autoFillWorkers()">👤 AUTO WORKERS</button>
                </div>
            </div>
            
            <div class="pools-grid">
    {generate_pools_html()}
            </div>
        </div>

        <!-- Progress & Actions -->
        <div class="action-section">
            <div class="progress-container">
                <div class="progress-header">
                    <span>PROGRESS</span>
                    <span id="progressText">0%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="updateProgress" style="width: 0%"></div>
                </div>
            </div>
            
            <div class="action-buttons">
                <button class="btn-cancel" onclick="closePoolsModal()">
                    <span>✕</span>
                    CANCEL
                </button>
                <button class="btn-apply" onclick="applyPoolSettings()">
                    <span>💾</span>
                    APPLY TO SELECTED MINERS
                </button>
            </div>
        </div>
    </div>

    <div id="poolsModalOverlay" class="modal-overlay" onclick="closePoolsModal()"></div>

    <style>
    .miner-selection-section {{
        background: linear-gradient(135deg, #1a1f2e 0%, #2d3748 100%);
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        border: 1px solid #4a5568;
    }}
    
    .section-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        flex-wrap: wrap;
        gap: 15px;
    }}
    
    .section-header h4 {{
        color: #e2e8f0;
        font-size: 16px;
        font-weight: 700;
        margin: 0;
        background: linear-gradient(135deg, #60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}
    
    .group-controls, .pool-actions {{
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }}
    
    .group-btn, .action-btn {{
        padding: 8px 16px;
        border: none;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        background: #4a5568;
        color: #e2e8f0;
        border: 1px solid #718096;
    }}
    
    .group-btn:hover, .action-btn:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }}
    
    .group-btn:nth-child(1):hover {{ background: #10b981; border-color: #10b981; }}
    .group-btn:nth-child(2):hover {{ background: #3b82f6; border-color: #3b82f6; }}
    .group-btn:nth-child(3):hover {{ background: #8b5cf6; border-color: #8b5cf6; }}
    .group-btn:nth-child(4):hover {{ background: #ef4444; border-color: #ef4444; }}
    
    .action-btn:nth-child(3):hover {{ background: #8b5cf6; border-color: #8b5cf6; }}
    
    .miner-groups-container {{
        display: flex;
        flex-direction: column;
        gap: 15px;
    }}
    
    .miner-group {{
        background: #2d3748;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #4a5568;
    }}
    
    .group-title {{
        color: #cbd5e0;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    
    .miners-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 12px;
    }}
    
    .miner-card {{
        background: #1a202c;
        border: 2px solid #4a5568;
        border-radius: 12px;
        padding: 15px;
        cursor: pointer;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }}
    
    .miner-card::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: var(--miner-color);
    }}
    
    .miner-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.4);
        border-color: var(--miner-color);
    }}
    
    .miner-card.selected {{
        border-color: var(--miner-color);
        background: linear-gradient(135deg, #1a202c 0%, var(--miner-color) 200%);
        box-shadow: 0 6px 20px rgba(0,0,0,0.4);
    }}
    
    .miner-info {{
        display: flex;
        align-items: center;
        gap: 12px;
    }}
    
    .miner-icon {{
        font-size: 24px;
        width: 45px;
        height: 45px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(255,255,255,0.1);
        border-radius: 10px;
        border: 2px solid rgba(255,255,255,0.2);
    }}
    
    .miner-details {{
        flex: 1;
    }}
    
    .miner-name {{
        color: #e2e8f0;
        font-size: 15px;
        font-weight: 700;
        margin: 0 0 4px 0;
    }}
    
    .miner-id {{
        color: #a0aec0;
        font-size: 12px;
        font-weight: 500;
        background: rgba(255,255,255,0.1);
        padding: 2px 8px;
        border-radius: 6px;
        display: inline-block;
    }}
    
    .miner-port {{
        color: #cbd5e0;
        font-size: 11px;
        font-weight: 500;
        margin-top: 4px;
    }}
    
    .miner-checkbox {{
        width: 20px;
        height: 20px;
        border: 2px solid #4a5568;
        border-radius: 6px;
        background: #2d3748;
        cursor: pointer;
        transition: all 0.3s ease;
        position: relative;
    }}
    
    .miner-checkbox:checked {{
        background: var(--miner-color);
        border-color: var(--miner-color);
    }}
    
    .miner-checkbox:checked::after {{
        content: '✓';
        position: absolute;
        color: white;
        font-size: 14px;
        font-weight: bold;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
    }}
    
    .pools-config-section {{
        background: linear-gradient(135deg, #1a1f2e 0%, #2d3748 100%);
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        border: 1px solid #4a5568;
    }}
    
    .pools-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 20px;
    }}
    
    .pool-card {{
        background: #2d3748;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #4a5568;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }}
    
    .pool-card::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #ff6b6b, #ee5a24);
    }}
    
    .pool-card:nth-child(2)::before {{
        background: linear-gradient(90deg, #48dbfb, #0abde3);
    }}
    
    .pool-card:nth-child(3)::before {{
        background: linear-gradient(90deg, #1dd1a1, #10ac84);
    }}
    
    .pool-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
    }}
    
    .pool-header {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 18px;
    }}
    
    .pool-icon {{
        font-size: 28px;
        width: 50px;
        height: 50px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(255,255,255,0.1);
        border-radius: 12px;
        border: 2px solid rgba(255,255,255,0.2);
    }}
    
    .pool-title {{
        color: #e2e8f0;
        font-size: 18px;
        font-weight: 700;
        margin: 0;
    }}
    
    .pool-badge {{
        background: #4a5568;
        color: #e2e8f0;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 11px;
        font-weight: 600;
    }}
    
    .form-group {{
        margin-bottom: 18px;
    }}
    
    .form-label {{
        display: block;
        margin-bottom: 8px;
        color: #cbd5e0;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    
    .form-input {{
        width: 100%;
        padding: 14px;
        background: #1a202c;
        border: 1px solid #4a5568;
        border-radius: 10px;
        color: #f7fafc;
        font-size: 14px;
        transition: all 0.3s ease;
        font-family: 'Courier New', monospace;
    }}
    
    .form-input:focus {{
        outline: none;
        border-color: #60a5fa;
        box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.1);
        background: #2d3748;
    }}
    
    .form-input::placeholder {{
        color: #718096;
    }}
    
    .action-section {{
        background: linear-gradient(135deg, #1a1f2e 0%, #2d3748 100%);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #4a5568;
    }}
    
    .progress-container {{
        margin-bottom: 20px;
    }}
    
    .progress-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }}
    
    .progress-header span {{
        color: #e2e8f0;
        font-size: 13px;
        font-weight: 600;
    }}
    
    .progress-bar {{
        width: 100%;
        height: 10px;
        background: #4a5568;
        border-radius: 5px;
        overflow: hidden;
    }}
    
    .progress-fill {{
        height: 100%;
        background: linear-gradient(90deg, #10b981, #34d399);
        transition: width 0.3s ease;
        border-radius: 5px;
    }}
    
    .action-buttons {{
        display: flex;
        gap: 12px;
        justify-content: flex-end;
    }}
    
    .btn-cancel, .btn-apply {{
        padding: 14px 28px;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 14px;
    }}
    
    .btn-cancel {{
        background: #4a5568;
        color: #e2e8f0;
        border: 1px solid #718096;
    }}
    
    .btn-cancel:hover {{
        background: #718096;
        transform: translateY(-2px);
    }}
    
    .btn-apply {{
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        border: 1px solid #10b981;
    }}
    
    .btn-apply:hover {{
        background: linear-gradient(135deg, #059669, #047857);
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
    }}
    
    @media (max-width: 768px) {{
        .section-header {{
            flex-direction: column;
            align-items: stretch;
        }}
        
        .group-controls, .pool-actions {{
            justify-content: center;
        }}
        
        .miners-grid {{
            grid-template-columns: 1fr;
        }}
        
        .pools-grid {{
            grid-template-columns: 1fr;
        }}
        
        .action-buttons {{
            flex-direction: column;
        }}
    }}
    </style>

    <script>
    // Pool Configuration Variables
    const POOL1_URL = "{POOL1_URL}";
    const POOL2_URL = "{POOL2_URL}";
    const POOL3_URL = "{POOL3_URL}";
    const POOL_PASSWORD = "{POOL_PASSWORD}";

    let selectedMiners = [];
    
    function toggleMiner(minerId) {{
        const checkbox = document.getElementById('miner_' + minerId);
        checkbox.checked = !checkbox.checked;
        updateCardState(minerId);
        updateSelection();
    }}

    function updateCardState(minerId) {{
        const card = document.querySelector(`[onclick="toggleMiner('${{minerId}}')"]`);
        const checkbox = document.getElementById('miner_' + minerId);
        
        if (checkbox.checked) {{
            card.classList.add('selected');
        }} else {{
            card.classList.remove('selected');
        }}
    }}

    function updateSelection() {{
        selectedMiners = Array.from(document.querySelectorAll('input[name="miners"]:checked'))
            .map(miner => miner.value);
        
        console.log('Selected miners:', selectedMiners);
    }}

    function selectGroup(group) {{
        const miners = {{
            'all': ['131', '132', '133', '65', '66', '70'],
            'A': ['131', '132', '133'],
            'B': ['65', '66', '70']
        }}[group];
        
        miners.forEach(miner => {{
            const checkbox = document.getElementById('miner_' + miner);
            checkbox.checked = true;
            updateCardState(miner);
        }});
        
        updateSelection();
    }}

    function deselectAll() {{
        ['131', '132', '133', '65', '66', '70'].forEach(miner => {{
            const checkbox = document.getElementById('miner_' + miner);
            checkbox.checked = false;
            updateCardState(miner);
        }});
        
        updateSelection();
    }}

    function autoFillWorkers() {{
        if (selectedMiners.length === 0) {{
            showNotification('❌ Please select miners first', 'error');
            return;
        }}
        
        // Get main worker from user
        const mainWorker = prompt('👤 Enter main worker name:\\n(Example: Ali or Charli)', 'Ali');
        
        if (!mainWorker) {{
            showNotification('❌ No worker name entered', 'error');
            return;
        }}
        
        // Only show for first miner (preview)
        const firstMiner = selectedMiners[0];
        document.getElementById('pool1_worker').value = mainWorker + '.' + firstMiner;
        document.getElementById('pool2_worker').value = mainWorker + '.' + firstMiner;
        document.getElementById('pool3_worker').value = mainWorker + '.' + firstMiner;
        
        // Notify user
        if (selectedMiners.length > 1) {{
            showNotification(`✅ Workers will be set for ${{selectedMiners.length}} miners`, 'info');
        }} else {{
            showNotification(`✅ Worker set: ${{mainWorker}}.${{firstMiner}}`, 'success');
        }}
    }}

    function fillSampleData() {{
        document.getElementById('pool1_url').value = POOL1_URL;
        document.getElementById('pool1_worker').value = 'kop1ma.131';
        document.getElementById('pool1_password').value = POOL_PASSWORD;
        
        document.getElementById('pool2_url').value = POOL2_URL;
        document.getElementById('pool2_worker').value = 'kop1ma.131';
        document.getElementById('pool2_password').value = POOL_PASSWORD;
        
        document.getElementById('pool3_url').value = POOL3_URL;
        document.getElementById('pool3_worker').value = 'kop1ma.131';
        document.getElementById('pool3_password').value = POOL_PASSWORD;
    }}

    function clearAllPools() {{
        document.querySelectorAll('.form-input').forEach(input => {{
            input.value = '';
        }});
    }}

    function applyPoolSettings() {{
        if (selectedMiners.length === 0) {{
            showNotification('❌ Please select at least one miner', 'error');
            return;
        }}

        const poolsData = {{
            1: {{
                url: document.getElementById('pool1_url').value.trim(),
                worker: document.getElementById('pool1_worker').value.trim(),
                password: document.getElementById('pool1_password').value.trim()
            }},
            2: {{
                url: document.getElementById('pool2_url').value.trim(),
                worker: document.getElementById('pool2_worker').value.trim(),
                password: document.getElementById('pool2_password').value.trim()
            }},
            3: {{
                url: document.getElementById('pool3_url').value.trim(),
                worker: document.getElementById('pool3_worker').value.trim(),
                password: document.getElementById('pool3_password').value.trim()
            }}
        }};

        // Validate pool data
        for (let poolNum in poolsData) {{
            const pool = poolsData[poolNum];
            if (!pool.url || !pool.worker) {{
                showNotification(`❌ Please fill URL and Worker for Pool ${{poolNum}}`, 'error');
                return;
            }}
            
            if (!pool.url.startsWith('stratum+tcp://')) {{
                showNotification(`❌ Pool ${{poolNum}} URL must start with stratum+tcp://`, 'error');
                return;
            }}
        }}

        const progressBar = document.getElementById('updateProgress');
        const progressText = document.getElementById('progressText');
        progressBar.style.width = '0%';
        progressText.textContent = '0%';

        showNotification('🚀 Starting pool configuration update...', 'info');
        
        // Update miners sequentially
        updateMinersSequentially(selectedMiners, poolsData, 0, progressBar, progressText);
    }}

    function updateMinersSequentially(miners, poolsData, currentIndex, progressBar, progressText) {{
        if (currentIndex >= miners.length) {{
            progressBar.style.width = '100%';
            progressText.textContent = '100%';
            setTimeout(() => {{
                showNotification('✅ All pool settings updated successfully!', 'success');
                closePoolsModal();
                // Reset form
                document.querySelectorAll('input[type="text"]').forEach(input => input.value = '');
                deselectAll();
            }}, 1000);
            return;
        }}

        const miner = miners[currentIndex];
        const progress = ((currentIndex + 1) / miners.length) * 100;
        progressBar.style.width = progress + '%';
        progressText.textContent = Math.round(progress) + '%';

        showNotification(`🔄 Configuring Miner ${{miner}} (${{currentIndex + 1}}/${{miners.length}})`, 'info');

        // برای هر ماینر worker مخصوص خودش رو تنظیم کن
        const minerPoolsData = JSON.parse(JSON.stringify(poolsData));
        const mainWorker = minerPoolsData[1].worker.split('.')[0]; // گرفتن بخش اول (مثلاً Ali)
        
        for (let poolNum in minerPoolsData) {{
            minerPoolsData[poolNum].worker = mainWorker + '.' + miner; // مثلاً Ali.131
        }}

        fetch('/update_pools', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                miner: miner,
                pools: minerPoolsData
            }})
        }})
        .then(response => response.json())
        .then(data => {{
            if (data.success) {{
                showNotification(`✅ ${{data.success}}`, 'success');
            }} else {{
                showNotification(`❌ Miner ${{miner}}: ${{data.error}}`, 'error');
            }}
            // Move to next miner
            updateMinersSequentially(miners, poolsData, currentIndex + 1, progressBar, progressText);
        }})
        .catch(error => {{
            showNotification(`❌ Error updating miner ${{miner}}: ${{error}}`, 'error');
            // Continue with next miner even if this one fails
            updateMinersSequentially(miners, poolsData, currentIndex + 1, progressBar, progressText);
        }});
    }}

    function showPoolsModal() {{
        console.log('🏊 Opening Pools Modal...');
        const overlay = document.getElementById('poolsModalOverlay');
        const modal = document.getElementById('poolsModal');
        
        if (overlay && modal) {{
            overlay.style.display = 'block';
            modal.style.display = 'block';
            console.log('✅ Pools Modal opened successfully');
            
            // Reset selection
            setTimeout(() => {{
                updateSelection();
            }}, 100);
        }} else {{
            console.error('❌ Pools Modal elements not found');
            alert('Pools configuration is not available');
        }}
    }}

    function closePoolsModal() {{
        const overlay = document.getElementById('poolsModalOverlay');
        const modal = document.getElementById('poolsModal');
        
        if (overlay && modal) {{
            overlay.style.display = 'none';
            modal.style.display = 'none';
        }}
    }}

    function showNotification(message, type) {{
        // Create notification element
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 600;
            z-index: 10000;
            max-width: 400px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            animation: slideIn 0.3s ease;
            background: ${{type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#3b82f6'}};
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {{
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {{
                document.body.removeChild(notification);
            }}, 300);
        }}, 3000);
    }}

    // Add CSS for animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {{
            from {{ transform: translateX(100%); opacity: 0; }}
            to {{ transform: translateX(0); opacity: 1; }}
        }}
        @keyframes slideOut {{
            from {{ transform: translateX(0); opacity: 1; }}
            to {{ transform: translateX(100%); opacity: 0; }}
        }}
    `;
    document.head.appendChild(style);

    // Close modal when clicking outside
    document.addEventListener('click', function(event) {{
        if (event.target === document.getElementById('poolsModalOverlay')) {{
            closePoolsModal();
        }}
    }});

    // Initialize miner cards
    setTimeout(() => {{
        ['131', '132', '133', '65', '66', '70'].forEach(miner => {{
            updateCardState(miner);
        }});
        updateSelection();
    }}, 100);
    </script>
    '''

def generate_miner_groups_html():
    """Generate HTML for miner groups selection"""
    html = ''
    for group_name, miners in MINER_GROUPS.items():
        html += f'''
        <div class="miner-group">
            <div class="group-title">
                <span>{"📊" if "A" in group_name else "🔥"} {group_name}</span>
                <span class="pool-badge">{len(miners)} MINERS</span>
            </div>
            <div class="miners-grid">
        '''
        
        for miner in miners:
            html += f'''
                <div class="miner-card" onclick="toggleMiner('{miner}')" style="--miner-color: {MINER_COLORS[miner]}">
                    <div class="miner-info">
                        <div class="miner-icon">{MINER_ICONS[miner]}</div>
                        <div class="miner-details">
                            <div class="miner-name">{MINER_NAMES[miner]}</div>
                            <div class="miner-id">MINER {miner}</div>
                            <div class="miner-port">Port: {port_map[miner]}</div>
                        </div>
                        <input type="checkbox" class="miner-checkbox" id="miner_{miner}" name="miners" value="{miner}" onchange="updateCardState('{miner}')">
                    </div>
                </div>
            '''
        
        html += '''
            </div>
        </div>
        '''
    
    return html

def generate_pools_html():
    """Generate HTML for pools configuration"""
    pools = [
        {"number": 1, "title": "PRIMARY POOL", "badge": "MAIN", "icon": "🏆"},
        {"number": 2, "title": "BACKUP POOL", "badge": "SECONDARY", "icon": "🛡️"},
        {"number": 3, "title": "BACKUP POOL", "badge": "TERTIARY", "icon": "⚡"}
    ]
    
    html = ''
    for pool in pools:
        html += f'''
        <div class="pool-card">
            <div class="pool-header">
                <div class="pool-icon">{pool['icon']}</div>
                <div>
                    <div class="pool-title">{pool['title']}</div>
                    <div class="pool-badge">{pool['badge']}</div>
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">POOL URL</label>
                <input type="text" class="form-input" id="pool{pool['number']}_url" placeholder="stratum+tcp://pool.com:443">
            </div>
            <div class="form-group">
                <label class="form-label">WORKER NAME</label>
                <input type="text" class="form-input" id="pool{pool['number']}_worker" placeholder="kop1ma.131">
            </div>
            <div class="form-group">
                <label class="form-label">PASSWORD</label>
                <input type="text" class="form-input" id="pool{pool['number']}_password" placeholder="x" value="x">
            </div>
        </div>
        '''
    
    return html