#!/usr/bin/env python3
"""Regression checks for H2's five browser annotations.
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


def browser_checks(target: Path, qa: Path) -> dict:
    from playwright.sync_api import sync_playwright
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args): pass
    handler = functools.partial(QuietHandler, directory=str(target.resolve()))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}'
    qa.mkdir(parents=True, exist_ok=True)
    checks, errors, missing = 0, [], []
    try:
        with sync_playwright() as p:
            executable = os.environ.get('CHROMIUM_PATH') or shutil.which('chromium')
            options = {'executable_path': executable} if executable else {}
            browser = p.chromium.launch(**options)
            ctx = browser.new_context()
            # The original remote film is not part of this offline UI regression.
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
                        card = page.locator('.project-card').nth(2)
                        img = card.locator('.card-image img')
                        img.evaluate('(el)=>el.decode()')
                        card.scroll_into_view_if_needed()
                        page.wait_for_timeout(100)
                        image_box = img.bounding_box()
                        card.hover()
                        for delay in [0, 50, 150, 350, 700]:
                            page.wait_for_timeout(delay)
                            state = img.evaluate('''el=>{const r=el.getBoundingClientRect();const p=el.parentElement.getBoundingClientRect();const s=getComputedStyle(el);return {transform:s.transform,transition:s.transitionDuration,covered:r.left<=p.left+.01&&r.right>=p.right-.01&&r.top<=p.top+.01&&r.bottom>=p.bottom-.01};}''')
                            assert state['transform'] == 'none' and state['transition'] == '0s' and state['covered'], (width, delay, state)
                            assert img.bounding_box() == image_box
                            checks += 2
                        assert float(card.locator('.card-caption').evaluate('el=>getComputedStyle(el).opacity')) > .95
                        hyatt = page.locator('a[href*="projects/hyatt-shijiazhuang/"]')
                        hyatt.hover()
                        assert hyatt.locator('img').evaluate('el=>getComputedStyle(el).transform') == 'matrix(1.3, 0, 0, 1.3, 0, 0)'
                        page.locator('[data-filter="city"]').click()
                        assert page.locator('.project-card:visible').count() == 3
                        page.locator('[data-filter="all"]').click()
                        assert page.locator('.project-card:visible').count() == 13
                        page.locator('[data-view-button="index"]').click()
                        assert page.locator('.project-grid').get_attribute('data-view') == 'index'
                        page.locator('[data-view-button="grid"]').click()
                        link = page.locator('.portfolio-note .arrow-link')
                        assert link.locator('svg').evaluate('el=>el.viewBox.baseVal.width') == 24
                        page.evaluate('scrollTo(0,document.body.scrollHeight)')
                        page.wait_for_timeout(700)
                        page.locator('.back-top').click()
                        page.wait_for_function('scrollY<2')
                        checks += 8
                        if width in (390, 877, 1440):
                            page.screenshot(path=str(qa/f'work-{width}.png'))
                            page.evaluate('scrollTo(0,document.body.scrollHeight)')
                            page.wait_for_timeout(700)
                            page.screenshot(path=str(qa/f'footer-{width}.png'))
                if width == 877:
                    page.goto(url,wait_until='domcontentloaded')
                    page.locator('#approach').scroll_into_view_if_needed()
                    page.wait_for_timeout(700)
                    page.screenshot(path=str(qa/'studio-caption-removed.png'))
            page.goto(url+'/projects/nalati-indigo/',wait_until='domcontentloaded')
            page.locator('a[data-lightbox]').first.click()
            assert page.locator('.lightbox').evaluate('el=>el.open')
            previous = page.locator('.lightbox-count').inner_text()
            page.locator('[data-lightbox-next]').click()
            assert page.locator('.lightbox-count').inner_text() != previous
            page.keyboard.press('Escape')
            assert not page.locator('.lightbox').evaluate('el=>el.open')
            checks += 3
            nojs = browser.new_context(java_script_enabled=False, reduced_motion='reduce',viewport={'width':390,'height':844})
            nojs.route('https://www.h2arch.com/**', lambda route: route.abort())
            np = nojs.new_page(); np.goto(url+'/work/index.html')
            assert np.locator('.project-card').count() == 13
            assert np.locator('.portfolio-note .arrow-link svg').evaluate('el=>el.viewBox.baseVal.width') == 24
            checks += 2
            browser.close()
        assert not errors, errors
        assert not missing, missing
        return {'browser_assertions': checks, 'widths': [320,390,768,877,1440], 'javascript_exceptions': errors, 'failed_local_requests': missing, 'engine': 'Chromium (not a physical iPhone)'}
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
