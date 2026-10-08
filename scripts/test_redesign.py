#!/usr/bin/env python3
"""Static and browser regression tests for the isolated H2 redesign."""
from __future__ import annotations
import functools, http.server, json, os, threading
from pathlib import Path
from urllib.parse import unquote, urlparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'redesign'
QA=ROOT/'redesign-qa'; QA.mkdir(exist_ok=True)
checks=[]
def verify(condition,description):
    checks.append({'test':description,'passed':bool(condition)})
    if not condition: raise AssertionError(description)
files=sorted(SITE.rglob('index.html'))
verify(len(files)==40,'40 static pages, 13 projects in two languages')
for path in files:
    soup=BeautifulSoup(path.read_text(),'html.parser')
    label=str(path.relative_to(SITE))
    verify(len(soup.select('main h1'))==1,label+': one H1')
    verify(bool(soup.select_one('meta[name=description]').get('content')),label+': description')
    verify(soup.select_one('meta[name=robots]')['content'].startswith('noindex'),label+': preview excluded from indexing')
    verify(len(soup.select('link[hreflang]'))==2,label+': language alternates')
    for el in soup.select('[href],[src],[poster]'):
        for key in ('href','src','poster'):
            url=el.get(key)
            if not url:continue
            parsed=urlparse(url)
            if parsed.scheme or parsed.netloc:continue
            target=(path.parent/unquote(parsed.path)).resolve() if parsed.path else path
            if target.is_dir():target=target/'index.html'
            verify(target.is_file(),label+': '+url)
            if parsed.fragment and target.suffix=='.html':
                dest=soup if target==path else BeautifulSoup(target.read_text(),'html.parser')
                verify(dest.find(id=unquote(parsed.fragment)) is not None,label+': anchor '+url)
    for el in soup.select('script[type="application/ld+json"]'):json.loads(el.string)

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}/redesign/'
errors=[];bad_responses=[]
try:
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(viewport={'width':1440,'height':1000},device_scale_factor=1,reduced_motion='reduce')
        page=context.new_page()
        page.on('pageerror',lambda err:errors.append(str(err)))
        page.on('response',lambda r:bad_responses.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
        page.goto(base,wait_until='networkidle')
        verify(page.locator('.project-card:visible').count()==13,'All 13 portfolio cards visible')
        verify(len(page.locator('.project-grid').evaluate("e=>getComputedStyle(e).gridTemplateColumns").split())==5,'Desktop five-column edge-to-edge image wall')
        for category,count in [('city',3),('mixed',2),('retreats',8),('all',13)]:
            page.locator(f'[data-filter="{category}"]').click()
            verify(page.locator('.project-card:visible').count()==count,f'Working {category} filter: {count} cards')
            verify(page.locator('[data-project-count]').inner_text()==str(count).zfill(2),category+': correct count')
        page.locator('[data-view-button=index]').click()
        verify(page.locator('.project-grid').get_attribute('data-view')=='index','Index view switches')
        page.locator('[data-view-button=grid]').click()
        page.goto(base+'projects/nalati-indigo/',wait_until='networkidle')
        for name in ['challenge','solution','outcome','film','details']:
            verify(page.locator('#'+name).count()==1,'Nalati chapter: '+name)
        verify(page.locator('.frame-strip>a').count()==3,'Three curated film shots')
        page.locator('[data-lightbox]').first.click()
        verify(page.locator('dialog').evaluate('e=>e.open'),'Image viewer opens')
        first=page.locator('.lightbox-count').inner_text()
        page.keyboard.press('ArrowRight')
        verify(page.locator('.lightbox-count').inner_text()!=first,'Image viewer keyboard navigation')
        page.keyboard.press('Escape')
        verify(not page.locator('dialog').evaluate('e=>e.open'),'Image viewer closes with Escape')
        page.locator('video').evaluate('e=>{e.muted=true;e.load()}')
        page.wait_for_function('Number.isFinite(document.querySelector("video").duration)',timeout=20000)
        duration=page.locator('video').evaluate('e=>e.duration')
        verify(14<duration<17,'Playable 15-second local project video')
        routes=['','projects/nalati-indigo/','studio/','journal/','contact/','cn/projects/nalati-indigo/']
        for width in [320,390,768,1440]:
            page.set_viewport_size({'width':width,'height':900 if width>700 else 844})
            for route in routes:
                page.goto(base+route,wait_until='networkidle')
                verify(page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),f'{width}px {route or "home"}: no horizontal overflow')
                if width in [390,1440]:
                    page.evaluate("document.querySelectorAll('img[loading]').forEach(i=>i.loading='eager')")
                    page.wait_for_function("[...document.querySelectorAll('main img[src]')].every(i=>i.complete&&i.naturalWidth>0)",timeout=20000)
                    # Wait for decoded and painted imagery, including off-screen lazy images.
                    page.evaluate("async()=>{await Promise.all([...document.querySelectorAll('main img[src]')].map(i=>i.decode()))}")
                    for image in page.locator('main img[src]').all():
                        image.scroll_into_view_if_needed()
                        page.wait_for_timeout(60)
                    page.evaluate('scrollTo(0,0)')
                    page.wait_for_timeout(200)
                    page.screenshot(path=str(QA/f'{width}-{route.strip("/").replace("/","-") or "work"}.jpg'),full_page=True,type='jpeg',quality=80)
        page.set_viewport_size({'width':390,'height':844})
        page.goto(base,wait_until='networkidle')
        page.locator('.menu-toggle').click()
        verify(page.locator('.main-nav').is_visible(),'Mobile menu opens')
        page.locator('.main-nav a').filter(has_text='Studio').click()
        verify('/studio/' in page.url,'Mobile navigation reaches Studio')
        page.locator('.menu-toggle').click()
        page.locator('.language-switch a').click()
        verify(page.locator('html').get_attribute('lang')=='zh-CN','Chinese language navigation works')
        for path in files:
            page.goto(base+str(path.relative_to(SITE)),wait_until='domcontentloaded')
            verify(page.locator('main').is_visible(),f'{path.relative_to(SITE)}: browser route loads')
        nojs=browser.new_context(java_script_enabled=False,viewport={'width':1440,'height':1000})
        raw=nojs.new_page();raw.goto(base)
        verify(raw.locator('.project-card').count()==13,'Portfolio exists without JavaScript')
        raw.goto(base+'projects/nalati-indigo/')
        verify('Make a destination' in raw.locator('main').inner_text(),'Case study readable without JavaScript')
        verify(raw.locator('a[data-lightbox]').first.get_attribute('href').endswith('.jpg'),'No-JavaScript image links remain functional')
        verify(not errors,'No JavaScript exceptions')
        verify(not bad_responses,'No failed local network requests')
        browser.close()
finally:
    server.shutdown()
    report={'passed':sum(x['passed'] for x in checks),'total':len(checks),'errors':errors,'bad_responses':bad_responses,'checks':checks}
    (QA/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='checks'},ensure_ascii=False))
