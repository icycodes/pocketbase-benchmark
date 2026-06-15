import json
from http.server import BaseHTTPRequestHandler, HTTPServer

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        try:
            data = json.loads(body)
            email = data.get('email', '')
        except json.JSONDecodeError:
            email = ''
        
        if email == 'fail@example.com':
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Internal Server Error')
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')

    def log_message(self, format, *args):
        pass # Suppress logging

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 8081), WebhookHandler)
    server.serve_forever()
