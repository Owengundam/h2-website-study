#!/usr/bin/env python3
"""Archive publicly linked H2 pages and their frontend assets. Requires curl."""
import concurrent.futures as cf
import hashlib, html, json, os, re, subprocess, time
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, unquote
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
HOSTS = {'www.h2arch.com', 'h2arch.com'}
ASSET_HOSTS = HOSTS | {'fonts.googleapis.com', 'fonts.gstatic.com'}
seen = set(); records = {}; pending = []

def normalize(url, base):
    url = html.unescape(url).replace('\\/', '/').strip()
    p = urlsplit(urljoin(base, url))
    if p.scheme not in ('http', 'https') or p.hostname not in ASSET_HOSTS: return
    if any(x in p.path for x in ('wp-admin', 'wp-login', 'xmlrpc', '/feed/', '/wp-json/', 'wlwmanifest')): return
    if p.hostname in HOSTS:
        if p.query and not p.path.startswith(('/wp-content/', '/wp-includes/')): return
        p = p._replace(scheme='https', netloc='www.h2arch.com', query='')
    return urlunsplit(p._replace(fragment=''))

def localpath(url):
    p = urlsplit(url)
    path = unquote(p.path).lstrip('/')
    if not path or path.endswith('/'): path += 'index.html'
    elif not Path(path).suffix: path += '/index.html'
    if '..' in Path(path).parts: raise ValueError('Unsafe URL path')
    if p.query: path += '-' + hashlib.sha256(p.query.encode()).hexdigest()[:12] + '.css'
    return SITE / p.netloc / path

def add(url, base):
    u = normalize(url, base)
    if u and u not in seen:
        seen.add(u); pending.append(u)

class Links(HTMLParser):
    def __init__(self, base): super().__init__(); self.base=base
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if not value: continue
            if key in ('href','src','data-src','data-lazy-src','poster','data-bg','data-background-image'):
                add(value,self.base)
            elif key in ('srcset','data-srcset','data-lazy-srcset','imagesrcset'):
                for part in value.split(','): add(part.strip().split(' ')[0],self.base)

def discover(text, base, kind):
    if kind == 'html':
        try: Links(base).feed(text)
        except Exception: pass
    for val in re.findall(r'url\(\s*[\"\']?([^\)\"\']+)', text): add(val,base)
    for val in re.findall(r'https?://(?:www\.)?h2arch\.com/[^\s<>\"\'\\)]+',text.replace('\\/','/')):
        add(val,base)

def fetch(url):
    path=localpath(url); path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.stat().st_size:
        data=path.read_bytes(); status='cached'
    else:
        result=subprocess.run(['curl','-sS','-L','--max-redirs','4','--max-time','45','--retry','1','-A','H2-Website-Study/1.0','-o',str(path),'-w','%{http_code}|%{content_type}',url],capture_output=True,text=True)
        status=result.stdout
        if result.returncode or not status.startswith('200|'):
            path.unlink(missing_ok=True)
            return url,{'ok':False,'status':status,'error':result.stderr[-300:]},None,None
        data=path.read_bytes()
    suffix=path.suffix.lower()
    kind='html' if data.lstrip().lower().startswith((b'<!doctype html',b'<html')) else ('css' if suffix=='.css' else ('js' if suffix=='.js' else None))
    text=data.decode('utf-8',errors='replace') if kind else None
    return url,{'ok':True,'path':str(path.relative_to(ROOT)),'bytes':len(data),'kind':kind,'status':status},text,kind

def main():
    if (ROOT/'.capture-complete').exists():
        raise SystemExit('This archive has converted links. To recapture, copy scripts/mirror.py into a fresh project directory and run it there.')
    for u in ['https://www.h2arch.com/projects/','https://www.h2arch.com/','https://www.h2arch.com/cn/']: add(u,u)
    with cf.ThreadPoolExecutor(max_workers=16) as pool:
        active={}
        while pending or active:
            while pending and len(active)<16:
                u=pending.pop(0); active[pool.submit(fetch,u)]=u
            done,_=cf.wait(active,return_when=cf.FIRST_COMPLETED)
            for fut in done:
                active.pop(fut)
                try: u,r,t,k=fut.result()
                except Exception as exc: print('ERROR',str(exc),flush=True); continue
                records[u]=r
                if t: discover(t,u,k)
                if len(records)%25==0: print(f'{len(records)} downloaded/attempted; {len(pending)+len(active)} queued',flush=True)
                (ROOT/'capture-manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    # Rewrite successful URLs in pages, CSS, JS and serialized Elementor settings.
    mapping={u:'/'+str(localpath(u).relative_to(SITE)) for u,r in records.items() if r['ok']}
    for u,r in records.items():
        if not r['ok'] or not r['kind']: continue
        path=ROOT/r['path']; text=path.read_text(errors='replace')
        for source,dest in sorted(mapping.items(),key=lambda x:-len(x[0])):
            variants={source,source.replace('https:','http:'),source.replace('https:',''),html.escape(source,quote=True),source.replace('/','\\/')}
            for old in variants:
                replacement=dest.replace('/','\\/') if '\\/' in old else dest
                text=re.sub(re.escape(old)+r'''(?=[\s"'<>?#)]|$)''',lambda m: replacement,text)
        # CSS relative resources still resolve naturally within the mirrored tree.
        path.write_text(text)
    (ROOT/'.capture-complete').write_text('Links converted for local serving.\n')
    print(json.dumps({'successful':sum(r['ok'] for r in records.values()),'failed':sum(not r['ok'] for r in records.values()),'bytes':sum(r.get('bytes',0) for r in records.values())}),flush=True)

if __name__=='__main__': main()
