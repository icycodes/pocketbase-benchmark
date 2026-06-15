from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/subscription":
            qs = parse_qs(parsed.query)
            user_id = qs.get("userId", [""])[0]
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            if user_id == "active_user":
                self.wfile.write(json.dumps({"status": "active"}).encode())
            elif user_id == "inactive_user":
                self.wfile.write(json.dumps({"status": "inactive"}).encode())
            else:
                self.wfile.write(json.dumps({"status": "error"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8080), Handler)
    server.serve_forever()
