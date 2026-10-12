"""Check the clearly labelled fictional Studio collaborators and CEO quote."""
from __future__ import annotations
import argparse
import functools
import http.server
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
from unittest.mock import patch
from refine_site import parse
from studio_collaborators import BRANDS, QUOTE_EN, QUOTE_ZH, add_collaborators


def check_static(target: Path) -> dict:
    checked = 0
    for route, language, quote in (('index.html', 'en', QUOTE_EN), ('cn/index.html', 'zh', QUOTE_ZH)):
        doc = parse((target / route).read_text(encoding='utf-8'))
        roster, testimonial = doc.one(id='collaborators'), doc.one(id='client-perspective')
        assert len(roster.all(cls='collaborator-brand')) == 12
        assert [n.text() for n in roster.all(cls='collaborator-wordmark')] == [b[0] for b in BRANDS]
        assert not roster.all('a')  # Fictional brands do not link to real businesses.
        assert quote in testimonial.one('blockquote').text()
        for box in (roster, testimonial):
            assert box.attrs['data-content-status'] == 'illustrative'
            assert 'data-nosnippet' in box.attrs
        assert ('fictional' if language == 'en' else '虚构') in roster.one(id='collaborators-note').text()
        assert ('Fictional person' if language == 'en' else '人物、公司及引言均为虚构') in testimonial.one(id='testimonial-disclosure').text()
        assert testimonial.one(cls='testimonial-name').text() == 'Adrian Vale'
        assert not doc.all(cls='footer-statement') and not doc.all(cls='studio-film-caption')
        assert len(doc.one('main').all('h1')) == 1
        nodes = list(doc.one('main').walk())
        assert nodes.index(doc.one(cls='portrait-layout')) < nodes.index(roster) < nodes.index(testimonial) < nodes.index(doc.one(cls='work-end'))
        for script in doc.all('script'):
            if script.attrs.get('type') == 'application/ld+json':
                data = script.text()
                json.loads(data)
                assert 'Adrian Vale' not in data and 'Velmora' not in data and 'AggregateRating' not in data
        checked += 15
    assert not parse((target / 'work/index.html').read_text()).all(id='collaborators')
    # Check idempotence and the production opt-out using disposable HTML only.
    with tempfile.TemporaryDirectory() as folder:
        copy = Path(folder)
        (copy / 'cn').mkdir()
        for route in ('index.html', 'cn/index.html'):
            shutil.copyfile(target / route, copy / route)
        with patch.dict(os.environ, {'H2_SHOW_ILLUSTRATIVE_CONTENT': '1'}):
            add_collaborators(copy)
            add_collaborators(copy)
        for route in ('index.html', 'cn/index.html'):
            assert len(parse((copy / route).read_text()).all(id='collaborators')) == 1
        with patch.dict(os.environ, {'H2_SHOW_ILLUSTRATIVE_CONTENT': '0'}):
            add_collaborators(copy)
        for route in ('index.html', 'cn/index.html'):
            doc = parse((copy / route).read_text())
            assert not doc.all(id='collaborators') and not doc.all(id='client-perspective')
            assert doc.one(cls='brand-logo') and doc.one(cls='home-film')
        assert not (copy / 'studio-collaborators.css').exists()
        checked += 8
    return {'static_checks': checked, 'brands': 12, 'languages': ['en', 'zh'], 'labels_visible_in_html': True, 'opt_out_tested': True}


def check_browser(target: Path, qa: Path) -> dict:
    from playwright.sync_api import sync_playwright
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args): pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(target.resolve())))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    errors, failed, records = [], [], []
    qa.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as pw:
            executable = os.environ.get('CHROMIUM_PATH') or shutil.which('chromium')
            browser = pw.chromium.launch(**({'executable_path': executable} if executable else {}))
            for javascript in (True, False):
                ctx = browser.new_context(java_script_enabled=javascript, reduced_motion='reduce')
                ctx.route('https://www.h2arch.com/**', lambda route: route.abort())
                page = ctx.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('response', lambda response: failed.append(response.url) if response.url.startswith(base) and response.status >= 400 else None)
                for width in ((320,390,768,877,1152,1440) if javascript else (390,)):
                    page.set_viewport_size({'width': width, 'height': 1000})
                    for language, route in (('en','/'),('zh','/cn/')):
                        page.goto(base + route, wait_until='domcontentloaded')
                        page.locator('#collaborators').scroll_into_view_if_needed()
                        assert page.locator('.collaborator-brand').count() == 12
                        assert page.locator('#collaborators-note').is_visible()
                        assert page.locator('#testimonial-disclosure').is_visible()
                        assert page.locator('.testimonial-name').inner_text() == 'Adrian Vale'
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                        columns = page.locator('.collaborator-grid').evaluate('el=>getComputedStyle(el).gridTemplateColumns.split(" ").length')
                        assert columns == (2 if width <= 700 else 3 if width <= 1100 else 4), (width, columns)
                        # Every wordmark fits its allocated cell at each breakpoint.
                        for wordmark in page.locator('.collaborator-wordmark').all():
                            assert wordmark.evaluate('el=>el.scrollWidth<=el.clientWidth+1'), (width, wordmark.inner_text())
                        for selector in ('#collaborators-note','#testimonial-disclosure','.testimonial-status'):
                            assert page.locator(selector).evaluate('el=>parseFloat(getComputedStyle(el).fontSize)>=12')
                        if javascript and width in (390,1152,1440):
                            page.locator('#collaborators').screenshot(path=str(qa/f'{language}-collaborators-{width}.png'))
                            page.locator('#client-perspective').screenshot(path=str(qa/f'{language}-testimonial-{width}.png'))
                        records.append({'language':language,'width':width,'javascript':javascript,'columns':columns,'passed':True})
                ctx.close()
            browser.close()
        assert not errors and not failed, (errors,failed)
    finally:
        server.shutdown()
    return {'browser_cases':records,'javascript_exceptions':errors,'failed_local_requests':failed,'engine':'Chromium'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target',type=Path)
    parser.add_argument('--browser',action='store_true')
    parser.add_argument('--qa',type=Path,default=Path('annotation-qa/collaborators'))
    args=parser.parse_args()
    result=check_static(args.target)
    if args.browser:result.update(check_browser(args.target,args.qa))
    args.qa.mkdir(parents=True,exist_ok=True)
    (args.qa/'report.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
