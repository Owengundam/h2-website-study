"""Read-only checks for the original film and the packaged player geometry."""
from __future__ import annotations
import collections, functools, http.server, json, re, subprocess, threading, urllib.request
from pathlib import Path
import imageio_ffmpeg
from playwright.sync_api import sync_playwright
from refine_site import FILM

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'video-fit-qa'
OUT.mkdir(exist_ok=True)
source = OUT / 'original-atmosphere.mp4'
request = urllib.request.Request(FILM, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(request, timeout=45) as response:
    source.write_bytes(response.read())
assert b'ftyp' in source.read_bytes()[:64], 'Expected original MP4'
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
# Limited-range YUV represents black above zero. FFmpeg's usual 24-level
# threshold distinguishes the encoded matte from the visible image.
probe = subprocess.run([ffmpeg, '-hide_banner', '-i', str(source), '-vf',
    'fps=2,cropdetect=limit=24:round=2:reset=1', '-an', '-f', 'null', '-'],
    capture_output=True, text=True, timeout=90)
assert probe.returncode == 0, probe.stderr[-2000:]
(OUT / 'source-crop-detection.txt').write_text(probe.stderr)
size = re.search(r'Video:.*?\b(\d{3,5})x(\d{3,5})\b', probe.stderr)
assert size, 'Missing decoded source dimensions'
w, h = map(int, size.groups())
crops = [tuple(map(int, match)) for match in re.findall(r'crop=(\d+):(\d+):(\d+):(\d+)', probe.stderr)]
assert crops, 'No active-picture bounds detected'
wide = [c for c in crops if c[0] >= w - 4]
assert wide, 'Cannot establish full-width active picture'
active, occurrences = collections.Counter(wide).most_common(1)[0]
assert (w, h) == (640, 640), (w, h)
assert active == (640, 360, 0, 140), active
assert occurrences > len(crops) * .9, 'Picture bounds must agree throughout the film'
report = {'source_url':FILM, 'source_size':[w,h], 'active_picture':active,
    'detected_crop_samples':len(crops), 'common_crops':collections.Counter(crops).most_common(8), 'pages':[]}
(OUT / 'video-fit-report.json').write_text(json.dumps(report, indent=2))
subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-ss', '4', '-i', str(source),
    '-frames:v', '1', '-y', str(OUT / 'original-square-frame.jpg')], check=True, timeout=30)

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
server = http.server.ThreadingHTTPServer(('127.0.0.1',8765),
    functools.partial(QuietHandler, directory=str(ROOT / '_site')))
threading.Thread(target=server.serve_forever, daemon=True).start()
BASE = 'http://127.0.0.1:8765/'
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for width in (320,390,768,1100,1440,1920):
        page = browser.new_page(viewport={'width':width,'height':1050})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('**/20230928-atmosphere*.mp4', lambda route: route.fulfill(
            status=200, content_type='video/mp4', path=str(source)))
        for path in ('','cn/'):
            page.goto(BASE+path, wait_until='domcontentloaded')
            def measure():
                return page.evaluate('''() => {
                  const box = el => { const r=el.getBoundingClientRect(); return {left:r.left,right:r.right,width:r.width,height:r.height}; };
                  const v=document.querySelector('.home-film');
                  return {video:box(document.querySelector('.home-cinema')),strategy:box(document.querySelector('.service-list')),
                    pictureFit:getComputedStyle(v).objectFit,picturePosition:getComputedStyle(v).objectPosition,
                    source:v.getAttribute('src'),scrollWidth:document.documentElement.scrollWidth};
                }''')
            data = measure()
            assert abs(data['video']['left']-data['strategy']['left']) < 1, data
            assert abs(data['video']['right']-data['strategy']['right']) < 1, data
            assert abs(data['video']['width']/data['video']['height']-16/9) < .005, data
            assert data['pictureFit']=='cover' and data['picturePosition']=='50% 50%', data
            assert data['scrollWidth'] <= width+1, data
            assert data['source']==FILM
            if width==1440 and not path:
                page.locator('.home-cinema').scroll_into_view_if_needed()
                page.wait_for_function("document.querySelector('.home-film').readyState>=2", timeout=45000)
                page.locator('.film-toggle').click()
                if not page.locator('.home-film').evaluate('(v)=>v.paused'):
                    page.locator('.film-toggle').click()
                page.locator('.home-film').evaluate('(v)=>{v.currentTime=4;}')
                page.wait_for_function("!document.querySelector('.home-film').seeking")
                loaded=measure()
                assert abs(loaded['video']['width']/loaded['video']['height']-16/9) < .005, loaded
                page.locator('.home-cinema').screenshot(path=str(OUT/'film-no-bars.jpg'),type='jpeg',quality=90)
                page.locator('#approach').screenshot(path=str(OUT/'our-work-desktop.jpg'),type='jpeg',quality=88)
                page.locator('.film-fullscreen').click()
                page.wait_for_function("document.fullscreenElement?.classList.contains('home-cinema')")
                assert page.locator('.home-film').evaluate('(v)=>Math.abs(v.clientWidth/v.clientHeight-16/9)<.01')
                page.evaluate('document.exitFullscreen()')
                page.wait_for_function('!document.fullscreenElement')
                page.locator('.film-toggle').click()
                page.wait_for_function("!document.querySelector('.home-film').paused")
            if width==390 and not path:
                page.locator('.home-cinema').scroll_into_view_if_needed()
                page.wait_for_function("document.querySelector('.home-film').readyState>=2",timeout=45000)
                page.screenshot(path=str(OUT/'our-work-mobile.jpg'),type='jpeg',quality=85)
            assert not errors, errors
            report['pages'].append({'width':width,'path':path,'measurements':data,'passed':True})
        page.close()
    ctx=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
    page=ctx.new_page()
    page.goto(BASE,wait_until='domcontentloaded')
    box=page.locator('.home-cinema').bounding_box()
    assert abs(box['width']/box['height']-16/9)<.005
    assert page.locator('.home-film').get_attribute('controls') is not None
    report.update(no_javascript_ratio=True,fullscreen_picture_ratio=True,pause_resume=True)
    browser.close()
server.shutdown()
(OUT/'video-fit-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'source_size':[w,h],'active_picture':active,'responsive_pages_passed':len(report['pages']),
    'strategy_edges_aligned':True,'picture_ratio':'16:9','no_picture_stretch':True,'fullscreen':True}))
