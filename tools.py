#!/usr/bin/env python3
"""Generate a portable report, or serve it with a loopback-only test runner."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import subprocess
import shutil
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent


def build_report():
    evidence = json.loads((ROOT / "reports/results.json").read_text())
    html = (ROOT / "web/index.template.html").read_text()
    substitutions = {
        "__STYLES__": (ROOT / "web/styles.css").read_text(),
        "__SCRIPT__": (ROOT / "web/app.js").read_text(),
        "__EVIDENCE__": json.dumps(evidence).replace("<", "\\u003c"),
    }
    for key, value in substitutions.items():
        html = html.replace(key, value)
    (ROOT / "reports/index.html").write_text(html)
    return evidence


def publish_report():
    # Refuse to publish a passing snapshot if its tested source has since changed.
    evidence = json.loads((ROOT / "reports/results.json").read_text())
    digest = hashlib.sha256()
    for folder in ("src", "tests"):
        for path in sorted((ROOT / folder).glob("*")):
            if path.is_file() and path.suffix in (".cpp", ".hpp", ".py"):
                digest.update(str(path.relative_to(ROOT)).encode())
                digest.update(path.read_bytes())
    if not evidence.get("verification_passed") or evidence.get("source_sha256") != digest.hexdigest():
        raise SystemExit("Evidence is failing or stale. Run make demo before publishing.")
    build_report()
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    # Only these explicit public artifacts are published, never the local runner.
    for filename in ("index.html", "results.json"):
        shutil.copyfile(ROOT / "reports" / filename, output / filename)
    print("Published report assembled in dist/ from verified, source-matched evidence.")


class Handler(BaseHTTPRequestHandler):
    def send_body(self, status, body, content_type="application/json"):
        if not isinstance(body, bytes):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(body)

    def allowed_host(self):
        port = self.server.server_port
        return self.headers.get("Host") in ("127.0.0.1:" + str(port), "localhost:" + str(port))

    def do_GET(self):
        if not self.allowed_host():
            self.send_body(403, '{"error":"Local host required"}')
            return
        path = urlsplit(self.path).path
        if path in ("/", "/index.html"):
            self.send_body(200, (ROOT / "reports/index.html").read_bytes(), "text/html")
        elif path == "/results.json":
            self.send_body(200, (ROOT / "reports/results.json").read_bytes())
        elif path == "/api/status":
            self.send_body(200, '{"runner":"signal-bench"}')
        elif path == "/favicon.ico":
            self.send_body(204, b"", "image/x-icon")
        else:
            self.send_body(404, '{"error":"Not found"}')

    def do_POST(self):
        port = self.server.server_port
        origins = {"http://127.0.0.1:" + str(port), "http://localhost:" + str(port)}
        if not self.allowed_host() or self.headers.get("Origin") not in origins:
            self.send_body(403, '{"error":"Same-origin local request required"}')
            return
        if self.path != "/api/run":
            self.send_body(404, '{"error":"Not found"}')
            return
        if self.headers.get("Content-Type") != "application/json" or self.headers.get("Content-Length") != "2":
            self.send_body(400, '{"error":"Expected an empty JSON object"}')
            return
        if self.rfile.read(2) != b"{}":
            self.send_body(400, '{"error":"Expected an empty JSON object"}')
            return
        try:
            build = subprocess.run(["make", "build"], cwd=ROOT, capture_output=True, text=True, timeout=30)
            if build.returncode:
                self.send_body(500, json.dumps({"error": "C++ build failed. See terminal output."}))
                print(build.stdout, build.stderr, flush=True)
                return
            run = subprocess.run([sys.executable, "tests/run_tests.py"], cwd=ROOT,
                                 capture_output=True, text=True, timeout=30)
            if run.returncode not in (0, 1):
                self.send_body(500, json.dumps({"error": "Test runner could not start. See terminal output."}))
                print(run.stdout, run.stderr, flush=True)
                return
            evidence = build_report()
            self.send_body(200, json.dumps(evidence))
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            print(error, flush=True)
            self.send_body(500, '{"error":"Local runner failed. See terminal output."}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("report", "serve", "publish"))
    parser.add_argument("--port", type=int, default=8873)
    args = parser.parse_args()
    if args.action == "publish":
        publish_report()
        return
    build_report()
    if args.action == "report":
        print("Portable report: " + str(ROOT / "reports/index.html"))
        return
    with HTTPServer(("127.0.0.1", args.port), Handler) as server:
        print("Signal Bench: http://127.0.0.1:" + str(args.port), flush=True)
        print("Press Ctrl+C to stop. This server is for local development only.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
