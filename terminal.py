#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import socket

def send_tcp_json(ip, port, payload, timeout=3.0):
    """ارسال دستور به ماینر از طریق TCP"""
    if not ip:
        return None
    data = json.dumps(payload).encode("utf-8")
    try:
        with socket.create_connection((ip, port), timeout=timeout) as s:
            s.settimeout(timeout)
            s.sendall(data)
            chunks = []
            while True:
                try:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
                except socket.timeout:
                    break
            raw = b"".join(chunks).decode("utf-8", errors="ignore").strip()
            if not raw:
                return None
            try:
                return json.loads(raw)
            except Exception:
                first = raw.find("{")
                last = raw.rfind("}")
                if first != -1 and last != -1 and last > first:
                    sub = raw[first:last+1]
                    try:
                        return json.loads(sub)
                    except Exception:
                        return None
            return None
    except Exception:
        return None

def execute_terminal_command(miner_name, command, miner_ip, miner_names, miner_ports):
    """اجرای دستور ترمینال برای ماینر مشخص"""
    try:
        if not miner_name:
            return {"error": "No miner provided"}

        # استخراج نام ماینر از ورودی کاربر
        miner_key = miner_name.split()[0].strip()
        
        # پیدا کردن ماینر در لیست
        if miner_key not in miner_names:
            # جستجوی جزئی
            found = None
            for k in miner_names:
                if miner_key == k or miner_name.startswith(k) or k in miner_name:
                    found = k
                    break
            if found:
                miner_key = found
            else:
                return {"error": f"Miner {miner_name} not found"}

        # پیدا کردن پورت ماینر - استفاده از MINER_PORTS اصلی
        idx = miner_names.index(miner_key)
        port = miner_ports[idx]

        # ارسال دستور به ماینر
        payload = {"command": command}
        response = send_tcp_json(miner_ip, port, payload)

        if not response:
            return {"error": f"No response from miner {miner_key} on port {port}"}

        # فرمت کردن خروجی
        formatted_output = json.dumps(response, indent=2, ensure_ascii=False)
        return {"output": formatted_output}

    except ValueError:
        return {"error": f"Miner {miner_name} not found in available miners"}
    except Exception as e:
        return {"error": f"Terminal error: {str(e)}"}

def get_terminal_html():
    """HTML مربوط به ترمینال"""
    return '''
    <!-- Terminal Modal -->
    <div id="terminalOverlay" class="modal-overlay" onclick="closeTerminal()"></div>
    <div id="terminalModal" class="modal" aria-hidden="true">
        <h3>💻 Miner Terminal</h3>
        <div style="display:flex; gap:10px; justify-content:center; margin-bottom:10px; flex-wrap:wrap;">
            <input id="minerInput" list="minersList" type="text" placeholder="e.g. 131" style="padding:8px; width:110px; border-radius:6px; border:1px solid #ccc;">
            <datalist id="minersList">
                {% for n in MINER_NAMES %}
                <option value="{{ n }}"></option>
                {% endfor %}
            </datalist>
            <select id="cmdInput" style="padding:8px; border-radius:6px; border:1px solid #ccc;">
                <option value="summary">summary</option>
                <option value="devs">devs</option>
            </select>
            <button class="button" onclick="sendCommand()">Run</button>
        </div>
        <div id="terminalOutput" class="terminal-pre">Ready.</div>
        <div style="text-align:center; margin-top:10px;">
            <button onclick="closeTerminal()" style="background:#e74c3c; color:white; padding:8px 16px; border:none; border-radius:6px;">❌ Close</button>
        </div>
    </div>

    <script>
    // Terminal functions
    function openTerminal(){
        document.getElementById('terminalOverlay').style.display='block';
        document.getElementById('terminalModal').style.display='block';
        document.getElementById('terminalOutput').textContent='⏳ Ready...';
        document.getElementById('terminalModal').setAttribute('aria-hidden','false');
    }
    
    function closeTerminal(){
        document.getElementById('terminalOverlay').style.display='none';
        document.getElementById('terminalModal').style.display='none';
        document.getElementById('terminalModal').setAttribute('aria-hidden','true');
    }

    function sendCommand(){
        const miner = document.getElementById('minerInput').value.trim();
        const cmd = document.getElementById('cmdInput').value;
        const output = document.getElementById('terminalOutput');

        if (!miner) {
            output.textContent = "⚠️ Please enter miner name (e.g. 131).";
            return;
        }

        output.textContent = "⏳ Running...";

        fetch('/terminal_command', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({miner, cmd})
        })
        .then(r => r.json())
        .then(data => {
            if(data.output){
                let formatted = data.output
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/("(\\\\u[a-zA-Z0-9]{4}|\\\\[^u]|[^\\\\"])*")(\\s*):/g, '<span style="color:green;">$1</span>$3:')
                    .replace(/:\\s*("(\\\\u[a-zA-Z0-9]{4}|\\\\[^u]|[^\\\\"])*"|[\\d.eE+-]+)/g, ': <span style="color:red;">$1</span>')
                    .replace(/([{}\\[\\]\\(\\)])/g, '<span style="color:blue;">$1</span>');

                output.innerHTML = '<pre class="terminal-pre">' + formatted + '</pre>';
            } else if(data.error){
                output.textContent = "❌ " + data.error;
            } else {
                output.textContent = "❌ Invalid response";
            }
        })
        .catch(err => {
            output.textContent = "⚠️ Connection error: " + err;
        });
    }
    </script>
    '''