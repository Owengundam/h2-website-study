"""Add the requested illustrative collaborator roster and CEO testimonial.

All names, organisations and endorsement text in this module are fictional.
Visible labels travel with each section; nothing is added to structured data.
Set H2_SHOW_ILLUSTRATIVE_CONTENT=0 when publishing without concept content.
Standard library only; original H2 assets and project descriptions stay intact.
"""
from __future__ import annotations
import html
import os
from pathlib import Path
from refine_site import Node, parse

ROOT = Path(__file__).resolve().parents[1]
STYLESHEET = 'studio-collaborators.css'
BRANDS = (
    ('VELMORA', 'Hotels & Resorts', '酒店与度假村', 'serif-wide'),
    ('soraen', 'Retreats', '度假居所', 'soft-lower'),
    ('AURENNE', 'Hospitality', '酒店集团', 'sans-wide'),
    ('FORME & FIELD', 'Destinations', '旅行目的地', 'serif-italic'),
    ('LINROVE', 'Resort Collection', '精选度假酒店', 'serif-wide'),
    ('MEREVA', 'Hotels', '酒店', 'sans-light'),
    ('STILLHARBOUR', 'Private Retreats', '私享度假', 'sans-compact'),
    ('ORIVA', 'Living', '生活空间', 'serif-italic'),
    ('HAVEN & HILL', 'Development', '文旅开发', 'sans-compact'),
    ('FIELDVALE', 'Destinations', '目的地开发', 'serif-wide'),
    ('NORROW', 'Hospitality', '酒店集团', 'sans-wide'),
    ('ELVENA', 'Places & Experiences', '空间与体验', 'sans-light'),
)
QUOTE_EN = (
    'H2 understood that a hotel is more than a collection of rooms. '
    'Their approach connected the character of the place with the way guests '
    'arrive, gather and settle in, giving the project a clear identity from the outset.'
)
QUOTE_ZH = (
    '赫图理解，一间酒店并不只是客房的集合。他们将场所的独特气质，'
    '与宾客抵达、相聚和停留的体验联系起来，让项目从一开始就有了清晰的个性。'
)


def markup(language: str) -> str:
    """Render complete, labelled concept content without claiming real partners."""
    tr = lambda en, zh: zh if language == 'zh' else en
    brands = ''.join(
        '<li class="collaborator-brand"><span class="collaborator-wordmark '
        + style + '" lang="en">' + html.escape(name) + '</span>'
        + '<span class="collaborator-sector">' + html.escape(tr(en, zh)) + '</span></li>'
        for name, en, zh, style in BRANDS
    )
    return f'''
<section class="studio-collaborators" id="collaborators" aria-labelledby="collaborators-title" aria-describedby="collaborators-note" data-content-status="illustrative" data-nosnippet>
  <div class="collaborators-heading">
    <p class="eyebrow">{tr('Collaborators', '合作伙伴')}</p>
    <h2 id="collaborators-title">{tr('A shared approach to hospitality.', '共筑酒店与度假的多元体验。')}</h2>
    <p class="collaborators-disclosure" id="collaborators-note">{tr('Concept preview · All brands below are fictional and do not represent H2 partnerships.', '概念示意 · 以下品牌均为虚构，不代表赫图的实际合作关系。')}</p>
  </div>
  <ul class="collaborator-grid" aria-label="{tr('Illustrative collaborator brands', '虚构合作品牌示意')}" aria-describedby="collaborators-note">{brands}</ul>
</section>
<section class="studio-testimonial" id="client-perspective" aria-labelledby="testimonial-title" aria-describedby="testimonial-disclosure" data-content-status="illustrative" data-nosnippet>
  <div class="testimonial-heading">
    <h2 id="testimonial-title">{tr('A shared perspective', '合作视角')}</h2>
    <p class="testimonial-status">{tr('Illustrative testimonial', '虚构评价示意')}</p>
  </div>
  <figure class="testimonial-figure">
    <blockquote><p>{html.escape(tr(QUOTE_EN, QUOTE_ZH))}</p></blockquote>
    <figcaption>
      <span class="testimonial-name">{tr('Adrian Vale', 'Adrian Vale')}</span>
      <span class="testimonial-role">{tr('Chief Executive Officer · Velmora Hotels & Resorts', '首席执行官 · Velmora 酒店与度假村')}</span>
      <span class="testimonial-disclosure" id="testimonial-disclosure">{tr('Fictional person, company and quote · For layout demonstration only.', '人物、公司及引言均为虚构 · 仅用于版式展示。')}</span>
    </figcaption>
  </figure>
</section>'''


def add_collaborators(target: Path) -> dict:
    """Insert into the EN/CN Studio homepages, before the existing contact CTA."""
    target = Path(target).resolve()
    enabled = os.environ.get('H2_SHOW_ILLUSTRATIVE_CONTENT', '1') == '1'
    source = ROOT / 'redesign' / STYLESHEET
    if enabled:
        if not source.is_file():
            raise FileNotFoundError(source)
        (target / STYLESHEET).write_bytes(source.read_bytes())
    count = 0
    for language, relative in (('en', 'index.html'), ('zh', 'cn/index.html')):
        path = target / relative
        doc = parse(path.read_text(encoding='utf-8'))
        main, head = doc.one('main'), doc.one('head')
        for node in list(doc.all(id='collaborators')) + list(doc.all(id='client-perspective')):
            node.remove()
        for node in list(head.all('link')):
            if (node.attrs.get('href') or '').split('?')[0].split('/')[-1] == STYLESHEET:
                node.remove()
        if enabled:
            anchor = main.one(cls='work-end')
            position = main.children.index(anchor)
            additions = parse(markup(language)).children
            for node in additions:
                if isinstance(node, Node):
                    node.parent = main
            main.children[position:position] = additions
            css_url = os.path.relpath(target / STYLESHEET, path.parent).replace(os.sep, '/')
            link = Node('link', {'rel': 'stylesheet', 'href': css_url}.items(), head)
            # Keep the existing UI-polish stylesheet last in the cascade.
            tail = [n for n in head.all('link') if (n.attrs.get('href') or '').endswith('ui-polish.css')]
            if tail:
                head.children.insert(head.children.index(tail[0]), link)
            else:
                head.children.append(link)
            assert len(doc.one(id='collaborators').all(cls='collaborator-brand')) == len(BRANDS)
            assert 'data-content-status' in doc.one(id='client-perspective').attrs
            count += 1
        path.write_text(str(doc), encoding='utf-8')
    if not enabled:
        (target / STYLESHEET).unlink(missing_ok=True)
    result = {'enabled': enabled, 'pages': count, 'illustrative_brands_per_page': len(BRANDS) if enabled else 0}
    print('Studio collaborator concept:', result)
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', type=Path)
    add_collaborators(parser.parse_args().target)
