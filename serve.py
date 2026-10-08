#!/usr/bin/env python3
"""Serve this archive on localhost without third-party dependencies."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from pathlib import Path
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=8000)
args = parser.parse_args()
root = Path(__file__).resolve().parent / 'site'
handler = partial(SimpleHTTPRequestHandler, directory=str(root))
print(f'Open http://localhost:{args.port}/ (Ctrl+C to stop)', flush=True)
with ThreadingHTTPServer(('127.0.0.1', args.port), handler) as server:
    try: server.serve_forever()
    except KeyboardInterrupt: pass
