"""Make the existing Studio the landing page without duplicating its content.

Applied after editorial refinement. No network I/O or third-party dependencies.
H2's original logo and film files are not altered.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from refine_site import Node, parse, FILM


def adopt(parent: Node, node: Node, position: int | None = None) -> None:
    node.remove()
    node.parent = parent
    if position is None:
        parent.children.append(node)
    else:
        parent.children.insert(position, node)


def relative_url(target: Path, page: Path) -> str:
    return os.path.relpath(target, page.parent).replace(os.sep, '/')


def relocate(doc: Node, source: Path, destination: Path) -> None:
    """Preserve all relative assets/links when Studio moves one directory up."""
    def rebase(value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme or parts.netloc or not parts.path or parts.path.startswith('/'):
            return value
        path = (source.parent / parts.path).resolve()
        return urlunsplit(('', '', relative_url(path, destination), parts.query, parts.fragment))
    for node in doc.walk():
        for key in ('href', 'src', 'poster'):
            if node.attrs.get(key):
                node.attrs[key] = rebase(node.attrs[key])
        if node.attrs.get('srcset'):
            candidates = []
            for item in node.attrs['srcset'].split(','):
                fields = item.strip().split()
                if fields:
                    candidates.append(' '.join([rebase(fields[0]), *fields[1:]]))
            node.attrs['srcset'] = ', '.join(candidates)


def make_studio_homepage(target: Path) -> None:
    target = Path(target).resolve()
    for language in ('en', 'zh'):
        folder = target / ('cn' if language == 'zh' else '')
        home_path = folder / 'index.html'
        studio_path = folder / 'studio/index.html'
        old_home = parse(home_path.read_text(encoding='utf-8'))
        doc = parse(studio_path.read_text(encoding='utf-8'))
        tr = lambda en, zh: zh if language == 'zh' else en
        main, head, body = doc.one('main'), doc.one('head'), doc.one('body')
        body.attrs['class'] = 'studio-page studio-homepage'
        # Both official variants are copied unchanged by the existing refiner.
        brand = doc.one(cls='brand')
        original_logo = brand.one(cls='brand-logo')
        white_logo = parse(str(original_logo)).one('img')
        white_logo.attrs.update({'class': 'brand-logo-white', 'alt': '', 'aria-hidden': 'true'})
        white_logo.attrs['src'] = original_logo.attrs['src'].replace('h2-logo-black.png', 'h2-logo-white.png')
        adopt(brand, white_logo)

        # The Studio image becomes the first element, behind the overlay header.
        hero = main.one(cls='studio-image')
        hero.attrs.update({'class': 'studio-landing', 'id': 'studio-landing'})
        hero.attrs.pop('data-reveal', None)
        image = hero.one('img')
        image.attrs.update({'loading': 'eager', 'fetchpriority': 'high', 'sizes': '100vw'})
        wrapper = image.parent
        if wrapper.tag == 'a':
            wrapper.tag = 'div'
            wrapper.attrs = {'class': 'studio-landing-image'}
        captions = hero.all('figcaption')
        if captions:
            captions[0].attrs['class'] = 'studio-landing-caption'
            captions[0].inner('<span>' + tr('Nalati, Xinjiang', '新疆 · 那拉提') +
                              '</span><a href="#studio-introduction">' +
                              tr('Discover the studio ↓', '了解赫图 ↓') + '</a>')
        adopt(main, hero, 0)
        main.one(cls='page-lead').attrs['id'] = 'studio-introduction'

        # Reuse the exact former homepage film and its existing native controls.
        section = main.one(id='approach')
        section.attrs.update({'class': 'studio-work', 'aria-label': tr('Our work', '我们的工作')})
        section.attrs.pop('data-reveal', None)
        label = section.one(cls='chapter-label')
        copy = section.one(cls='chapter-copy')
        left = Node('div', {'class': 'studio-work-copy'})
        adopt(left, label)
        adopt(left, copy)
        adopt(section, left)
        right = Node('figure', {'class': 'studio-work-film'})
        cinema = parse(str(old_home.one(cls='home-cinema'))).one(cls='home-cinema')
        film = cinema.one(cls='home-film')
        assert film.attrs['src'] == FILM, 'Only the original H2 film may be moved'
        film.attrs['preload'] = 'none'
        film.attrs.pop('autoplay', None)
        adopt(right, cinema)
        caption = Node('figcaption', {'class': 'studio-film-caption'})
        caption.inner('<span>' + tr('H2 Architecture — Atmosphere', '赫图建筑 — 空间与氛围') + '</span>')
        adopt(right, caption)
        adopt(section, right)
        link = parse('<a class="arrow-link" href="../work/index.html"><span>' +
                     tr('Explore our work', '浏览全部作品') +
                     '</span><span aria-hidden="true">↗</span></a>').one('a')
        adopt(copy, link)

        old_canonical = next(n.attrs['href'] for n in head.all('link') if n.attrs.get('rel') == 'canonical')
        canonical = old_canonical.replace('/studio/', '/')
        for node in head.all('link'):
            if node.attrs.get('rel') in ('canonical', 'alternate'):
                node.attrs['href'] = node.attrs['href'].replace('/studio/', '/')
        for node in head.all('meta'):
            if node.attrs.get('property') == 'og:url':
                node.attrs['content'] = canonical
        for schema in head.all('script'):
            if schema.attrs.get('type') == 'application/ld+json':
                data = json.loads(schema.text().replace(old_canonical, canonical))
                schema.children = [json.dumps(data, ensure_ascii=False).replace('</', '<\\/')]
        for switch in doc.all(cls='language-switch'):
            for link in switch.all('a'):
                link.attrs['href'] = relative_url(target/('cn/index.html' if language == 'en' else 'index.html'), studio_path)
        head.inner(''.join(map(str, head.children)) +
                   '<link rel="stylesheet" href="../studio-home.css">' +
                   '<script src="../studio-home.js" defer></script>')
        if language == 'zh':
            head.all('link')[-1].attrs['href'] = '../../studio-home.css'
            head.all('script')[-1].attrs['src'] = '../../studio-home.js'
        relocate(doc, studio_path, home_path)
        home_path.write_text(str(doc), encoding='utf-8')

    # Studio now consistently means the home route in both language versions.
    for page in sorted(target.rglob('*.html')):
        doc = parse(page.read_text(encoding='utf-8'))
        if not doc.all('main'):
            continue
        for node in doc.all('a'):
            href = node.attrs.get('href') or ''
            parts = urlsplit(href)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            resolved = (page.parent / parts.path).resolve()
            for prefix in ('', 'cn/'):
                if resolved in ((target/prefix/'studio/index.html').resolve(), (target/prefix/'studio').resolve()):
                    node.attrs['href'] = relative_url(target/prefix/'index.html', page)
                    if parts.fragment:
                        node.attrs['href'] += '#' + parts.fragment
        page.write_text(str(doc), encoding='utf-8')
    print('Studio is the EN/CN homepage; original film is beside Our Work; portfolio remains on Work.')
