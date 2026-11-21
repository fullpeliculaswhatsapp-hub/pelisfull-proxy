import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urljoin
import urllib.request

class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/proxy':
            query_params = parse_qs(parsed_path.query)
            target_url = query_params.get('url', [None])[0]
            if not target_url:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing url")
                return
            try:
                req = urllib.request.Request(target_url, headers={'User-Agent': 'VLC/3.0.16', 'Referer': target_url})
                with urllib.request.urlopen(req) as response:
                    content_type = response.headers.get('Content-Type', '')
                    body = response.read()

                    self.send_response(response.status)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Headers', '*')

                    # Si es una lista de reproducción .m3u8 (HLS), reescribir los segmentos internos
                    if 'm3u8' in target_url or 'application/vnd.apple.mpegurl' in content_type or body.lstrip().startswith(b'#EXTM3U'):
                        self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
                        lines = body.decode('utf-8', errors='ignore').splitlines()
                        new_lines = []
                        for line in lines:
                            line_str = line.strip()
                            if line_str and not line_str.startswith('#'):
                                absolute_segment_url = urljoin(target_url, line_str)
                                proxied_segment = f"https://{self.headers.get('Host', 'pelisfull-proxy.onrender.com')}/proxy?url={absolute_segment_url}"
                                new_lines.append(proxied_segment)
                            else:
                                new_lines.append(line)
                        final_body = "\n".join(new_lines).encode('utf-8')
                        self.send_header('Content-Length', str(len(final_body)))
                        self.end_headers()
                        self.wfile.write(final_body)
                    else:
                        for header, value in response.headers.items():
                            if header.lower() not in ['content-encoding', 'transfer-encoding', 'connection']:
                                self.send_header(header, value)
                        self.end_headers()
                        self.wfile.write(body)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"PelisFull Smart HLS Proxy Server is running!")

def run():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), ProxyHandler)
    print(f"Proxy inteligente corriendo en el puerto {port}")
    server.serve_forever()

if __name__ == '__main__':
    run()
