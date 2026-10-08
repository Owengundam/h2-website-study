"""Read-only browser regression checks for the atmosphere film's minimal controls."""
from __future__ import annotations
import functools
import http.server
import json
import threading
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
from refine_site import FILM

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'video-fit-qa'
OUT.mkdir(exist_ok=True)
source = OUT / 'original-atmosphere.mp4'
with urllib.request.urlopen(urllib.request.Request(FILM, headers={'User-Agent':'Mozilla/5.0'}), timeout=45) as response:
    source.write_bytes(response.read())
assert b'ftyp' in source.read_bytes()[:64], 'Original film must return an MP4'

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_): pass

server = http.server.ThreadingHTTPServer(('127.0.0.1',0), functools.partial(QuietHandler,directory=str(ROOT/'_site')))
threading.Thread(target=server.serve_forever, daemon=True).start()
BASE = f'http://127.0.0.1:{server.server_port}/'
report = {'pages':[], 'javascript_errors':[]}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    def prepare(context):
        context.route('**/20230928-atmosphere*', lambda route: route.fulfill(status=200,content_type='video/mp4',path=str(source)))
        page = context.new_page()
        page.on('pageerror',lambda error:report['javascript_errors'].append(str(error)))
        return page
    def wait_opacity(page, shown):
        page.wait_for_function("expected => Math.abs(Number(getComputedStyle(document.querySelector('.film-controls')).opacity) - expected) < .01",arg=1 if shown else 0)
    def assert_clean(page):
        data = page.evaluate('''() => {
          const v=document.querySelector('.home-film'), panel=document.querySelector('.film-controls');
          const box=x=>{const r=x.getBoundingClientRect();return {left:r.left,right:r.right,width:r.width,height:r.height}};
          return {native:v.controls,source:v.getAttribute('src'),frame:box(v.closest('.home-cinema')),strategy:box(document.querySelector('.service-list')),
            styles:[panel,...panel.querySelectorAll('button'),v,v.closest('.home-cinema')].map(x=>{const c=getComputedStyle(x);return {border:c.borderTopWidth,shadow:c.boxShadow,background:c.backgroundColor}}),
            icons:[...panel.querySelectorAll('button')].map(x=>({text:x.innerText.trim(),label:x.getAttribute('aria-label'),icon:x.dataset.icon,svg:x.querySelectorAll('svg').length,color:getComputedStyle(x).color,width:x.clientWidth,height:x.clientHeight})),
            overflow:document.documentElement.scrollWidth>innerWidth+1};
        }''')
        assert data['source']==FILM and not data['native'] and not data['overflow'],data
        for s in data['styles']:
            assert s['border']=='0px' and s['shadow']=='none',data
        for s in data['styles'][:3]:
            assert s['background'] in ('rgba(0, 0, 0, 0)','transparent'),data
        assert len(data['icons'])==2,data
        for i in data['icons']:
            assert i['text']=='' and i['label'] and i['svg']==1 and i['color']=='rgb(255, 255, 255)',data
            assert i['width']>=44 and i['height']>=44,data
        assert abs(data['frame']['left']-data['strategy']['left'])<1,data
        assert abs(data['frame']['right']-data['strategy']['right'])<1,data
        assert abs(data['frame']['width']/data['frame']['height']-16/9)<.005,data
        return data

    for width in (320,390,700,768,1100,1440):
        context = browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        page = prepare(context)
        for route in ('','cn/'):
            page.goto(BASE+route,wait_until='domcontentloaded')
            page.locator('.home-cinema').scroll_into_view_if_needed()
            page.wait_for_function("document.querySelector('.home-film').readyState>=2",timeout=45000)
            page.mouse.move(1,1)
            wait_opacity(page,False)
            data = assert_clean(page)
            page.locator('.home-cinema').hover(position={'x':30,'y':30})
            wait_opacity(page,True)
            page.locator('.film-toggle').click()
            page.wait_for_function("!document.querySelector('.home-film').paused")
            assert page.locator('.film-toggle').get_attribute('data-icon')=='pause'
            page.locator('.film-toggle').click()
            assert page.locator('.home-film').evaluate('(v)=>v.paused')
            assert page.locator('.film-toggle').get_attribute('data-icon')=='play'
            assert not page.locator('.home-film').evaluate('(v)=>v.controls')
            page.mouse.move(1,1)
            wait_opacity(page,False)
            if width==1440 and not route:
                page.locator('.home-film').evaluate('(v)=>{v.currentTime=4;}')
                page.wait_for_function("!document.querySelector('.home-film').seeking")
                page.locator('.home-cinema').screenshot(path=str(OUT/'video-controls-hidden.jpg'),type='jpeg',quality=90)
                page.locator('.home-cinema').hover(position={'x':30,'y':30})
                page.locator('.film-toggle').click()
                page.wait_for_function("document.querySelector('.film-toggle').dataset.icon==='pause'")
                page.locator('.home-cinema').screenshot(path=str(OUT/'video-white-hover-icons.jpg'),type='jpeg',quality=90)
                page.locator('.film-fullscreen').click()
                page.wait_for_function("document.fullscreenElement?.classList.contains('home-cinema')")
                assert page.locator('.film-fullscreen').get_attribute('data-icon')=='collapse'
                assert not page.locator('.home-film').evaluate('(v)=>v.controls')
                page.locator('.home-cinema').hover(position={'x':30,'y':30})
                page.locator('.film-fullscreen').click()
                page.wait_for_function('!document.fullscreenElement')
                page.mouse.move(1,1)
                page.keyboard.press('Tab')
                page.locator('.film-toggle').focus()
                wait_opacity(page,True)
                page.keyboard.press('Space')
                page.wait_for_function("document.querySelector('.home-film').paused")
                assert_clean(page)
                report.update(fullscreen_icons=True,keyboard_controls=True,hover_hide_after_click=True)
            report['pages'].append({'width':width,'route':route,'passed':True,'geometry':data['frame']})
        context.close()

    # Autoplay still pauses when the film leaves the viewport.
    context=browser.new_context(viewport={'width':1440,'height':1000})
    page=prepare(context);page.goto(BASE,wait_until='domcontentloaded')
    page.locator('.home-cinema').scroll_into_view_if_needed()
    page.wait_for_function("document.querySelector('.home-film').currentTime>0 && !document.querySelector('.home-film').paused",timeout=45000)
    page.evaluate('scrollTo(0,0)')
    page.wait_for_function("document.querySelector('.home-film').paused")
    report['viewport_playback']=True
    context.close()

    # Touch devices reveal the same two icons on tap rather than relying on hover.
    context=browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True,reduced_motion='reduce')
    page=prepare(context);page.goto(BASE,wait_until='domcontentloaded')
    page.locator('.home-cinema').scroll_into_view_if_needed()
    page.wait_for_function("document.querySelector('.home-film').readyState>=2",timeout=45000)
    wait_opacity(page,False)
    page.locator('.home-cinema').tap(position={'x':30,'y':30})
    wait_opacity(page,True)
    page.locator('.film-toggle').tap()
    page.wait_for_function("!document.querySelector('.home-film').paused")
    wait_opacity(page,False)
    assert_clean(page)
    report['touch_tap_reveal_and_hide']=True
    context.close()

    context=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
    page=prepare(context);page.goto(BASE,wait_until='domcontentloaded')
    assert page.locator('.home-film').get_attribute('controls') is not None
    report['no_javascript_native_fallback']=True
    context.close();browser.close()
server.shutdown()
assert not report['javascript_errors'],report['javascript_errors']
(OUT/'film-controls-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'responsive_pages_passed':len(report['pages']),**{k:v for k,v in report.items() if k!='pages'}}))
