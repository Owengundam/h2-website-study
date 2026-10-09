#!/usr/bin/env python3
"""Apply browser-annotation refinements after the Studio homepage is built.

Standard library only. Preserve existing branding, copy, media and links.
Icons are inline SVG paths, not characters resolved through a device font.
"""
from __future__ import annotations
import html
import json
import os
import re
from pathlib import Path
from refine_site import Node, parse

ROOT = Path(__file__).resolve().parents[1]
STYLESHEET = 'ui-polish.css'
PATHS = {
    '\u2197': 'M6 18 18 6M6 6h12v12',
    '\u2191': 'M12 19V5M5 12l7-7 7 7',
    '\u2193': 'M12 5v14M5 12l7 7 7-7',
    '\u2190': 'M19 12H5M12 5l-7 7 7 7',
    '\u2192': 'M5 12h14M12 5l7 7-7 7',
}
ARROWS = re.compile('([' + ''.join(PATHS) + '])(?:\ufe0e|\ufe0f)?')
SKIP = {'script', 'style', 'svg', 'code', 'pre', 'textarea'}


def icon(character: str, parent: Node) -> Node:
    svg = Node('svg', {
        'class': 'ui-arrow', 'viewBox': '0 0 24 24', 'width': '24', 'height': '24',
        'fill': 'none', 'stroke': 'currentColor', 'stroke-width': '1.5',
        'stroke-linecap': 'round', 'stroke-linejoin': 'round',
        'aria-hidden': 'true', 'focusable': 'false',
    }.items(), parent)
    svg.children.append(Node('path', {'d': PATHS[character]}.items(), svg))
    return svg


def replace_arrows(node: Node) -> int:
    if node.tag in SKIP:
        return 0
    total = 0
    children = []
    for child in node.children:
        if isinstance(child, Node):
            total += replace_arrows(child)
            children.append(child)
        elif node.tag in {'a', 'button', 'span'} and ARROWS.search(html.unescape(child)):
            decoded = html.unescape(child)
            start = 0
            for match in ARROWS.finditer(decoded):
                if match.start() > start:
                    children.append(html.escape(decoded[start:match.start()], quote=False))
                children.append(icon(match.group(1), node))
                total += 1
                start = match.end()
            if start < len(decoded):
                children.append(html.escape(decoded[start:], quote=False))
        else:
            children.append(child)
    node.children = children
    return total


def polish(target: Path) -> dict:
    target = Path(target).resolve()
    css = ROOT/'redesign'/STYLESHEET
    if not css.is_file():
        raise RuntimeError(f'Missing UI stylesheet: {css}')
    (target/STYLESHEET).write_bytes(css.read_bytes())
    stats = {'pages': 0, 'removed_film_captions': 0, 'removed_footer_statements': 0, 'svg_arrows': 0, 'centered_introductions': 0}
    for path in sorted(target.rglob('*.html')):
        doc = parse(path.read_text(encoding='utf-8'))
        if not doc.all('main'):
            continue
        body, head = doc.one('body'), doc.one('head')
        for intro in body.all(id='studio-introduction'):
            # Remove the label from HTML, not just from the visual layout.
            for node in list(intro.all(cls='eyebrow')):
                if node.parent is intro:
                    node.remove()
            heading = intro.one('h1')
            is_chinese = (doc.one('html').attrs.get('lang') or '').startswith('zh')
            separator = '' if is_chinese else ' '
            heading.set_text(separator.join(heading.text().split()))
            stats['centered_introductions'] += 1
        for node in list(doc.all(cls='studio-film-caption')):
            node.remove()
            stats['removed_film_captions'] += 1
        for footer in doc.all(cls='site-footer'):
            for node in list(footer.all(cls='footer-statement')):
                node.remove()
                stats['removed_footer_statements'] += 1
        stats['svg_arrows'] += replace_arrows(body)
        for link in list(head.all('link')):
            if (link.attrs.get('href') or '').split('?')[0].split('/')[-1] == STYLESHEET:
                link.remove()
        relative = os.path.relpath(target/STYLESHEET, path.parent).replace(os.sep, '/')
        head.children.append(Node('link', {'rel': 'stylesheet', 'href': relative}.items(), head))
        assert not doc.all(cls='studio-film-caption')
        assert not doc.all(cls='footer-statement')
        assert not ARROWS.search(body.text()), f'An interface arrow was not replaced: {path}'
        for svg in body.all(cls='ui-arrow'):
            assert svg.tag == 'svg' and svg.attrs.get('aria-hidden') == 'true'
        assert doc.one(cls='back-top').attrs.get('aria-label'), 'Back-to-top must remain named'
        path.write_text(str(doc), encoding='utf-8')
        stats['pages'] += 1
    print('Browser annotation fixes: ' + json.dumps(stats, sort_keys=True))
    return stats


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', type=Path)
    polish(parser.parse_args().target)
