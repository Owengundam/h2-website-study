#!/usr/bin/env python3
"""Regression checks for H2's annotations and restored, edge-safe hover zoom.
Run: python scripts/test_annotation_polish.py _site [--browser]
Static checks use the standard library. Browser checks require Playwright.
"""
from __future__ import annotations
import argparse
import functools
import hashlib
import http.server
import json
import os
from pathlib import Path
import re
import shutil
import threading
from refine_site import parse


def check_site(target: Path) -> dict:
    target = target.resolve()
    total = 0
    pages = 0
    for file in target.rglob('*.html'):
        doc = parse(file.read_text(encoding='utf-8'))
        if not doc.all('main'):
            continue
        assert not doc.all(cls='studio-film-caption'), file
        assert not doc.all(cls='footer-statement'), file
        assert not re.search('[↗↑↓←→]', doc.one('body').text()), file
        assert len(doc.all(cls='back-top')) == 1, file
        back = doc.one(cls='back-top')
        assert back.attrs.get('aria-label') and back.attrs.get('href') == '#top', file
        assert len(back.all('svg')) == 1, file
        assert len(doc.all(cls='footer-nav')) == 1, file
        assert len(doc.one(cls='footer-nav').all('a')) == 4, file
        css = [n for n in doc.all('link') if n.attrs.get('rel') == 'stylesheet']
        assert len([n for n in css if (n.attrs.get('href') or '').endswith('ui-polish.css')]) == 1, file
        assert css[-1].attrs['href'].endswith('ui-polish.css'), file
        assert doc.one(cls='brand-logo').attrs['src'].endswith('h2-logo-black.png'), file
        for svg in doc.all(cls='ui-arrow'):
            assert svg.tag == 'svg' and svg.attrs.get('aria-hidden') == 'true', file
            assert svg.attrs.get('focusable') == 'false' and svg.attrs.get('viewbox') == '0 0 24 24', file
            assert len(svg.all('path')) == 1, file
            total += 3
        for script in doc.all('script'):
            if script.attrs.get('type') == 'application/ld+json':
                json.loads(script.text())
        pages += 1
        total += 12
    integrity = json.loads((target/'brand-integrity.json').read_text())
    for variant, expected in integrity['logo_sha256'].items():
        actual = hashlib.sha256((target/f'assets/brand/h2-logo-{variant}.png').read_bytes()).hexdigest()
        assert actual == expected, f'Original {variant} logo bytes changed'
        total += 1
    for route in ['index.html', 'cn/index.html']:
        doc = parse((target/route).read_text())
        assert doc.one(cls='home-film').attrs['src'] == integrity['film_source']
        total += 1
    assert pages >= 38
    return {'pages': pages, 'static_assertions': total}


IMAGE_STATE = '''el => {
  const r=el.getBoundingClientRect(), p=el.parentElement.getBoundingClientRect();
  const s=getComputedStyle(el), ps=getComputedStyle(el.parentElement);
  return {scale:new DOMMatrixReadOnly(s.transform).a,
    transition:parseFloat(s.transitionDuration), clip:ps.overflow,
    covered:r.left<=p.left-.5 && r.right>=p.right+.5 && r.top<=p.top-.5 && r.bottom>=p.bottom+.5,
    tile:{x:p.x,y:p.y,width:p.width,height:p.height}};
}'''


def exercise_zoom(page, card, qa: Path, label: str, base: float = 1.0, animated: bool = True, capture: bool = False) -> tuple[int, list]:
    """Sample entry AND exit: image zooms, tile stays fixed, all four edges covered."""
    img = card.locator('.card-image img')
    img.evaluate('(el)=>el.decode()')
    card.scroll_into_view_if_needed()
    page.mouse.move(0, 0)
    page.wait_for_timeout(900)
    initial = img.evaluate(IMAGE_STATE)
    assert abs(initial['scale']-base) < .0001, (label, initial)
    assert initial['covered'] and initial['clip'] == 'hidden', (label, initial)
    assert initial['transition'] > .8 if animated else initial['transition'] == 0, (label, initial)
    count, samples = 3, []
    tile = initial['tile']
    if capture:
        page.screenshot(path=str(qa/f'zoom-{label}-rest.png'))
    for direction in ['enter', 'leave']:
        if direction == 'enter':
            page.mouse.move(tile['x']+tile['width']/2, tile['y']+tile['height']/2)
        else:
            page.mouse.move(0, 0)
        elapsed = 0
        for checkpoint in [0, 16, 50, 160, 350, 650, 950]:
            page.wait_for_timeout(checkpoint-elapsed)
            elapsed = checkpoint
            state = img.evaluate(IMAGE_STATE)
            assert state['covered'] and state['clip'] == 'hidden', (label, direction, checkpoint, state)
            assert all(abs(state['tile'][k]-tile[k]) < .03 for k in tile), (label, 'tile moved', state)
            assert base-.0001 <= state['scale'] <= base*1.02+.0001, (label, state)
            count += 3
            samples.append({'direction':direction,'checkpoint_ms':checkpoint,'scale':state['scale'],'covered':state['covered']})
            if capture and checkpoint in [16,160,350,950]:
                page.screenshot(path=str(qa/f'zoom-{label}-{direction}-{checkpoint}.png'))
        expected = base*1.02 if animated and direction == 'enter' else base
        assert abs(state['scale']-expected) < .0001, (label, direction, expected, state)
        count += 1
    if animated:
        assert any(base+.00001 < s['scale'] < base*1.02-.00001 for s in samples), (label, 'Animation jumped instead of scaling', samples)
        count += 1
    return count, samples


def browser_checks(target: Path, qa: Path) -> dict:
    from playwright.sync_api import sync_playwright
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args): pass
    handler = functools.partial(QuietHandler, directory=str(target.resolve()))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}'
    qa.mkdir(parents=True, exist_ok=True)
    checks, errors, missing, zoom_samples = 0, [], [], {}
    try:
        with sync_playwright() as p:
            executable = os.environ.get('CHROMIUM_PATH') or shutil.which('chromium')
            options = {'executable_path': executable} if executable else {}
            browser = p.chromium.launch(**options)
            ctx = browser.new_context()
            ctx.route('https://www.h2arch.com/**', lambda route: route.abort())
            page = ctx.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('response', lambda response: missing.append(response.url) if response.url.startswith(url) and response.status >= 400 else None)
            for width in [320, 390, 768, 877, 1440]:
                page.set_viewport_size({'width': width, 'height': 892})
                for route in ['', '/work/index.html', '/cn/', '/cn/work/index.html', '/projects/nalati-indigo/']:
                    page.goto(url+route, wait_until='domcontentloaded')
                    page.locator('.brand-logo').evaluate('el=>el.decode()')
                    assert page.locator('.footer-statement,.studio-film-caption').count() == 0
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), (width, route, 'overflow')
                    result = page.locator('.back-top').evaluate('''el => {
                      const s=getComputedStyle(el); const r=el.getBoundingClientRect();
                      return {radius:s.borderRadius,w:r.width,h:r.height,svg:el.querySelector('svg').viewBox.baseVal.width};
                    }''')
                    assert result == {'radius': '50%', 'w': 44, 'h': 44, 'svg': 24}, result
                    assert page.locator('.brand-logo').evaluate('(el)=>el.naturalWidth>0')
                    checks += 4
                    if route == '/work/index.html':
                        assert page.locator('.project-card').count() == 13
                        count, samples = exercise_zoom(page, page.locator('.project-card').nth(2), qa, str(width), capture=width==877)
                        checks += count
                        zoom_samples[str(width)] = samples
                        card = page.locator('.project-card').nth(2)
                        card.hover(); page.wait_for_timeout(400)
                        assert float(card.locator('.card-caption').evaluate('el=>getComputedStyle(el).opacity')) > .95
                        hyatt = page.locator('a[href*="projects/hyatt-shijiazhuang/"]')
                        count, samples = exercise_zoom(page, hyatt, qa, f'hyatt-{width}', base=1.3)
                        checks += count
                        zoom_samples[f'hyatt-{width}'] = samples
                        page.locator('[data-filter="city"]').click()
                        assert page.locator('.project-card:visible').count() == 3
                        page.locator('[data-filter="retreats"]').click()
                        assert page.locator('.project-card:visible').count() == 8
                        if width == 877:
                            count, samples = exercise_zoom(page, page.locator('.project-card:visible').first, qa, 'retreats-877')
                            checks += count; zoom_samples['retreats-877'] = samples
                        page.locator('[data-filter="all"]').click()
                        assert page.locator('.project-card:visible').count() == 13
                        page.locator('[data-view-button="index"]').click()
                        assert page.locator('.project-grid').get_attribute('data-view') == 'index'
                        if width == 877:
                            count, samples = exercise_zoom(page, page.locator('.project-card').nth(2), qa, 'index-877')
                            checks += count; zoom_samples['index-877'] = samples
                        page.locator('[data-view-button="grid"]').click()
                        link = page.locator('.portfolio-note .arrow-link')
                        assert link.locator('svg').evaluate('el=>el.viewBox.baseVal.width') == 24
                        page.evaluate('scrollTo(0,document.body.scrollHeight)')
                        page.wait_for_timeout(700)
                        page.locator('.back-top').click()
                        page.wait_for_function('scrollY<2')
                        checks += 9
                        if width in (390, 877, 1440):
                            page.screenshot(path=str(qa/f'work-{width}.png'))
                            page.evaluate('scrollTo(0,document.body.scrollHeight)')
                            page.wait_for_timeout(700)
                            page.screenshot(path=str(qa/f'footer-{width}.png'))
            page.goto(url+'/projects/nalati-indigo/',wait_until='domcontentloaded')
            page.locator('a[data-lightbox]').first.click()
            assert page.locator('.lightbox').evaluate('el=>el.open')
            previous = page.locator('.lightbox-count').inner_text()
            page.locator('[data-lightbox-next]').click()
            assert page.locator('.lightbox-count').inner_text() != previous
            page.keyboard.press('Escape')
            assert not page.locator('.lightbox').evaluate('el=>el.open')
            checks += 3
            # Fractional raster boundaries at high device pixel ratios.
            for dpr in [2, 3]:
                high = browser.new_context(viewport={'width':877,'height':892},device_scale_factor=dpr)
                hp = high.new_page(); hp.goto(url+'/work/index.html',wait_until='domcontentloaded')
                count, samples = exercise_zoom(hp, hp.locator('.project-card').nth(2), qa, f'dpr-{dpr}')
                checks += count; zoom_samples[f'dpr-{dpr}'] = samples
                high.close()
            # Zoom must not become a sticky tap effect or ignore motion preferences.
            for name, options in [('touch',{'has_touch':True,'is_mobile':True,'device_scale_factor':3}),('reduced',{'reduced_motion':'reduce'})]:
                special = browser.new_context(viewport={'width':390,'height':844},**options)
                sp = special.new_page(); sp.goto(url+'/work/index.html',wait_until='domcontentloaded')
                count, samples = exercise_zoom(sp, sp.locator('.project-card').nth(2), qa, name, animated=False)
                checks += count; zoom_samples[name] = samples
                special.close()
            nojs = browser.new_context(java_script_enabled=False, reduced_motion='reduce',viewport={'width':390,'height':844})
            np = nojs.new_page(); np.goto(url+'/work/index.html')
            assert np.locator('.project-card').count() == 13
            assert np.locator('.portfolio-note .arrow-link svg').evaluate('el=>el.viewBox.baseVal.width') == 24
            checks += 2
            browser.close()
        assert not errors, errors
        assert not missing, missing
        return {'browser_assertions': checks, 'widths': [320,390,768,877,1440], 'device_pixel_ratios':[1,2,3], 'zoom_samples':zoom_samples, 'javascript_exceptions': errors, 'failed_local_requests': missing, 'engine': 'Chromium (not a physical iPhone)'}
    finally:
        server.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', type=Path)
    parser.add_argument('--browser', action='store_true')
    parser.add_argument('--qa', type=Path, default=Path('annotation-qa'))
    args = parser.parse_args()
    result = check_site(args.target)
    if args.browser: result.update(browser_checks(args.target,args.qa))
    args.qa.mkdir(parents=True,exist_ok=True)
    (args.qa/'report.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
