import os
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Global states
REPORTS = []
RECEIPTS = []


DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>SAP Concur Expense Dashboard</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background-color: #f7f9fa; }
        .section-title { margin-top: 30px; border-bottom: 2px solid #e0e5ea; padding-bottom: 5px; color: #1a1a1a; }
        .report-card { border: 1px solid #e1e4e6; border-radius: 8px; background: white; padding: 15px; margin: 15px 0; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .report-info { flex: 1; }
        .report-name { font-weight: bold; font-size: 1.1em; color: #1a1a1a; }
        .report-purpose { color: #5c646b; margin-left: 10px; font-style: italic; }
        .button { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 0.9em; }
        #create-report-btn { background-color: #0070d2; color: white; margin-bottom: 10px; }
        .edit-btn { background-color: #e0e5ea; color: #0070d2; margin-right: 10px; }
        .delete-btn { background-color: #c23934; color: white; }
        #report-dialog { border: 1px solid #c9c9c9; border-radius: 6px; padding: 25px; position: absolute; background: white; top: 100px; left: 100px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); width: 350px; z-index: 1000; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-group input, .form-group textarea { width: 95%; padding: 8px; border: 1px solid #c9c9c9; border-radius: 4px; }
        .form-actions { display: flex; justify-content: flex-end; }
        .form-actions button { margin-left: 10px; }
        
        /* Available Receipts Gallery */
        .receipt-gallery { display: flex; gap: 15px; flex-wrap: wrap; margin-top: 15px; }
        .available-receipt-thumbnail { border: 1px solid #c9c9c9; border-radius: 6px; padding: 15px; width: 120px; text-align: center; background: white; cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .available-receipt-thumbnail:hover { border-color: #0070d2; }
        .receipt-icon { font-size: 2em; display: block; margin-bottom: 5px; }
        .receipt-name { font-size: 0.85em; word-break: break-all; font-weight: bold; color: #1a1a1a; }
        #receipt-modal { border: 1px solid #c9c9c9; border-radius: 6px; padding: 25px; position: absolute; background: white; top: 150px; left: 150px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); width: 300px; z-index: 1001; text-align: center; }
        #receipt-modal img { max-width: 100%; height: auto; border: 1px solid #ccc; margin-bottom: 15px; }
    </style>
</head>
<body>
    <h1>Expense Dashboard</h1>
    
    <h2 class="section-title">Expense Reports</h2>
    <button id="create-report-btn" class="button" onclick="showCreateModal()">Create New Report</button>
    <div id="reports-container"></div>

    <h2 class="section-title">Available Receipts</h2>
    <div id="receipts-container" class="receipt-gallery"></div>

    <!-- Create/Edit Modal Dialog -->
    <div id="report-dialog" style="display:none;">
        <h2 id="dialog-title">Create Report</h2>
        <form onsubmit="saveReport(event)">
            <input type="hidden" id="edit-index">
            <div class="form-group">
                <label for="reportname">Report Name</label>
                <input type="text" id="reportname" required>
            </div>
            <div class="form-group">
                <label for="purpose">Purpose</label>
                <input type="text" id="purpose">
            </div>
            <div class="form-group">
                <label for="comment">Comment</label>
                <textarea id="comment"></textarea>
            </div>
            <div class="form-actions">
                <button type="button" class="button" onclick="closeDialog()">Cancel</button>
                <button type="submit" id="submit-report-btn" class="button">Create Report</button>
            </div>
        </form>
    </div>

    <!-- Receipt Viewer Dialog -->
    <div id="receipt-modal" style="display:none;">
        <h2>Receipt Viewer</h2>
        <div style="padding: 10px; background: #f0f0f0; border: 1px dashed #ccc; margin-bottom: 15px;">
            <span style="font-size: 3em;">📄</span>
        </div>
        <p id="receipt-modal-name" class="receipt-name"></p>
        <div style="margin-top: 20px;">
            <button type="button" class="button" onclick="closeReceiptModal()" style="margin-right:10px;">Close</button>
            <button type="button" id="delete-receipt-btn" class="button delete-btn" onclick="triggerDeleteReceipt()">Delete Receipt</button>
        </div>
    </div>

    <script>
        // Fetch reports list from server
        async function fetchReports() {
            const res = await fetch('/api/reports');
            const reports = await res.json();
            renderReports(reports);
        }

        // Fetch receipts list from server
        async function fetchReceipts() {
            const res = await fetch('/api/receipts');
            const receipts = await res.json();
            renderReceipts(receipts);
        }

        function renderReports(reports) {
            const container = document.getElementById('reports-container');
            container.innerHTML = '';
            if (reports.length === 0) {
                container.innerHTML = '<p class="no-reports">No reports found.</p>';
                return;
            }
            reports.forEach((r, idx) => {
                const card = document.createElement('div');
                card.className = 'report-card';
                card.innerHTML = `
                    <div class="report-info">
                        <span class="report-name">${r.name}</span>
                        <span class="report-purpose">(${r.purpose || 'No Purpose'})</span>
                        <p style="margin: 5px 0 0 0; font-size:12px; color:#5c646b;">Comment: ${r.comment || 'None'}</p>
                    </div>
                    <div>
                        <button class="button edit-btn" onclick="showEditModal(${idx}, '${r.name}', '${r.purpose || ''}', '${r.comment || ''}')">Edit</button>
                        <button class="button delete-btn" onclick="deleteReport('${r.name}')">Delete</button>
                    </div>
                `;
                container.appendChild(card);
            });
        }

        function renderReceipts(receipts) {
            const container = document.getElementById('receipts-container');
            container.innerHTML = '';
            if (receipts.length === 0) {
                container.innerHTML = '<p class="no-reports">No available receipts.</p>';
                return;
            }
            receipts.forEach((r) => {
                const thumb = document.createElement('div');
                thumb.className = 'available-receipt-thumbnail';
                thumb.onclick = () => showReceiptModal(r.name);
                thumb.innerHTML = `
                    <span class="receipt-icon">📄</span>
                    <span class="receipt-name">${r.name}</span>
                `;
                container.appendChild(thumb);
            });
        }

        let selectedReceiptName = '';
        function showReceiptModal(name) {
            selectedReceiptName = name;
            document.getElementById('receipt-modal-name').innerText = name;
            document.getElementById('receipt-modal').style.display = 'block';
        }

        function closeReceiptModal() {
            document.getElementById('receipt-modal').style.display = 'none';
        }

        async function triggerDeleteReceipt() {
            if (confirm('Delete this receipt?')) {
                await fetch('/api/receipts/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: selectedReceiptName })
                });
                closeReceiptModal();
                fetchReceipts();
            }
        }

        function showCreateModal() {
            document.getElementById('dialog-title').innerText = 'Create Report';
            document.getElementById('submit-report-btn').innerText = 'Create Report';
            document.getElementById('edit-index').value = '';
            document.getElementById('reportname').value = '';
            document.getElementById('purpose').value = '';
            document.getElementById('comment').value = '';
            document.getElementById('report-dialog').style.display = 'block';
        }

        function showEditModal(idx, name, purpose, comment) {
            document.getElementById('dialog-title').innerText = 'Edit Report';
            document.getElementById('submit-report-btn').innerText = 'Save';
            document.getElementById('edit-index').value = idx;
            document.getElementById('reportname').value = name;
            document.getElementById('purpose').value = purpose;
            document.getElementById('comment').value = comment;
            document.getElementById('report-dialog').style.display = 'block';
        }

        function closeDialog() {
            document.getElementById('report-dialog').style.display = 'none';
        }

        async function saveReport(e) {
            e.preventDefault();
            const idx = document.getElementById('edit-index').value;
            const report = {
                name: document.getElementById('reportname').value,
                purpose: document.getElementById('purpose').value,
                comment: document.getElementById('comment').value
            };

            let url = '/api/reports';
            let payload = report;
            
            if (idx !== '') {
                url = '/api/reports/update';
                payload = { index: parseInt(idx), ...report };
            }

            await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            closeDialog();
            fetchReports();
        }

        async function deleteReport(name) {
            if (confirm('Are you sure you want to delete this report?')) {
                await fetch('/api/reports/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name })
                });
                fetchReports();
            }
        }

        // Run fetches
        fetchReports();
        fetchReceipts();
    </script>
</body>
</html>
"""

LOGIN_HTML = """<!DOCTYPE html>
<html>
<head><title>SAP Concur Login</title></head>
<body>
  <h1>Mock SAP Concur Login</h1>
  <form action="/login-submit" method="GET">
    <input type="text" id="username" placeholder="Username"><br><br>
    <input type="password" id="password" placeholder="Password"><br><br>
    <button type="submit" id="login-btn">Sign In</button>
  </form>
</body>
</html>
"""


class MockConcurRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress logging request lines to keep smoke test logs clean
        pass

    def do_GET(self):
        if self.path == "/" or "login" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(LOGIN_HTML.encode("utf-8"))
        elif self.path == "/nui/expense":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
        elif self.path == "/api/reports":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(REPORTS).encode("utf-8"))
        elif self.path == "/api/receipts":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(RECEIPTS).encode("utf-8"))
        elif "/login-submit" in self.path:
            self.send_response(302)
            self.send_header("Location", "/nui/expense")
            self.send_header("Set-Cookie", "concur_mock_session=active_state; Path=/; HttpOnly")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            data = {}

        if self.path == "/api/reports":
            name = data.get("name", "Unnamed")
            purpose = data.get("purpose", "")
            comment = data.get("comment", "")
            REPORTS.append({"name": name, "purpose": purpose, "comment": comment})
            
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))

        elif self.path == "/api/reports/update":
            idx = data.get("index")
            if idx is not None and 0 <= idx < len(REPORTS):
                REPORTS[idx]["name"] = data.get("name", REPORTS[idx]["name"])
                REPORTS[idx]["purpose"] = data.get("purpose", REPORTS[idx]["purpose"])
                REPORTS[idx]["comment"] = data.get("comment", REPORTS[idx]["comment"])
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))

        elif self.path == "/api/reports/delete":
            name = data.get("name")
            REPORTS[:] = [r for r in REPORTS if r["name"] != name]
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))

        elif self.path == "/api/receipts/delete":
            name = data.get("name")
            RECEIPTS[:] = [r for r in RECEIPTS if r["name"] != name]
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


class MockConcurServer:
    def __init__(self, host="127.0.0.1", port=8090):
        self.host = host
        self.port = port
        self.httpd = None
        self.thread = None

    def start(self):
        # Reset states
        REPORTS.clear()
        RECEIPTS[:] = [
            {"name": "lunch_receipt.png"},
            {"name": "taxi_receipt.png"},
            {"name": "hotel_receipt.jpg"}
        ]
        
        self.httpd = HTTPServer((self.host, self.port), MockConcurRequestHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        print(f"Mock SAP Concur server running at http://{self.host}:{self.port}")

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            print("Mock SAP Concur server stopped.")
