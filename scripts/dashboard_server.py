#!/usr/bin/env python3
"""THE INGESTION DASHBOARD, SERVED -- so its buttons can do something.

    python3 scripts/dashboard_server.py        # http://127.0.0.1:8795/  (bash scripts/status.sh starts it)

WHY A SERVER NOW. The dashboard was a file opened from disk on purpose -- nothing listening on
a port. TJ, 15 October 2026, wanted a button that starts a report generation, and a page opened
from disk cannot start anything. So this serves the same files, plus two actions:

    POST /api/generate   {"slug": ...}            -> scripts/generate_report.py <slug>
    POST /api/answer     {"slug": ..., "text": ...} -> scripts/generate_report.py <slug> --answer
    POST /api/review     {"slug": ..., "verdict": ..., "note": ...} -> a PERSON's verdict on the draft,
                         written into its generation.json. No agent; costs nothing. It is the half of
                         the auto-generation evidence the agent cannot supply about itself.

and reads a generation's own files under /gen/<slug>/ (DRAFT.md, build.py, payload.json).

WHO CAN PRESS IT. Bound to 127.0.0.1 only. And a web page on ANY other site can still send a
request to localhost, so every action needs the header `X-Dashboard-Token`, a random value made
when the server starts and handed out only in /token.js. A cross-site page cannot read that
file and cannot send a custom header without a CORS preflight this server never approves.
A button spends money -- capped per run in generate_report.py -- so it must be this person
pressing it, on this machine.
"""
import http.server
import json
import os
import re
import secrets
import subprocess
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS = os.path.join(ROOT, 'build', 'status')
GEN = os.path.join(ROOT, 'notes', 'report-generations')
PORT = 8795
TOKEN = secrets.token_hex(16)
SLUG = re.compile(r'^[a-z0-9][a-z0-9-]{0,80}$')
TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
         '.json': 'application/json; charset=utf-8', '.md': 'text/plain; charset=utf-8',
         '.py': 'text/plain; charset=utf-8', '.css': 'text/css'}


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        sys.stderr.write('%s %s\n' % (self.command, self.path))

    def send(self, code, body, ctype='application/json; charset=utf-8'):
        b = body if isinstance(body, bytes) else body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(b)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(b)

    def file(self, base, rel):
        p = os.path.realpath(os.path.join(base, rel))
        if not p.startswith(os.path.realpath(base) + os.sep) or not os.path.isfile(p):
            return self.send(404, '{"error":"not found"}')
        self.send(200, open(p, 'rb').read(), TYPES.get(os.path.splitext(p)[1], 'application/octet-stream'))

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == '/token.js':
            return self.send(200, 'window.DASH_TOKEN=%s;' % json.dumps(TOKEN), TYPES['.js'])
        if path.startswith('/gen/'):
            return self.file(GEN, path[len('/gen/'):])
        return self.file(STATUS, path.lstrip('/') or 'index.html')

    def do_POST(self):
        if self.headers.get('X-Dashboard-Token') != TOKEN:
            return self.send(403, '{"error":"no token: open the dashboard at http://127.0.0.1:%d/"}' % PORT)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
        except ValueError:
            return self.send(400, '{"error":"not json"}')
        slug = body.get('slug') or ''
        if not SLUG.match(slug):
            return self.send(400, '{"error":"bad slug"}')
        if self.path == '/api/review':
            verdict = body.get('verdict')
            if verdict not in ('yes', 'with-a-person', 'no'):
                return self.send(400, '{"error":"verdict is yes, with-a-person or no"}')
            p = os.path.join(GEN, slug, 'generation.json')
            if not os.path.exists(p):
                return self.send(404, '{"error":"no generation"}')
            g = json.load(open(p, encoding='utf-8'))
            import datetime as _dt
            g.setdefault('reviews', []).append(dict(
                at=_dt.datetime.now().astimezone().isoformat(timespec='seconds'),
                verdict=verdict, note=(body.get('note') or '').strip()[:2000]))
            with open(p + '.tmp', 'w', encoding='utf-8') as fh:
                json.dump(g, fh, indent=1, ensure_ascii=False)
                fh.write('\n')
            os.replace(p + '.tmp', p)
            return self.send(200, json.dumps({'reviewed': slug}))
        argv = [sys.executable, os.path.join(ROOT, 'scripts', 'generate_report.py'), slug]
        if self.path == '/api/answer':
            text = (body.get('text') or '').strip()
            if not text:
                return self.send(400, '{"error":"empty answer"}')
            argv += ['--answer', text[:8000]]
        elif self.path != '/api/generate':
            return self.send(404, '{"error":"no such action"}')
        # DETACHED: the generation outlives this request, and the dashboard follows it through
        # generation.json, which the runner rewrites as it goes.
        log = open(os.path.join(ROOT, 'build', 'report-generations', '%s.out' % slug), 'a')
        subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        return self.send(202, json.dumps({'started': slug}))


def main():
    os.makedirs(os.path.join(ROOT, 'build', 'report-generations'), exist_ok=True)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), H)
    print('dashboard at http://127.0.0.1:%d/' % PORT, flush=True)
    srv.serve_forever()


if __name__ == '__main__':
    main()
