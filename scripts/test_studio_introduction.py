#!/usr/bin/env python3
"""Read-only checks for the centered Studio introduction.

Usage: python scripts/test_studio_introduction.py _site
Starts its own local server. Requires Playwright; no external content is needed.
"""
from __future__ import annotations
import argparse
import functools
import http.server
import json
import os
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

MEASURE = """section => {
  const heading = section.querySelector('h1');
  const paragraph = section.querySelector('div > p');
  const rect = node => {
    const r = node.getBoundingClientRect();
    return {left:r.left, right:r.right, top:r.top, bottom:r.bottom,
            width:r.width, height:r.height, center:r.left+r.width/2};
  };
  const range = document.createRange();
  range.selectNodeContents(heading);
  const lines = [...range.getClientRects()].filter(r => r.width>0 && r.height>0);
  const headingStyle = getComputedStyle(heading);
  return {
    viewport:document.documentElement.clientWidth,
    scrollWidth:document.documentElement.scrollWidth,
    section:rect(section), heading:rect(heading), paragraph:rect(paragraph),
    lineTops:[...new Set(lines.map(r => Math.round(r.top)))],
    textLeft:Math.min(...lines.map(r=>r.left)),
    textRight:Math.max(...lines.map(r=>r.right)),
    headingAlign:headingStyle.textAlign,
    paragraphAlign:getComputedStyle(paragraph).textAlign,
    fontSize:parseFloat(headingStyle.fontSize),
    whiteSpace:headingStyle.whiteSpace,
    userSelect:headingStyle.userSelect,
    display:getComputedStyle(section).display,
    text:heading.textContent,
    labels:section.querySelectorAll(':scope > .eyebrow').length
  };
}"""


def check_intro(page, width: int, route: str) -> dict:
    section = page.locator('#studio-introduction')
    assert section.count() == 1
    assert page.locator('main h1').count() == 1
    result = section.evaluate(MEASURE)
    assert result['labels'] == 0, (width, route, 'The Studio label returned')
    assert result['display'] == 'block', result
    assert result['headingAlign'] == result['paragraphAlign'] == 'center', result
    center = result['viewport']/2
    for key in ('section', 'heading', 'paragraph'):
        assert abs(result[key]['center']-center) < 1, (width, route, key, result)
    assert result['paragraph']['top'] > result['heading']['bottom'], result
    assert result['scrollWidth'] <= result['viewport']+1, result
    assert result['textLeft'] >= result['section']['left']-1, result
    assert result['textRight'] <= result['section']['right']+1, result
    assert result['userSelect'] != 'none', result
    assert '\n' not in result['text'], result
    if width > 700:
        assert result['whiteSpace'] == 'nowrap', result
        assert len(result['lineTops']) == 1, result
    else:
        assert result['whiteSpace'] == 'normal' and result['fontSize'] >= 28, result
    expected = '以酒店建筑，回应场所。' if route.startswith('cn') else 'Architecture for hospitality. A sense of place.'
    assert result['text'] == expected, result
    assert page.locator('.footer-statement,.studio-film-caption').count() == 0
    return {'width':width, 'route':route, 'passed':True, 'measurements':result}


def run(target: Path, output: Path) -> None:
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    handler = functools.partial(QuietHandler, directory=str(target.resolve()))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/'
    output.mkdir(parents=True, exist_ok=True)
    results, errors, failures = [], [], []
    try:
        with sync_playwright() as p:
            options = {'executable_path':os.environ['CHROMIUM_PATH']} if os.environ.get('CHROMIUM_PATH') else {}
            browser = p.chromium.launch(**options)
            context = browser.new_context(reduced_motion='reduce')
            # The original remote film is unchanged and separately checked in deployment.
            context.route('https://www.h2arch.com/**', lambda route:route.abort())
            page = context.new_page()
            page.on('pageerror', lambda error:errors.append(str(error)))
            page.on('response', lambda response:failures.append(response.url) if response.url.startswith(base) and response.status>=400 else None)
            for width in (320,390,700,701,768,877,1024,1152,1440,1920):
                page.set_viewport_size({'width':width,'height':892})
                for route in ('index.html','cn/index.html'):
                    page.goto(base+route, wait_until='domcontentloaded')
                    page.evaluate('document.fonts.ready')
                    results.append(check_intro(page,width,route))
                    if width in (390,1152,1440):
                        page.locator('.studio-landing img').evaluate('el=>el.decode()')
                        page.evaluate("scrollTo(0,document.querySelector('#studio-introduction').getBoundingClientRect().top+scrollY-240)")
                        page.wait_for_timeout(180)
                        name = ('cn' if route.startswith('cn') else 'en') + f'-intro-{width}.png'
                        page.screenshot(path=str(output/name))
            nojs = browser.new_context(java_script_enabled=False, reduced_motion='reduce',viewport={'width':1152,'height':892})
            nojs.route('https://www.h2arch.com/**', lambda route:route.abort())
            nojs_page = nojs.new_page()
            for route in ('index.html','cn/index.html'):
                nojs_page.goto(base+route,wait_until='domcontentloaded')
                result = check_intro(nojs_page,1152,route)
                result['javascript_enabled'] = False
                results.append(result)
            browser.close()
        assert not errors, errors
        assert not failures, failures
        report = {'passed':True,'cases':results,'javascript_exceptions':errors,'failed_local_requests':failures,'engine':'Chromium'}
        (output/'studio-introduction-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'Centered introduction: {len(results)} EN/CN viewport and no-JavaScript checks passed.')
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', type=Path)
    parser.add_argument('--qa', type=Path, default=Path('annotation-qa/studio-introduction'))
    args = parser.parse_args()
    run(args.target,args.qa)
