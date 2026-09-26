"""HTTP server and API routes for ClearLedger."""
import json
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from ledger import importing, reporting, storage


class ClearLedgerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress noisy standard request logging in production/tests
        pass

    @property
    def db(self):
        return storage.connect(self.server.db_path)

    def send_json(self, status_code, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        db = self.db
        try:
            if path == '/api/overview':
                data = reporting.get_overview(db)
                self.send_json(200, data)
                return

            if path == '/api/invoices':
                status = query.get('status', ['all'])[0]
                try:
                    data = reporting.get_invoices(db, status=status)
                    self.send_json(200, data)
                except ValueError as err:
                    self.send_json(400, {'error': str(err)})
                return

            if path == '/api/export':
                csv_data = reporting.get_export_csv(db).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/csv; charset=utf-8')
                self.send_header('Content-Disposition', 'attachment; filename="invoices_export.csv"')
                self.send_header('Content-Length', str(len(csv_data)))
                self.end_headers()
                self.wfile.write(csv_data)
                return

            # Serve static files from web directory
            self.serve_static(path)
        finally:
            db.close()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        db = self.db
        try:
            if path == '/api/import':
                kind = query.get('kind', [''])[0]
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length)

                try:
                    result = importing.import_csv(db, body, kind)
                    self.send_json(200, result)
                except ValueError as err:
                    self.send_json(400, {'error': str(err)})
                return

            self.send_json(404, {'error': 'Not found'})
        finally:
            db.close()

    def serve_static(self, path):
        if path in ('/', ''):
            path = '/index.html'

        # Strip leading slash
        clean_path = path.lstrip('/')
        web_dir = Path(self.server.web_dir).resolve()
        target_file = (web_dir / clean_path).resolve()

        if not str(target_file).startswith(str(web_dir)) or not target_file.is_file():
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'File Not Found')
            return

        mime_type, _ = mimetypes.guess_type(str(target_file))
        if not mime_type:
            mime_type = 'application/octet-stream'

        data = target_file.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mime_type)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def make_server(db_path, web_dir, port):
    """Create and return an HTTPServer instance."""
    server = HTTPServer(('0.0.0.0', port), ClearLedgerHandler)
    server.db_path = db_path
    server.web_dir = web_dir
    return server
