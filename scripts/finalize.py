#!/usr/bin/env python3
"""Build a navigable capture index and inspect references in archived HTML."""
import html, json, re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site'
manifest=json.loads((ROOT/'capture-manifest.json').read_text())
pages=[]
page_paths=set()
for url,item in manifest.items():
    if item.get('ok') and item.get('kind')=='html' and item['path'] not in page_paths:
        page_paths.add(item['path'])
        p=ROOT/item['path']
        text=p.read_text()
        title=re.search(r'<title>(.*?)</title>',text,re.S)
        pages.append((html.unescape(title.group(1)) if title else url,url,'/'+str(p.relative_to(SITE))))

# Match encoded font stylesheet URLs and preserve query strings/fragments.
mapping={u:'/'+str((ROOT/r['path']).relative_to(SITE)) for u,r in manifest.items() if r.get('ok')}
def fix_attr(m):
    val=html.unescape(m.group(2)); parts=urlsplit(val)
    if val in mapping: dest=mapping[val]
    elif parts.netloc in ('www.h2arch.com','h2arch.com'):
        key='https://www.h2arch.com'+parts.path
        if key not in mapping: return m.group(0)
        dest=mapping[key]+(('?'+parts.query) if parts.query else '')
    else: return m.group(0)
    if parts.fragment: dest+='#'+parts.fragment
    return m.group(1)+html.escape(dest,quote=True)+m.group(3)

missing=set(); external_assets=set()
class Inspector(HTMLParser):
    def __init__(self,source): super().__init__(); self.source=source
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        for key in ('src','href','data-src','data-lazy-src','poster'):
            v=attrs.get(key,'')
            if v.startswith('/') and not v.startswith('//'):
                p=SITE/unquote(urlsplit(v).path).lstrip('/')
                if p.is_dir(): p=p/'index.html'
                if not p.exists(): missing.add((self.source,v))
            elif (tag in ('img','script','source','video') and key!='href' or tag=='link' and attrs.get('rel')=='stylesheet') and v.startswith(('http://','https://','//')):
                external_assets.add((self.source,v))

for title,url,path in pages:
    p=SITE/path.lstrip('/'); text=p.read_text()
    text=re.sub(r'((?:href|src|data-src|data-lazy-src)=[\"\'])(.*?)([\"\'])',fix_attr,text)
    p.write_text(text)
    Inspector(url).feed(text)

rows=''.join(f'<li><a href="{html.escape(path)}">{html.escape(title)}</a><small>{html.escape(url)}</small></li>' for title,url,path in sorted(pages))
landing='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>H2 Website Study</title><style>body{font:16px/1.5 system-ui;max-width:1000px;margin:60px auto;padding:0 24px;color:#222}h1{font-size:40px}a{color:#24534a}li{margin:16px 0}small{display:block;color:#777;font-size:12px;overflow-wrap:anywhere}.lead{padding:20px;background:#f0f3ef;border-radius:10px}</style><h1>H2 · Website Study</h1><p class="lead">Public frontend archive captured 8 October 2026. <a href="/www.h2arch.com/projects/index.html">Open English projects</a> · <a href="/www.h2arch.com/cn/index.html">Open Chinese homepage</a></p><p>The English homepage returned a redirect loop during capture. This index is an archive navigation aid, not a recreation of that missing page. Backend form submissions and WordPress services are not reproduced.</p><h2>Captured pages</h2><ul>'''+rows+'</ul></html>'
(SITE/'index.html').write_text(landing)
if not (SITE/'www.h2arch.com/index.html').exists():
    (SITE/'www.h2arch.com/index.html').write_text(landing)
successful=[r for r in manifest.values() if r.get('ok')]
failed=[(u,r) for u,r in manifest.items() if not r.get('ok')]
files=[p for p in SITE.rglob('*') if p.is_file()]
large=[(str(p.relative_to(ROOT)),p.stat().st_size) for p in files if p.stat().st_size>=100*1024*1024]
report={'pages':len(pages),'captured_resources':len(successful),'failed_urls':len(failed),'site_bytes':sum(p.stat().st_size for p in files),'missing_local_references':sorted(missing),'external_asset_references':sorted(external_assets),'files_over_100_mib':large}
(ROOT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
lines=['# Capture notes','',f'- Capture date: 2026-10-08',f'- HTML pages: {len(pages)}',f'- Successfully captured URLs: {len(successful)}',f'- Capture size: {report["site_bytes"]/1024/1024:.1f} MiB',f'- Failed source URLs: {len(failed)}',f'- Missing local HTML references: {len(missing)}',f'- External HTML asset references: {len(external_assets)}',f'- Files at or above 100 MiB: {len(large)}','','## Scope and limitations','','The capture follows public links and frontend assets in the English and Chinese site. This is not proof that every unlinked or dynamically loaded resource has been discovered. No WordPress database, PHP source, credentials, or private content was copied. Forms and server-backed interactions cannot work fully offline. Browser rendering has not been verified; inspect `validation.json` for unresolved dependencies.','','The root English homepage returned a redirect loop. A clearly labeled archive index is provided in its local place.','','## Unsuccessful URLs','']
lines += [f'- `{u}` — `{r.get("status","")}`; {r.get("error","").strip()}' for u,r in failed]
lines += ['','## Page inventory','']+[f'- {title} — {url}' for title,url,path in sorted(pages)]
(ROOT/'STUDY.md').write_text('\n'.join(lines)+'\n')
(ROOT/'.capture-complete').write_text('Links converted for local serving.\n')
print(json.dumps({k:v for k,v in report.items() if not isinstance(v,list)},indent=2))
