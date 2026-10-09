#!/usr/bin/env python3
"""Publish H2 at the existing Pages root; original archive remains in git.
Only Python's standard library is required. Packaging performs no network I/O.
"""
from __future__ import annotations
import ast, html, json, os, shutil
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from refine_site import refine, parse, FILM
from studio_homepage import make_studio_homepage
from polish_site import polish

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'redesign'
TARGET = ROOT/'_site'
OWNER, NAME = os.environ.get('GITHUB_REPOSITORY','Owengundam/h2-website-study').split('/',1)
BASE = f'https://{OWNER.lower()}.github.io/{NAME}'
OLD_BASE = 'https://owengundam.github.io/h2-website-study/redesign'

def redirect(relative, destination):
    file = TARGET/relative
    file.parent.mkdir(parents=True,exist_ok=True)
    url = BASE+'/'+destination.lstrip('/')
    escaped = html.escape(url,quote=True)
    file.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,follow"><title>H2 Architecture</title>'+f'<link rel="canonical" href="{escaped}"><meta http-equiv="refresh" content="0;url={escaped}"><script>location.replace({json.dumps(url)}+location.search+location.hash);</script></head><body><a href="{escaped}">Continue to H2 Architecture</a></body></html>',encoding='utf-8')

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.urls=[]
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if not value:continue
            if key in {'href','src','poster'}:self.urls.append(value)
            elif key=='srcset':self.urls.extend(item.strip().split()[0] for item in value.split(',') if item.strip())

def main():
    required=['index.html','projects/nalati-indigo/index.html','cn/index.html','site.css','site.js','editorial.css','editorial.js','editorial.json','studio-home.css','studio-home.js','ui-polish.css']
    for relative in required:
        if not (SOURCE/relative).is_file():raise RuntimeError('Missing redesign file: '+relative)
    if TARGET.exists():shutil.rmtree(TARGET)
    shutil.copytree(SOURCE,TARGET)
    for file in TARGET.rglob('*'):
        if file.is_file() and file.suffix.lower() in {'.html','.xml','.json','.txt'}:
            file.write_text(file.read_text(encoding='utf-8').replace(OLD_BASE,BASE),encoding='utf-8')
    refine(TARGET)
    make_studio_homepage(TARGET)
    polish(TARGET)
    pages=sorted(TARGET.rglob('*.html'))
    assert len(pages)==40,'Unexpected public page count'
    banned=['Make a destination, not simply a hotel.','Bring the scale down to the landscape.',
            'require studio confirmation','require confirmation before official publication',
            'Edited for this design study','DESIGN STUDY · EDITORIAL CONTENT FOR REVIEW',
            '本研究版本编辑整理','设计研究版本 · 编辑内容待审核']
    for file in pages:
        doc=parse(file.read_text(encoding='utf-8'))
        assert len(doc.one('main').all('h1'))==1, str(file)+': expected one H1'
        assert doc.one(cls='brand-logo').attrs['src'].endswith('h2-logo-black.png')
        visible=doc.one('body').text()
        assert not any(phrase in visible for phrase in banned),str(file)+': review/advisory copy remains'
        for script in doc.all('script'):
            if script.attrs.get('type')=='application/ld+json':json.loads(script.text())
    for prefix in ('','cn/'):
        doc=parse((TARGET/prefix/'index.html').read_text(encoding='utf-8'))
        assert doc.one(cls='home-film').attrs['src']==FILM,'Original film source changed'
        assert doc.one(id='approach').one(cls='studio-work-film').one(cls='home-film')
        assert doc.one(cls='studio-landing').one('img').attrs['loading']=='eager'
        assert not doc.all(cls='home-opening'),'Old front page must not remain'
        assert not doc.all(cls='project-card'),'Portfolio belongs on the Work page'
        work=parse((TARGET/prefix/'work/index.html').read_text(encoding='utf-8'))
        assert len(work.all(cls='project-card'))==13,'All portfolio projects must remain on Work'
    for file in pages:
        relative=file.relative_to(TARGET)
        redirect(Path('redesign')/relative,relative.as_posix())
    aliases={'studio/index.html':'index.html','cn/studio/index.html':'cn/index.html',
             'www.h2arch.com/index.html':'index.html','www.h2arch.com/projects/index.html':'work/index.html',
             'www.h2arch.com/profile/index.html':'index.html','www.h2arch.com/contact/index.html':'contact/index.html',
             'www.h2arch.com/cn/home-cn/index.html':'cn/index.html','www.h2arch.com/cn/projects-cn/index.html':'cn/work/index.html'}
    tree=ast.parse((ROOT/'scripts/build_redesign.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CONFIG' for t in node.targets):
            for source_slug,slug,*_ in ast.literal_eval(node.value):aliases[f'www.h2arch.com/portfolio-item/{source_slug}/index.html']=f'projects/{slug}/index.html'
    for old,new in aliases.items():
        if not (TARGET/new).is_file():raise RuntimeError('Missing redirect destination: '+new)
        redirect(old,new)
    sitemap=TARGET/'sitemap.xml'
    if sitemap.exists():
        tree=ET.parse(sitemap); root=tree.getroot()
        for entry in list(root):
            if any('/studio/' in (child.text or '') for child in entry):root.remove(entry)
        tree.write(sitemap,encoding='utf-8',xml_declaration=True)
    (TARGET/'.nojekyll').touch()
    (TARGET/'deployment.json').write_text(json.dumps({'site':'H2 Architecture','base_url':BASE+'/',
        'commit':os.environ.get('GITHUB_SHA','local'),'pages':len(pages)-2,'original_brand':True,
        'homepage':'studio','homepage_film':FILM,'film_placement':'beside-our-work'},indent=2),encoding='utf-8')
    checked=0
    for file in TARGET.rglob('*.html'):
        parser=Links();parser.feed(file.read_text(encoding='utf-8'))
        page_url=BASE+'/'+file.relative_to(TARGET).as_posix()
        for value in parser.urls:
            url=urlsplit(urljoin(page_url,value))
            if url.scheme not in {'http','https'} or url.netloc!=urlsplit(BASE).netloc:continue
            prefix=urlsplit(BASE).path+'/'
            if not url.path.startswith(prefix):raise RuntimeError(f'Link escapes Pages project: {file}: {value}')
            target=TARGET/unquote(url.path[len(prefix):])
            if target.is_dir():target=target/'index.html'
            if not target.is_file():raise RuntimeError(f'Broken published link: {file}: {value}')
            checked+=1
    print(f'Prepared {len(pages)-2} public pages and Studio redirects; verified {checked} local links, original logos, source film and public copy.')

if __name__=='__main__':main()
