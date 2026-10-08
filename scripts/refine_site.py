#!/usr/bin/env python3
"""Apply public-facing brand, film and copy refinements to a packaged H2 site.
Only the Python standard library is required. No network requests are made.
Original logo files are copied byte-for-byte; the film streams from H2's original URL.
"""
from __future__ import annotations
import hashlib
import html
import json
import os
import shutil
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILM = 'https://www.h2arch.com/wp-content/uploads/2023/10/20230928-atmosphere%E4%BD%8E%E6%B8%85%E7%89%88.mp4'
VOID = set('area base br col embed hr img input link meta param source track wbr'.split())

class Node:
    def __init__(self, tag='', attrs=(), parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []
    def walk(self):
        for child in self.children:
            if isinstance(child, Node):
                yield child
                yield from child.walk()
    def all(self, tag=None, cls=None, id=None):
        return [n for n in self.walk() if (tag is None or n.tag == tag) and
                (cls is None or cls in (n.attrs.get('class') or '').split()) and
                (id is None or n.attrs.get('id') == id)]
    def one(self, tag=None, cls=None, id=None):
        found = self.all(tag, cls, id)
        if not found:
            raise ValueError(f'Missing node: {tag=} {cls=} {id=}')
        return found[0]
    def text(self):
        return html.unescape(''.join(x.text() if isinstance(x, Node) else x for x in self.children))
    def set_text(self, value):
        self.children = [html.escape(value)]
    def inner(self, markup):
        self.children = parse(markup).children
        for child in self.children:
            if isinstance(child, Node): child.parent = self
    def remove(self):
        if self.parent is not None and self in self.parent.children:
            self.parent.children.remove(self)
    def __str__(self):
        inside = ''.join(map(str, self.children))
        if not self.tag: return inside
        attrs = ''.join(' '+key if value is None else f' {key}="{html.escape(str(value), quote=True)}"' for key, value in self.attrs.items())
        opening = f'<{self.tag}{attrs}>'
        return opening if self.tag in VOID else opening + inside + f'</{self.tag}>'

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.root = Node()
        self.stack = [self.root]
    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID: self.stack.append(node)
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID: self.handle_endtag(tag)
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break
    def handle_data(self, data): self.stack[-1].children.append(data)
    def handle_entityref(self, name): self.handle_data('&'+name+';')
    def handle_charref(self, name): self.handle_data('&#'+name+';')
    def handle_decl(self, decl): self.handle_data('<!'+decl+'>')
    def handle_comment(self, data): self.handle_data('<!--'+data+'-->')

def parse(markup):
    parser = Parser()
    parser.feed(markup)
    parser.close()
    return parser.root

def paragraphs(values):
    return ''.join('<p>'+html.escape(value)+'</p>' for value in values)

def replace_paragraphs(node, values):
    direct = [n for n in node.children if isinstance(n, Node) and n.tag == 'p' and 'eyebrow' not in (n.attrs.get('class') or '')]
    position = node.children.index(direct[0]) if direct else len(node.children)
    for p in direct: p.remove()
    added = parse(paragraphs(values)).children
    for p in added: p.parent = node
    node.children[position:position] = added

def refine(target: Path):
    target = Path(target).resolve()
    content = json.loads((ROOT/'redesign/editorial.json').read_text(encoding='utf-8'))
    brand = target/'assets/brand'
    brand.mkdir(parents=True, exist_ok=True)
    logos = {}
    for variant in ('black', 'white'):
        original = ROOT/f'site/www.h2arch.com/wp-content/uploads/2025/05/h2_logo_2025_{variant}.png'
        destination = brand/f'h2-logo-{variant}.png'
        shutil.copyfile(original, destination)
        assert original.read_bytes() == destination.read_bytes(), 'Logo bytes must stay unchanged'
        logos[variant] = hashlib.sha256(destination.read_bytes()).hexdigest()
    original_icon = ROOT/'site/www.h2arch.com/wp-content/uploads/2024/01/h2arch-favicon-150x150.png'
    shutil.copyfile(original_icon, brand/'favicon.png')
    count = 0
    for path in sorted(target.rglob('*.html')):
        relative = path.relative_to(target).as_posix()
        doc = parse(path.read_text(encoding='utf-8'))
        if not doc.all('main'): continue
        lang = 'zh' if relative.startswith('cn/') else 'en'
        tr = lambda en, zh: zh if lang == 'zh' else en
        copy = content[lang]
        route = relative.removeprefix('cn/')
        prefix = os.path.relpath(target, path.parent).replace(os.sep, '/')
        url = lambda p: (prefix+'/' if prefix != '.' else '')+p
        main, head, body = doc.one('main'), doc.one('head'), doc.one('body')
        for item in doc.all(cls='brand'):
            item.inner(f'<img class="brand-logo" src="{url("assets/brand/h2-logo-black.png")}" width="3402" height="503" alt="H2 Architecture 赫图建筑" decoding="async">')
        for item in doc.all('link'):
            if item.attrs.get('rel') == 'icon':
                item.attrs.update(href=url('assets/brand/favicon.png'), type='image/png')
        head.children.extend(parse(f'<link rel="stylesheet" href="{url("editorial.css")}"><script src="{url("editorial.js")}" defer></script>').children)
        for node in list(doc.all(cls='review-label')) + list(doc.all(cls='source-notes')) + list(doc.all(cls='editorial-note')):
            node.remove()
        for footer in doc.all(cls='footer-bottom'):
            for a in list(footer.all('a')):
                if a.attrs.get('href') == 'https://www.h2arch.com/': a.remove()
            footer.children.append('<span>© 2026 H2 Architecture</span>')
        for node in main.all('dt'):
            translations = {
                'Year in source archive':'Design year', 'Year in design archive':'Design year',
                'Hotel group in archive':'Hotel group', 'Project scope in H2 account':'Design',
                'Indigo accommodation':'Hotel Indigo accommodation',
                '档案标注年份':'设计年份', '设计档案年份':'设计年份', '原档案年份':'设计年份',
                '档案标注酒店集团':'酒店集团', '原档案酒店集团':'酒店集团', 'H2公开记录中的范围':'设计内容'
            }
            if node.text() in translations: node.set_text(translations[node.text()])
        for subtitle in main.all(cls='subtitle'):
            subtitle.inner(str(subtitle).split('>',1)[1].rsplit('</',1)[0].replace('H2 project archive ·','Design ·').replace('H2 项目档案 ·','设计 ·'))
        if route == 'index.html':
            body.attrs['class'] = 'home-page'
            main.one('h1').tag = 'h2'
            main.one(cls='work-main').attrs['id'] = 'selected-work'
            heading = copy['home_intro']
            home = f'''<section class="home-opening" aria-label="{tr('H2 original atmosphere film','赫图原版氛围影片')}"><div class="home-cinema"><video class="home-film" src="{FILM}" autoplay muted playsinline loop controls preload="metadata" aria-label="{tr('H2 Architecture atmosphere film','赫图建筑氛围影片')}"></video><div class="film-controls" hidden><button type="button" class="film-toggle" aria-label="{tr('Play or pause film','播放或暂停影片')}">{tr('Play film','播放影片')}</button><button type="button" class="film-fullscreen">{tr('Fullscreen','全屏')}</button></div><p class="film-message" role="status" hidden></p></div><div class="home-film-caption"><span>{tr('H2 Architecture / Hotels, resorts & destinations','赫图建筑 / 酒店 · 度假 · 目的地')}</span><a href="#selected-work">{tr('Selected work ↓','精选作品 ↓')}</a></div></section><section class="home-introduction container"><p class="eyebrow">{tr('The practice / Shanghai','事务所 / 上海')}</p><div><h1>{html.escape(heading)}</h1>{paragraphs(copy['home_paragraphs'])}<a class="arrow-link" href="studio/index.html"><span>{tr('About the studio','关于赫图')}</span><span aria-hidden="true">↗</span></a></div></section>'''
            additions = parse(home).children
            for node in additions:
                if isinstance(node, Node): node.parent = main
            main.children = additions + main.children
            doc.one('title').set_text(copy['home_title']+' — H2 Architecture')
            for nav in doc.all(cls='main-nav'):
                for a in nav.all('a'): a.attrs.pop('aria-current', None)
            for meta in head.all('meta'):
                if meta.attrs.get('name') == 'description' or meta.attrs.get('property') == 'og:description': meta.attrs['content'] = copy['home_paragraphs'][0]
                if meta.attrs.get('property') == 'og:title': meta.attrs['content'] = copy['home_title']
                if meta.attrs.get('property') == 'og:image': meta.attrs['content'] = 'https://www.h2arch.com/wp-content/uploads/2025/05/h2_logo_2025_black.png'
        if route == 'projects/nalati-indigo/index.html':
            summary = main.one(cls='project-summary')
            replace_paragraphs(summary, [copy['nalati_summary']])
            for section in ('challenge','solution','outcome'):
                box = main.one(id=section).one(cls='chapter-copy')
                box.one('h2').set_text(copy['nalati'][section]['title'])
                replace_paragraphs(box, copy['nalati'][section]['paragraphs'])
            notes = tr('Project imagery: H2 Architecture archive. Design-film stills: 2024 visualisations. Completed-project photography: published 2025.', '项目影像：赫图建筑项目资料。设计短片及截帧：2024年可视化。落成摄影：2025年发布。')
            main.one(id='details').one(cls='chapter-copy').children.append('<p class="project-credits">'+notes+'</p>')
        elif route.startswith('projects/'):
            slug = route.split('/')[1]
            if slug in copy.get('projects', {}):
                replace_paragraphs(main.one(cls='chapter-copy'), copy['projects'][slug])
        if route == 'studio/index.html':
            lead = main.one(cls='page-lead').one('div')
            replace_paragraphs(lead, [copy['studio_intro']])
            approach = main.one(id='approach').one(cls='chapter-copy')
            approach.one('h2').set_text(copy['studio_heading'])
            replace_paragraphs(approach, copy['studio_paragraphs'])
            founder = main.one(cls='portrait-layout').one('div')
            replace_paragraphs(founder, copy['founder_paragraphs'])
        if route in ('journal/reading-nalati/index.html','journal/nalati-opening/index.html'):
            article = copy['opening' if '/nalati-opening/' in route else 'reading']
            lead = main.one(cls='page-lead')
            lead.one(cls='eyebrow').set_text(tr('Project journal','项目手记'))
            replace_paragraphs(lead.one('div'), [article['lead']])
            article_body = main.one(cls='article-body')
            link = str(article_body.one(cls='arrow-link'))
            markup = paragraphs([article['intro']])
            for title, *parts in article['sections']:
                markup += '<h2>'+html.escape(title)+'</h2>'+paragraphs(parts)
            article_body.inner(markup + link)
            if '/reading-nalati/' in route:
                main.one(cls='hero-figure').one(cls='figure-caption').inner('<span>'+tr('Nalati / Circular guest accommodation','那拉提 / 圆形客房组团')+'</span><span>'+tr('Design visualisation · 2024','设计可视化 · 2024')+'</span>')
        if route == 'contact/index.html':
            main.one(cls='contact-hint').set_text(copy['contact_hint'])
            for h in main.all('h2'):
                if h.text() in ('Original contact record','原始联系信息'): h.set_text(tr('Website','网站'))
        for schema in head.all('script'):
            if schema.attrs.get('type') != 'application/ld+json': continue
            data = json.loads(schema.text())
            if isinstance(data.get('isPartOf'), dict): data['isPartOf']['name'] = 'H2 Architecture'
            if route == 'index.html': data.update(name=copy['home_title'],description=copy['home_paragraphs'][0])
            schema.children = [json.dumps(data,ensure_ascii=False).replace('</','<\\/')]
        html_text = str(doc)
        html_text = html_text.replace('An editorial project reading','Project journal').replace('编辑项目解读','项目手记')
        path.write_text(html_text, encoding='utf-8')
        count += 1
    (target/'favicon.svg').unlink(missing_ok=True)
    (target/'editorial.json').unlink(missing_ok=True)
    (target/'brand-integrity.json').write_text(json.dumps({'logo_sha256':logos,'film_source':FILM,'film_delivery':'Original H2-hosted file, unchanged','refined_pages':count},indent=2))
    print(f'Refined {count} bilingual pages; preserved original H2 logo bytes and original film URL.')
    return count

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('target', type=Path)
    refine(parser.parse_args().target)
