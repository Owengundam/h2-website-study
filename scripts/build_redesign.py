#!/usr/bin/env python3
"""Build the isolated H2 design study from the captured archive. No network needed.
Run from repository root: python scripts/build_redesign.py
Dependencies: beautifulsoup4, Pillow. Production indexing is opt-in via H2_PRODUCTION_URL.
"""
from __future__ import annotations
import hashlib, html, json, os, re, shutil
from pathlib import Path
from urllib.parse import unquote, urlparse
from bs4 import BeautifulSoup
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'redesign'
ARCHIVE=ROOT/'site/www.h2arch.com'
MEDIA=OUT/'assets/media'
MEDIA.mkdir(parents=True,exist_ok=True)
PRODUCTION=os.environ.get('H2_PRODUCTION_URL','').rstrip('/')
BASE=PRODUCTION or 'https://owengundam.github.io/h2-website-study/redesign'
SOURCES=[]
WARNINGS=[]
ASSET_CACHE={}
PAGES=[]
NEWS='https://www.h2arch.com/july-1-2025-indigo-hotel-nalati-xinjiang-huamei-shengdi-holiday-inn-express-hotel-nalati-xinjiang-huamei-shengdi-grand-opening/'
NALATI_SOURCE='https://www.h2arch.com/portfolio-item/xinjiang-nalati-indigo-holiday-inn-express-hotel-2/'

def e(text): return html.escape(str(text),quote=True)
def clean(text): return re.sub(r'\s+',' ',text).strip()
def choose(en,cn,lang): return cn if lang=='zh' else en

def local_asset(url):
    url=html.unescape(url).replace('https:/www.','https://www.')
    part=urlparse(url); p=unquote(part.path)
    if part.netloc:p='/'+part.netloc+p
    return ROOT/'site'/p.lstrip('/')

def asset(path):
    path=Path(path)
    key=str(path.relative_to(ROOT))
    if key in ASSET_CACHE:return ASSET_CACHE[key]
    try:
        with Image.open(path) as original:
            original.load()
            image=ImageOps.exif_transpose(original).convert('RGB')
    except Exception as ex:
        WARNINGS.append(f'Skipped unreadable image: {key}: {ex}')
        return None
    name=hashlib.sha1(key.encode()).hexdigest()[:12]
    full=image.copy();full.thumbnail((1920,1920),Image.Resampling.LANCZOS)
    small=image.copy();small.thumbnail((800,1000),Image.Resampling.LANCZOS)
    full.save(MEDIA/f'{name}.jpg',quality=87,optimize=True,progressive=True)
    small.save(MEDIA/f'{name}-small.jpg',quality=82,optimize=True,progressive=True)
    item={'full':f'assets/media/{name}.jpg','small':f'assets/media/{name}-small.jpg','width':full.width,'height':full.height,'small_width':small.width,'source':key}
    ASSET_CACHE[key]=item;SOURCES.append(item)
    return item

# Short display names are editorial labels; original names and years remain in the source record.
CONFIG=[
('xinjiang-nalati-indigo-holiday-inn-express-hotel-2','nalati-indigo','Nalati Indigo','那拉提英迪格','Nalati, Xinjiang','新疆 · 那拉提','retreats'),
('resea-indigo-hotel-qinhuangdao','resea-indigo','Resea Indigo','秦皇岛如是海英迪格','Qinhuangdao, Hebei','河北 · 秦皇岛','retreats'),
('cordis-hotel-kunshan-2','cordis-kunshan','Cordis Kunshan','昆山康得思','Kunshan, Jiangsu','江苏 · 昆山','city'),
('st-regis-hotel-xian','st-regis-xian','St. Regis Xi’an','西安瑞吉','Xi’an, Shaanxi','陕西 · 西安','city'),
('anandi-hotel-an-ji-zhejiang-2','anandi-anji','The Anandi Anji','安吉阿纳迪','Anji, Zhejiang','浙江 · 安吉','retreats'),
('st-regis-hotel-sanya','st-regis-sanya','St. Regis Sanya','三亚瑞吉','Sanya, Hainan','海南 · 三亚','retreats'),
('the-unbound-collection-by-hyatt-pingyao','hyatt-pingyao','Hyatt Unbound Pingyao','平遥凯悦臻选','Pingyao, Shanxi','山西 · 平遥','retreats'),
('melia-hotel-xi-xian-new-district-xian','melia-xian','Meliá Xi’an','西安美利亚','Xi’an, Shaanxi','陕西 · 西安','retreats'),
('hyatt-regency-hotel-shijia-zhuang','hyatt-shijiazhuang','Hyatt Regency Shijiazhuang','石家庄凯悦','Shijiazhuang, Hebei','河北 · 石家庄','city'),
('sofitel-yangshan-wuxi','sofitel-yangshan','Sofitel Yangshan','无锡阳山索菲特','Wuxi, Jiangsu','江苏 · 无锡','retreats'),
('shuangyue-bay-dusit-devarana-hotel-huizhou-2','dusit-shuangyue-bay','Dusit Shuangyue Bay','惠州双月湾都喜天丽','Huizhou, Guangdong','广东 · 惠州','mixed'),
('crowne-plaza-hotel-hot-spring-center-qinhuangdao','qinhuangdao-hotel-hot-springs','Qinhuangdao Hotel & Hot Springs','秦皇岛酒店与温泉中心','Qinhuangdao, Hebei','河北 · 秦皇岛','retreats'),
('mixed-use-project-indigo-hotel-shijiazhuang-qiangda','qiangda-indigo','Qiangda Indigo & Mixed Use','石家庄强大英迪格综合体','Shijiazhuang, Hebei','河北 · 石家庄','mixed')]
PROJECTS=[]
for source,slug,title,title_zh,location,location_zh,category in CONFIG:
    path=ARCHIVE/'portfolio-item'/source/'index.html'
    soup=BeautifulSoup(path.read_text(encoding='utf-8'),'html.parser')
    hero=soup.select_one('link[as=image]')
    candidates=([hero['href']] if hero else [])+[a['href'] for a in soup.select('a.e-gallery-item[href]')]
    original_images=[]
    for url in candidates:
        file=local_asset(url)
        if file.is_file() and file not in original_images:original_images.append(file)
    # The original Hyatt page mixes in Resea imagery. Do not carry that mismatch forward.
    if slug=='hyatt-shijiazhuang':original_images=[p for p in original_images if p.name.startswith('05-')]
    imgs=[a for p in original_images if (a:=asset(p))]
    if not imgs:raise RuntimeError(f'No verified image for {slug}')
    vals=[clean(t.get_text(' ',strip=True)) for t in soup.select('.elementor-icon-list-text')]
    year=next((v for v in vals if re.fullmatch(r'20\d\d',v)),'')
    group=vals[-1] if vals else ''
    for tag in soup.select('script,style,header,footer,nav'):tag.decompose()
    ps=[]
    for t in soup.select('.elementor-widget-text-editor'):
        text=clean(t.get_text(' ',strip=True))
        if len(text)>80 and not text.startswith('2023 ©') and text not in ps:ps.append(text)
    zhfile=ARCHIVE/'cn/portfolio-item'/(source+'-cn')/'index.html'
    if not zhfile.exists():
        cn_candidates=list((ARCHIVE/'cn/portfolio-item').glob(source.replace('-2','')+'*/index.html'))
        zhfile=cn_candidates[0] if cn_candidates else zhfile
    zps=[]
    if zhfile.exists():
        z=BeautifulSoup(zhfile.read_text(encoding='utf-8'),'html.parser')
        for t in z.select('.elementor-widget-text-editor'):
            text=clean(t.get_text(' ',strip=True))
            if len(text)>40 and text not in zps:zps.append(text)
    PROJECTS.append({'source_slug':source,'slug':slug,'title':title,'title_zh':title_zh,'location':location,'location_zh':location_zh,'category':category,'year':year,'group':group,'images':imgs,'paragraphs':ps[:5],'paragraphs_zh':zps[:5],'source_url':f'https://www.h2arch.com/portfolio-item/{source}/','original_title':soup.title.get_text() if soup.title else title})
NALATI=PROJECTS[0]
# Deliberately curate three distinct shots from the 15.32-second source film.
FRAME_INFO=json.loads((OUT/'film-frames.json').read_text())
FRAMES=[]
for number,label,cn in [(5,'The principal hotel plan','主酒店组团的总平面'),(10,'A room framing the meadow','面向草原的室内视景'),(18,'A dispersed cluster of circular suites','分散布置的圆形客房组团')]:
    record=FRAME_INFO['frames'][number-1]
    image=asset(ROOT/record['path'])
    if image is None:raise RuntimeError('Chosen film frame cannot be read')
    FRAMES.append({**image,'time':record['time'],'label':label,'label_zh':cn})

def named(n):
    return next(a for a in NALATI['images'] if Path(a['source']).name==n)
NALATI_PHOTO=named('f347948dbacc931d3f9bc73e0178b23-scaled.jpg')
NALATI_COVER=named('511f6b1b93810eee5dd63d85c379046.jpg')
NALATI_MOUNTAIN=named('9815e4656a65c4727f61909d1da7f19-scaled.jpg')
NALATI_ARRIVAL=named('39771f80529c3445f7a9d70a2b6f1c7-scaled.jpg')
NALATI['cover']=NALATI_COVER
for p in PROJECTS:p.setdefault('cover',p['images'][0])

class Page:
    def __init__(self,route,lang='en'):
        self.lang=lang;self.route=('cn/' if lang=='zh' else '')+route
    def url(self,target=''):
        if target.startswith(('https://','http://','mailto:','tel:','#')):return target
        dest=OUT/target
        # Explicit index.html lets the same export work on Pages and a simple local server.
        if not Path(target).suffix:dest=dest/'index.html'
        return os.path.relpath(dest,OUT/self.route).replace(os.sep,'/')
    def link(self,target=''):
        return self.url(('cn/' if self.lang=='zh' else '')+target)
    def tr(self,en,cn):return choose(en,cn,self.lang)
    def image(self,im,alt,lazy=True,small=False,cls=''):
        return f'<img src="{e(self.url(im["small"] if small else im["full"]))}" srcset="{e(self.url(im["small"]))} {im["small_width"]}w, {e(self.url(im["full"]))} {im["width"]}w" sizes="{("(max-width: 700px) 50vw, 20vw" if small else "(max-width:700px) 100vw, 90vw")}" width="{im["width"]}" height="{im["height"]}" alt="{e(alt)}" loading="{("lazy" if lazy else "eager")}" decoding="async" {("fetchpriority=\"high\"" if not lazy else "")} class="{e(cls)}">'
    def figure(self,im,caption,cls='',note=None,lazy=True):
        return f'<figure class="{cls}" data-reveal><a class="image-link" href="{e(self.url(im["full"]))}" data-lightbox data-caption="{e(caption)}">{self.image(im,caption,lazy)}</a><figcaption class="figure-caption"><span>{e(caption)}</span><span>{e(note or self.tr("H2 project archive","H2 项目档案"))}</span></figcaption></figure>'
    def arrow(self,route,label):return f'<a class="arrow-link" href="{e(self.link(route))}"><span>{e(label)}</span><span aria-hidden="true">↗</span></a>'
    def write(self,title,body,section='work',description='',cover=None,extra_schema=None):
        current=self.route.removeprefix('cn/')
        nav=''.join(f'<a href="{e(self.link(route))}"'+(' aria-current="page"' if section==key or (section=='project' and key=='work') else '')+f'>{self.tr(label,cn)}</a>' for key,route,label,cn in [('studio','studio/','Studio','事务所'),('work','work/','Work','作品'),('journal','journal/','Journal','手记'),('contact','contact/','Contact','联系')])
        alt_lang='en' if self.lang=='zh' else 'zh'
        lang_url=self.url(current if self.lang=='zh' else 'cn/'+current)
        cover=cover or NALATI_COVER
        imageurl=f'{BASE}/{cover["full"]}'
        canonical=f'{BASE}/{self.route}'
        schema={'@context':'https://schema.org','@type':'WebPage','name':title,'description':description,'url':canonical,'inLanguage':'zh-CN' if self.lang=='zh' else 'en','isPartOf':{'@type':'WebSite','name':'H2 Architecture — Design Study','url':BASE+'/'}}
        if extra_schema:schema.update(extra_schema)
        footer=f'''<footer class="site-footer"><div class="footer-top"><p class="footer-statement">{self.tr('Architecture, grounded in place.','让建筑，回到场所。')}</p><nav class="footer-nav" aria-label="Footer">{nav}</nav></div><div class="footer-bottom"><span>H2 ARCHITECTURE · 上海赫图建筑设计事务所</span><span><a href="mailto:info@h2arch.com">info@h2arch.com</a> · Shanghai</span><span class="review-label">{self.tr('DESIGN STUDY · EDITORIAL CONTENT FOR REVIEW','设计研究版本 · 编辑内容待审核')}</span><a href="https://www.h2arch.com/">{self.tr('Original website ↗','原网站 ↗')}</a></div></footer>'''
        dialog=f'''<dialog class="lightbox" aria-label="{self.tr('Project image viewer','项目图片浏览')}"><button class="lightbox-close" data-lightbox-close aria-label="{self.tr('Close gallery','关闭图片')}">×</button><div class="lightbox-inner"><img class="lightbox-image" alt=""><div class="lightbox-bottom"><p class="lightbox-caption"></p><div class="lightbox-controls"><button data-lightbox-prev aria-label="{self.tr('Previous image','上一张')}">←</button><span class="lightbox-count"></span><button data-lightbox-next aria-label="{self.tr('Next image','下一张')}">→</button></div></div></div></dialog>'''
        html_doc=f'''<!doctype html><html lang="{'zh-CN' if self.lang=='zh' else 'en'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} — H2 Architecture</title><meta name="description" content="{e(description)}"><meta name="robots" content="{'index,follow,max-image-preview:large' if PRODUCTION else 'noindex,follow'}"><meta name="theme-color" content="#fbfaf6"><link rel="canonical" href="{e(canonical)}"><link rel="alternate" hreflang="en" href="{BASE}/{e(current)}"><link rel="alternate" hreflang="zh-CN" href="{BASE}/cn/{e(current)}"><meta property="og:type" content="website"><meta property="og:site_name" content="H2 Architecture"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}"><meta property="og:url" content="{e(canonical)}"><meta property="og:image" content="{e(imageurl)}"><meta name="twitter:card" content="summary_large_image"><link rel="icon" href="{self.url('favicon.svg')}" type="image/svg+xml"><link rel="stylesheet" href="{self.url('site.css')}"><link rel="stylesheet" href="{self.url('reference-layout.css')}"><script src="{self.url('site.js')}" defer></script><script type="application/ld+json">{json.dumps(schema,ensure_ascii=False).replace('</','<\\/')}</script></head><body class="{section}-page" id="top"><a class="skip-link" href="#content">{self.tr('Skip to content','跳至内容')}</a><header class="site-header"><a class="brand" href="{self.link('')}" aria-label="H2 Architecture — {self.tr('Home','首页')}"><span class="brand-mark">H2</span><span class="brand-label">ARCHITECTURE<br>赫图建筑</span></a><button class="menu-toggle" aria-expanded="false" aria-controls="navigation"><span>{self.tr('Menu','菜单')}</span><span class="menu-icon" aria-hidden="true">+</span></button><div class="nav-wrap" id="navigation"><nav class="main-nav" aria-label="{self.tr('Main navigation','主导航')}">{nav}</nav><div class="language-switch"><span class="current">{self.tr('EN','中文')}</span><span>/</span><a href="{lang_url}" hreflang="{alt_lang}">{self.tr('中文','EN')}</a></div></div></header><main id="content">{body}</main>{footer}<a class="back-top" href="#top" aria-label="{self.tr('Back to top','返回顶部')}">↑</a>{dialog}</body></html>'''
        dest=OUT/self.route/'index.html';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(html_doc,encoding='utf-8');PAGES.append(self.route)

def title(p,pg):return p['title_zh'] if pg.lang=='zh' else p['title']
def location(p,pg):return p['location_zh'] if pg.lang=='zh' else p['location']
def chapter(pg,no,label,labelzh,headline,headlinezh,paragraphs,paragraphszh,id):
    return f'<section class="chapter" id="{id}" data-reveal><div class="chapter-label"><span>{no}</span><span>{pg.tr(label,labelzh)}</span></div><div class="chapter-copy"><h2>{pg.tr(headline,headlinezh)}</h2>'+''.join(f'<p>{e(t)}</p>' for t in choose(paragraphs,paragraphszh,pg.lang))+'</div></section>'
def facts(pg,items):return '<dl class="facts-grid">'+''.join(f'<div class="fact"><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k,v in items)+'</dl>'
def next_project(pg,p):return f'<section class="next-project"><div><p class="eyebrow muted">{pg.tr("Next project","下一个项目")}</p><h2><a href="{pg.link("projects/"+p["slug"]+"/")}">{e(title(p,pg))}</a></h2></div><a href="{pg.link("projects/"+p["slug"]+"/")}" aria-label="{e(title(p,pg))}">↗</a></section>'

for lang in ['en','zh']:
    for route in ['', 'work/']:
        pg=Page(route,lang)
        filters=''.join(f'<button type="button" data-filter="{val}" aria-pressed="{str(val=="all").lower()}">{pg.tr(en,cn)}</button>' for val,en,cn in [('all','All','全部'),('retreats','Retreats','度假'),('city','City hotels','城市酒店'),('mixed','Mixed use','综合体')])
        cards=[]
        for i,p in enumerate(PROJECTS):
            feature=pg.tr('Featured case study','重点项目') if i==0 else ''
            cards.append(f'''<article class="project-card" data-category="{p['category']}"><a href="{pg.link('projects/'+p['slug']+'/')}" aria-label="{e(title(p,pg)+' — '+location(p,pg))}"><div class="card-image">{pg.image(p['cover'],title(p,pg)+' — '+location(p,pg),lazy=i>=5,small=True)}<span class="card-enter" aria-hidden="true">↗</span></div><div class="card-caption"><h2 class="card-title">{e(title(p,pg))}</h2><span class="card-year">{p['year']}</span></div><p class="card-location">{e(location(p,pg))}<span class="feature-label">{feature}</span></p></a></article>''')
        cards.append(f'<aside class="portfolio-note" data-filter-decoration><p class="eyebrow">{pg.tr("In focus / Nalati","重点项目 / 那拉提")}</p><h2>{pg.tr("A place in the meadow.","在草原，<br>形成场所。")}</h2>{pg.arrow("projects/nalati-indigo/",pg.tr("Discover the story","阅读项目故事"))}</aside>')
        body=f'''<section class="work-main"><div class="work-tools container"><h1 class="work-heading">{pg.tr('Selected work','精选作品')} <sup data-project-count aria-live="polite">13</sup></h1><div class="work-right"><div class="filter-bar" aria-label="{pg.tr('Filter projects','筛选项目')}">{filters}</div><div class="view-switch" aria-label="{pg.tr('Portfolio view','作品视图')}"><button type="button" data-view-button="grid" aria-pressed="true">{pg.tr('Grid','图集')}</button><button type="button" data-view-button="index" aria-pressed="false">{pg.tr('Index','目录')}</button></div></div></div><div class="project-grid" data-view="grid">{''.join(cards)}</div><p class="no-results container" hidden>{pg.tr('No projects in this selection.','此分类暂无项目。')}</p></section><section class="work-end container"><p>{pg.tr('Hotels, retreats and places to come together. Architecture shaped by its setting.','酒店、度假与相聚的场所。让建筑回应它所在的环境。')}</p>{pg.arrow('projects/nalati-indigo/',pg.tr('Explore Nalati Indigo','走进那拉提英迪格'))}</section>'''
        pg.write(pg.tr('Selected Work','精选作品'),body,'work',pg.tr('H2 Architecture: hotels, resorts and mixed-use projects. Explore Nalati Indigo and the practice’s hospitality portfolio.','赫图建筑酒店、度假与综合体项目。以那拉提英迪格为起点，了解场地、设计与落成。'))
    # Flagship case study: original evidence is linked, interpretation is identified at the end.
    pg=Page('projects/nalati-indigo/',lang)
    body=f'''<header class="project-intro container"><div><p class="eyebrow">{pg.tr('Xinjiang · China / Featured project','中国 · 新疆 / 重点项目')}</p><h1>{pg.tr('Nalati Indigo','那拉提英迪格')}</h1><p class="subtitle">{pg.tr('Hotel Indigo & Holiday Inn Express · Nalati','那拉提英迪格与智选假日酒店')}</p></div><div class="project-summary"><p>{pg.tr('A meadow destination shaped by local culture, low-rise buildings and the experience of arriving in a landscape.','从草原文化、低密度建筑和抵达体验出发，构筑那拉提的度假目的地。')}</p><a class="arrow-link" href="#challenge"><span>{pg.tr('Read the project','阅读项目')}</span><span aria-hidden="true">↓</span></a></div></header>'''
    body+=pg.figure(NALATI_PHOTO,pg.tr('Water, timber and the space between buildings.','水面、木构与建筑之间的空间。'),'hero-figure',pg.tr('Published project photography · 2025','已发布项目摄影 · 2025'),lazy=False)
    body+=f'''<div class="project-strip"><nav aria-label="{pg.tr('Project chapters','项目章节')}"><a href="#challenge">{pg.tr('Challenge','挑战')}</a><a href="#solution">{pg.tr('Solution','回应')}</a><a href="#outcome">{pg.tr('Outcome','落成')}</a><a href="#film">{pg.tr('Film','影像')}</a><a href="#details">{pg.tr('Details','资料')}</a></nav><button class="share-button" data-share>{pg.tr('Share project ↗','分享项目 ↗')}</button></div>'''
    body+=chapter(pg,'01','The challenge','设计挑战','Make a destination, not simply a hotel.','不止一座酒店，而是一处目的地。',[
        'At Nalati, hotel accommodation meets the life and culture of the meadow. The wider project brings Hotel Indigo and Holiday Inn Express into the same destination, with local settlement patterns, distinctive dwellings and pastoral traditions informing the design.',
        'The central design question is how that regional identity can become an experience of space rather than a decorative theme. The response begins with planning, the relationship between buildings and outdoor life, and encounters with the surrounding landscape.'
    ],['赫图对那拉提的设计构想，将酒店居住与草原生活、地域文化联系起来。项目同时包含英迪格与智选假日酒店，并以当地聚落肌理、特色居所和牧民生活作为设计线索。','核心问题是：如何让地域性成为真实的空间体验，而不只是表面的装饰主题？从已发布的设计说明出发，项目的着眼点在于规划布局、建筑与户外生活的关系，以及人们与周围景观的相遇。'],'challenge')
    body+='<div class="image-pair">'+pg.figure(FRAMES[0],pg.tr('Film still · The main hotel plan, read from above.','视频关键帧 · 从上方阅读主酒店布局。'),note=f"2024 / {FRAMES[0]['time']:.2f}s")+pg.figure(FRAMES[2],pg.tr('Film still · Paths connect a cluster of circular suites.','视频关键帧 · 路径串联圆形客房组团。'),note=f"2024 / {FRAMES[2]['time']:.2f}s")+'</div>'
    body+=chapter(pg,'02','The solution','建筑回应','Bring the scale down to the landscape.','让建筑的尺度，回到场地。',[
        'The published plan uses a low-density composition rather than a single continuous hotel mass. H2 describes the inclusion of yurt-inspired elements as distinctive moments within that larger arrangement. The selected film frames make this relationship legible: a principal hotel group and a more dispersed pattern of circular buildings connected by paths.',
        'Beige wall surfaces, timber elements and dark metal roofs establish the exterior palette. Across the drawings and published photographs, the emphasis moves between solid walls, open frames and the spaces between buildings. Water and planted courts give those transitions a visible presence.'
    ],['已发布的总图呈现了低密度的建筑组合，而不是一整块连续的酒店体量。赫图将毡房意象引入组团，作为其中具有辨识度的节点。选取的视频画面进一步呈现了两种组织方式：主要酒店组团，以及由路径联系的分散圆形建筑。','赫图的开业介绍记录了米色墙面、木构元素与深色金属屋面的立面材料组合。从设计图像到已发布摄影，可以读到实体墙面、开放框架和建筑间隙的不同节奏。水面和种植庭院让这些过渡空间更加清晰。'],'solution')
    body+='<div class="image-pair staggered">'+pg.figure(NALATI_COVER,pg.tr('A circular roof form against Nalati’s mountain setting.','圆形屋面与那拉提的山地背景。'),note=pg.tr('Published photography','已发布摄影'))+pg.figure(NALATI_ARRIVAL,pg.tr('An arrival marked by a timber-framed threshold.','木构门廊标记抵达的瞬间。'),note=pg.tr('Published photography','已发布摄影'))+'</div>'
    body+=pg.figure(FRAMES[1],pg.tr('Film still · An interior view directed toward the meadow.','视频关键帧 · 面向草原的室内视景。'),'full-image',pg.tr(f"Design-stage visualization · {FRAMES[1]['time']:.2f}s",f"设计阶段可视化 · {FRAMES[1]['time']:.2f}s"))
    body+=chapter(pg,'03','The outcome','落成记录','A new chapter, opened in July 2025.','2025年7月，开启新的篇章。',[
        'H2’s opening announcement records 1 July 2025 as the opening date for Nalati Indigo and Holiday Inn Express. It describes 151 rooms and suites at Hotel Indigo, with panoramic windows or balconies connecting the accommodation to views of the grassland and mountains.',
        'The story now moves from drawings and models to the life of a working destination. Published photographs show the architecture within its mountain setting: circular roof forms, framed entrances, planted courts and water gathering the buildings into a place.'
    ],['赫图发布的开业消息记录：那拉提英迪格与智选假日酒店于2025年7月1日正式开业。其中，英迪格酒店拥有151间客房及套房，借助全景窗或观景阳台，与草原及山地景观建立联系。','项目由图纸与模型走向正式运营的目的地。已发布摄影呈现了山地背景中的建筑：圆形屋面、框景门廊、种植庭院与水面，将不同组团联系成为一个场所。'],'outcome')
    body+=pg.figure(NALATI_MOUNTAIN,pg.tr('Published project view · Buildings and the mountain horizon.','已发布项目影像 · 建筑与远处的山脊。'),'full-image',pg.tr('H2 archive · July 2025','H2 档案 · 2025年7月'))
    body+=f'''<section class="film-section" id="film"><div class="section-topline"><h2>{pg.tr('The project in motion','流动的项目影像')}</h2><span class="eyebrow muted">00:15 · 2024</span></div><div class="film-player"><video controls playsinline preload="none" poster="{pg.url(FRAMES[0]['full'])}" aria-label="{pg.tr('Nalati design visualization film, silent web edit','那拉提设计可视化视频，无声网页版本')}"><source src="{pg.url('assets/indigo/nalati-film.mp4')}" type="video/mp4"><p><a href="{pg.url('assets/indigo/nalati-film.mp4')}">{pg.tr('Open the project film','打开项目视频')}</a></p></video></div><p class="film-note">{pg.tr('A short design film, 2024. The plan, the room and the cluster: three scales of the same place. Design-stage visualizations; silent web edit.','2024年设计短片。总图、房间与组团：在三个尺度中阅读同一个场所。画面为设计阶段可视化，网页版本无声。')}</p><div class="frame-strip">'''
    for f in FRAMES:
        cap=pg.tr(f['label'],f['label_zh'])
        body+=f'<a href="{pg.url(f["full"])}" data-lightbox data-caption="{e(cap)}">{pg.image(f,cap,small=True)}<span>{f["time"]:05.2f}s · {e(cap)}</span></a>'
    body+='</div></section>'
    items=[(pg.tr('Project','项目'),'Hotel Indigo & Holiday Inn Express'),(pg.tr('Location','地点'),pg.tr('Nalati, Xinjiang, China','中国新疆那拉提')),(pg.tr('Practice','事务所'),'H2 Architecture / 赫图建筑'),(pg.tr('Hotel group','酒店集团'),'IHG'),(pg.tr('Year in design archive','设计档案年份'),'2023'),(pg.tr('Design film','设计视频'),'2024'),(pg.tr('Opening','开业'),'1 July 2025'),(pg.tr('Indigo accommodation','英迪格客房'),pg.tr('151 rooms and suites','151间客房及套房')),(pg.tr('Project scope in H2 account','H2发布内容所述范围'),pg.tr('Planning and architectural design','规划与建筑设计'))]
    body+=f'<section class="chapter" id="details"><div class="chapter-label"><span>04</span><span>{pg.tr("Project details","项目资料")}</span></div><div class="chapter-copy">'+facts(pg,items)
    body+=f'''<div class="source-notes"><p>{pg.tr('Editorial case study prepared from H2’s existing public materials. The challenge and solution sections are an editorial synthesis, not a quoted client brief or founder statement. Exact contractual scope and the full collaborator list require studio confirmation.','本案例由赫图现有公开材料编辑整理。“挑战”与“回应”为编辑归纳，不是客户任务书或主创原话。具体合同范围与完整合作团队仍需事务所确认。')}</p><p>{pg.tr('Images and film: as published in the H2 project archive. Individual photography credits are not supplied there. H2’s opening article acknowledges Hongxing Cultural Travel / the hotel’s WeChat materials. Confirm image permissions and complete credits before an official launch; interior imagery does not establish H2’s interior-design authorship.','图片与视频来源：H2项目档案。档案未完整列出单张摄影署名。赫图开业文章注明部分图文来自红星文旅／酒店公众号。正式上线前需确认图片授权并补齐署名；室内影像不代表赫图拥有室内设计署名。')}</p><p><a href="{NALATI_SOURCE}">{pg.tr('Original project record ↗','原项目记录 ↗')}</a> · <a href="{NEWS}">{pg.tr('Opening announcement ↗','开业公告 ↗')}</a> · <a href="{e(FRAME_INFO['source'])}">{pg.tr('Source film ↗','原始视频 ↗')}</a></p></div></div></section>'''
    body+=next_project(pg,PROJECTS[1])
    pg.write(pg.tr('Nalati Indigo — Challenge, Solution, Outcome','那拉提英迪格 — 挑战、回应与落成'),body,'project',pg.tr('A detailed H2 case study: Nalati Indigo’s meadow setting, low-density architecture, three film keyframes and documented July 2025 opening.','那拉提英迪格项目深读：草原场地、低密度建筑、三个视频关键帧，以及2025年7月的开业记录。'),NALATI_PHOTO)
    # The remainder of the portfolio: retain real archive descriptions, no invented results.
    for i,p in enumerate(PROJECTS[1:],1):
        pg=Page('projects/'+p['slug']+'/',lang)
        body=f'<header class="project-intro container"><div><p class="eyebrow">{e(location(p,pg))}</p><h1>{e(title(p,pg))}</h1><p class="subtitle">{pg.tr("H2 project archive","H2 项目档案")} · {e(p["year"])}</p></div><div class="project-summary"><p>{e(p["group"])}</p>{pg.arrow("work/",pg.tr("All work","全部作品"))}</div></header>'
        body+=pg.figure(p['images'][0],title(p,pg),'hero-figure',lazy=False)
        paragraphs=p['paragraphs_zh'] if lang=='zh' and p['paragraphs_zh'] else p['paragraphs']
        copy=''.join(f'<p>{e(t)}</p>' for t in paragraphs)
        if not copy:copy=f'<p>{pg.tr("Explore the project through H2’s published image archive. The original project record is linked below.","通过赫图已发布的影像档案浏览本项目。下方保留原始项目记录链接。")}</p>'
        if lang=='zh' and not p['paragraphs_zh'] and p['paragraphs']:copy='<p class="editorial-note">项目说明保留英文档案版本。</p><div lang="en">'+copy+'</div>'
        body+=f'<section class="chapter"><div class="chapter-label"><span>01</span><span>{pg.tr("The project","项目介绍")}</span></div><div class="chapter-copy">{copy}</div></section>'
        if len(p['images'])>1:body+='<div class="generic-gallery">'+''.join(pg.figure(im,pg.tr(f'{p["title"]} · Project image {n+2}',f'{p["title_zh"]} · 项目影像 {n+2}')) for n,im in enumerate(p['images'][1:9]))+'</div>'
        body+='<section class="chapter"><div class="chapter-label"><span>02</span><span>'+pg.tr('Details','资料')+'</span></div><div class="chapter-copy">'+facts(pg,[(pg.tr('Location','地点'),location(p,pg)),(pg.tr('Year in source archive','源档案年份'),p['year']),(pg.tr('Hotel group in archive','档案酒店集团'),p['group'])])
        note=pg.tr('The year is the year stated in the original archive, not a verified completion date. The source may include design-stage imagery. Current naming, status, precise scope and image credits require confirmation before official publication.','年份沿用原档案标注，并非经核实的竣工年份。源材料可能包含设计阶段图像。正式发布前，应确认现名称、项目状态、具体服务范围和图片署名。')
        if p['slug']=='qinhuangdao-hotel-hot-springs':note+=' '+pg.tr('Chinese and English archive versions use different hotel brands; a neutral project title is used here pending confirmation.','原网站中英文档案使用不同酒店品牌，本版本暂用中性项目名称，等待核实。')
        body+=f'<div class="source-notes"><p>{note}</p><p><a href="{p["source_url"]}">{pg.tr("Original project record ↗","原始项目记录 ↗")}</a></p></div></div></section>'+next_project(pg,PROJECTS[(i+1)%len(PROJECTS)])
        pg.write(title(p,pg),body,'project',f'{title(p,pg)} — {location(p,pg)}. H2 Architecture project archive.',p['cover'])
    # Studio: a factual founder biography, not fabricated thought leadership.
    pg=Page('studio/',lang)
    body=f'<section class="page-lead"><p class="eyebrow">{pg.tr("The studio","事务所")}</p><div><h1>{pg.tr("Architecture for hospitality.\nA sense of place.","以酒店建筑，\n回应场所。")}</h1><p>{pg.tr("H2 Architecture is a Shanghai-based practice working across hotels, resorts and hospitality-led mixed-use projects. Its work connects architectural design with destination planning and the needs of owners and hotel groups.","赫图建筑立足上海，专注酒店、度假目的地与酒店主导的综合体项目，将建筑设计、目的地规划以及业主和酒店集团的需求联系起来。")}</p></div></section>'
    body+=pg.figure(NALATI_MOUNTAIN,pg.tr('Nalati · A project shaped by its setting.','那拉提 · 回应所在环境的建筑。'),'studio-image')
    body+=chapter(pg,'01','Our work','工作领域','From the first idea to the architectural experience.','从最初的构想，到建筑的体验。',[
        'The practice’s published services span strategy, planning, architectural design and project coordination. Hotels and resorts are the core of its work, alongside tourism destinations, residential developments and mixed-use projects.',
        'The portfolio is presented here as a connected body of work: places to arrive, stay, meet and return to. Each project page retains a link to its source record so that the architectural story and the documented facts remain connected.'
    ],['事务所公开的服务内容覆盖前期策略、规划、建筑设计和项目协调。酒店与度假建筑是核心方向，并延伸至旅游目的地、住宅开发及综合体项目。','本作品集将这些项目视作一组相互关联的实践：抵达、停留、相聚，以及再次回来。每个项目页面均保留源档案链接，让设计叙述与事实记录保持联系。'],'approach')
    services=[('Strategy','前期策略','Research, positioning, product advice and development phasing.','研究、定位、产品建议与开发分期。'),('Planning','规划','Destination, tourism and urban planning.','目的地、旅游及城市规划。'),('Architecture','建筑','Urban hotels, resort hotels and luxury villas.','城市酒店、度假酒店与高端别墅。'),('Coordination','协调','Project-management consultancy and general coordination.','项目管理顾问与总体协调。')]
    body+='<section class="chapter"><div class="chapter-label"><span>02</span><span>'+pg.tr('Expertise','专业领域')+'</span></div><ul class="service-list">'+''.join(f'<li><span class="number">0{i+1}</span><div><h3>{pg.tr(a,b)}</h3><p>{pg.tr(c,d)}</p></div></li>' for i,(a,b,c,d) in enumerate(services))+'</ul></section>'
    # Select a studio interior from the practice profile; do not invent a founder portrait.
    profile=BeautifulSoup((ARCHIVE/'profile/index.html').read_text(),'html.parser')
    portrait=None
    for img in profile.select('img'):
        alt=img.get('alt','');f=local_asset(img.get('src',''))
        if f.is_file() and not any(x in str(f).lower() for x in ['logo','favicon']):
            a=asset(f)
            if a and a['height']>a['width']*.9:portrait=a;break
    founder_copy=f'<div><p class="eyebrow">{pg.tr("Founder / Chief architect","创始人 / 首席建筑师")}</p><h2>{pg.tr("Yu Hong","洪羽")}</h2><p>{pg.tr("Yu Hong is H2’s founder and chief architect. He holds a Master of Architecture from the University of Arizona. Before H2, he worked with WATG for more than a decade, including as a senior designer and associate.","洪羽是赫图建筑创始人、首席建筑师，拥有美国亚利桑那大学建筑学硕士学位。创办赫图之前，他曾在WATG工作十余年，担任资深设计师及Associate。")}</p><p>{pg.tr("His published biography spans master planning, urban hotels and destination resorts. Experience gained before H2 belongs to his individual career history and should not be confused with projects commissioned to the H2 practice.","其公开履历涵盖总体规划、城市酒店与度假目的地。创办赫图之前的项目经验属于个人职业履历，不应等同于赫图事务所承接的项目。")}</p><div class="source-notes"><a href="https://www.h2arch.com/profile/">{pg.tr("Published biography ↗","公开履历 ↗")}</a></div></div>'
    body+=f'<section class="portrait-layout">{pg.image(portrait,pg.tr("Inside the H2 studio, from the practice profile","赫图工作室空间，图片来自事务所公开介绍")) if portrait else "<p class=eyebrow>H2 / PEOPLE</p>"}{founder_copy}</section>'
    body+=f'<section class="work-end container"><p>{pg.tr("A conversation starts with a place and an ambition.","一次交流，从场地与愿景开始。")}</p>{pg.arrow("contact/",pg.tr("Start a conversation","开始交流"))}</section>'
    pg.write(pg.tr('Studio','事务所'),body,'studio',pg.tr('H2 Architecture: hospitality design, destination planning and the practice of founder Yu Hong.','赫图建筑：酒店设计、目的地规划与创始人洪羽的建筑实践。'))
    # Journal: genuinely readable articles, not dead placeholder cards.
    pg=Page('journal/',lang)
    body=f'<section class="page-lead"><p class="eyebrow">{pg.tr("Journal","手记")}</p><div><h1>{pg.tr("Behind the work.","作品背后的思考。")}</h1><p>{pg.tr("Project readings, archive notes and moments in the life of a place. A closer look at the ideas behind H2’s hospitality architecture.","项目解读、档案笔记与场所生长的片段。走近赫图酒店建筑背后的设计思考。")}</p></div></section><div class="journal-grid">'
    for im,r,tag,tagcn,head,headcn,desc,desccn in [(FRAMES[2],'journal/reading-nalati/','Design reading','设计解读','From meadow to place','从草原，到场所','Three film frames reveal three scales of the Nalati design: the plan, the room and the cluster.','用三个视频关键帧，阅读那拉提的总图、房间与组团三个尺度。'),(NALATI_ARRIVAL,'journal/nalati-opening/','Project milestone / 2025','项目进展 / 2025','Nalati opens a new chapter','那拉提，开启新的篇章','The opening of Hotel Indigo and Holiday Inn Express, recorded on 1 July 2025.','记录英迪格与智选假日酒店于2025年7月1日正式开业。')]:
        body+=f'<article class="journal-card"><a href="{pg.link(r)}">{pg.image(im,pg.tr(head,headcn))}<p class="eyebrow">{pg.tr(tag,tagcn)}</p><h2>{pg.tr(head,headcn)}</h2><p>{pg.tr(desc,desccn)}</p></a>{pg.arrow(r,pg.tr("Read the story","阅读全文"))}</article>'
    body+='</div>'
    pg.write(pg.tr('Journal','手记'),body,'journal',pg.tr('Editorial readings and project milestones from the H2 Architecture archive.','来自赫图建筑项目档案的编辑解读与项目记录。'))
    for opening in [False,True]:
        pg=Page('journal/nalati-opening/' if opening else 'journal/reading-nalati/',lang)
        heading=pg.tr('Nalati opens a new chapter','那拉提，开启新的篇章') if opening else pg.tr('From meadow to place','从草原，到场所')
        im=NALATI_ARRIVAL if opening else FRAMES[2]
        body=f'<section class="page-lead"><p class="eyebrow">{pg.tr("Project milestone / 2025","项目进展 / 2025") if opening else pg.tr("An editorial project reading","编辑项目解读")}</p><div><h1>{heading}</h1><p>{pg.tr("H2 project archive / Edited for this design study","H2 项目档案 / 本研究版本编辑整理")}</p></div></section>'+pg.figure(im,heading,'hero-figure',lazy=False)+'<article class="article-body">'
        if opening:
            body+=f'<p>{pg.tr("On 1 July 2025, Nalati Indigo and Holiday Inn Express opened a new chapter in Xinjiang’s meadow landscape. H2 shared the opening on 21 July, marking the transition from a design project to a place welcoming its guests.","2025年7月1日，那拉提英迪格与智选假日酒店在新疆草原开启新的篇章。赫图于7月21日分享开业消息，记录项目从设计构想到迎接住客的转变。")}</p><h2>{pg.tr("From a design archive to an opened destination","从设计档案，到正式开业")}</h2><p>{pg.tr("The 2023 project archive and January 2024 design film trace the early spatial ambitions: a principal hotel group, circular suites and an architecture responding to its surroundings. The 2025 opening adds a new layer to that record, with published photography bringing the completed setting into view.","2023年项目档案与2024年1月的设计短片，记录了早期的空间构想：主酒店组团、圆形客房，以及回应周边环境的建筑。2025年的开业为这份记录增添了新的一层，项目摄影让落成后的场所进入视野。")}</p><p>{pg.tr("Hotel Indigo is described in H2’s account as having 151 rooms and suites. The broader project also includes Holiday Inn Express. That room count is not presented as a combined total for both hotels.","赫图公开介绍中，英迪格酒店拥有151间客房及套房；整体项目同时包含智选假日酒店。此处不将这一客房数量当作两家酒店的合计。")}</p>'
        else:
            body+=f'<p>{pg.tr("A plan, a room, a cluster. In just fifteen seconds, Nalati’s design film moves between three scales of experience. Seen together, these frames offer a way to read the project from the organization of the whole to the intimacy of a view.","一张总图、一个房间、一处组团。在约十五秒内，那拉提设计短片切换了三种体验尺度。将这些画面放在一起，可以从整体组织走向一段视景的亲密体验。")}</p>'
            sections=[('The plan: relationships before objects','总图：先看关系，再看建筑','The overhead view makes the relation between the main volumes, open space and water readable. It is a way to see the project as an arrangement, rather than as a collection of isolated façades.','俯视画面使主要体量、开放空间和水面的关系清晰可读。它让人把项目理解为一种空间组织，而不只是几张独立的立面。'),('The room: where the eye is led','房间：视线被引向何处','The interior frame directs attention outward. The room becomes a threshold rather than an endpoint: a sheltered place from which the landscape can be seen, and a reminder that the experience of a hotel extends beyond its walls.','室内画面将注意力引向户外。房间成为一处过渡，而不是终点：它既提供庇护，也让景观进入视野，提示着酒店体验并不止于墙体之内。'),('The cluster: a different grain of occupation','组团：另一种占据场地的尺度','Circular units and connecting paths form a looser pattern than the principal hotel buildings. H2’s written project account connects yurt-inspired elements to the local cultural setting; the frame makes that change of scale visible.','圆形单元与连接路径形成了比主酒店更松散的组织。赫图的项目说明将毡房意象与地域文化联系起来，画面则让这种尺度变化变得可见。')]
            for a,b,c,d in sections:body+=f'<h2>{pg.tr(a,b)}</h2><p>{pg.tr(c,d)}</p>'
        body+=pg.arrow('projects/nalati-indigo/',pg.tr('Explore the full case study','阅读完整项目案例'))+f'<div class="source-notes"><p>{pg.tr("Editorial synthesis for the redesign branch; not a quotation or signed statement by Yu Hong.","本内容为改版分支的编辑归纳，并非洪羽的引语或署名观点。")}</p><p><a href="{NALATI_SOURCE}">H2 project record ↗</a> · <a href="{NEWS}">H2 opening announcement ↗</a></p></div></article>'
        pg.write(heading,body,'journal',heading+' — H2 Architecture',im)
    pg=Page('contact/',lang)
    body=f'''<section class="page-lead"><p class="eyebrow">{pg.tr('Contact','联系')}</p><div><h1>{pg.tr('Let’s talk about\nyour next place.','一起谈谈，\n下一个场所。')}</h1><p>{pg.tr('For hotel, resort and destination projects, begin with a conversation.','关于酒店、度假与目的地项目，从一次交流开始。')}</p></div></section><section class="contact-panel"><p class="eyebrow">{pg.tr('Project inquiries','项目咨询')}</p><div><a class="contact-email" href="mailto:info@h2arch.com">info@h2arch.com ↗</a><div class="contact-details"><div><h2>{pg.tr('Shanghai office','上海办公室')}</h2><p>{pg.tr('Room 2102, No. 118 Minsheng Road<br>Pudong, Shanghai<br>Binjiang Vanke Centre','上海市浦东新区民生路118号<br>滨江万科中心 2102室')}</p></div><div><h2>{pg.tr('Telephone','电话')}</h2><p><a href="tel:+862152004200">+86 21 5200 4200</a></p><h2 style="margin-top:24px">{pg.tr('Original contact record','原始联系信息')}</h2><p><a href="https://www.h2arch.com/contact/">h2arch.com ↗</a></p></div></div><p class="contact-hint">{pg.tr('A useful introduction includes the location, project type, approximate scale, current stage and your contact details. Please avoid sending confidential project documents until a suitable sharing arrangement has been agreed.','初次交流可提供项目地点、类型、大致规模、当前阶段与联系方式。在确认资料分享方式前，请勿直接发送保密项目文件。')}</p></div></section><section class="work-end container"><p>{pg.tr('A project is often the best introduction.','一个项目，就是最好的介绍。')}</p>{pg.arrow('projects/nalati-indigo/',pg.tr('View the Nalati case study','查看那拉提案例'))}</section>'''
    pg.write(pg.tr('Contact','联系'),body,'contact',pg.tr('Contact H2 Architecture in Shanghai for hotel, resort and destination design projects.','联系上海赫图建筑，探讨酒店、度假与目的地设计项目。'))

(OUT/'favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#fbfaf6"/><text x="5" y="45" fill="#24251f" font-family="Arial,sans-serif" font-size="39" letter-spacing="-4">H2</text></svg>')
(OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{e(BASE+"/"+r)}</loc></url>' for r in PAGES)+'</urlset>')
(OUT/'assets/source-manifest.json').write_text(json.dumps({'source':'H2 website archive inherited from main','film_source':FRAME_INFO['source'],'selected_frames':[{'time':f['time'],'source':f['source'],'file':f['full']} for f in FRAMES],'images':SOURCES,'warnings':WARNINGS},ensure_ascii=False,indent=2))
(OUT/'build-report.json').write_text(json.dumps({'pages':len(PAGES),'projects':len(PROJECTS),'languages':['en','zh-CN'],'optimized_images':len(ASSET_CACHE),'film_frames_used':len(FRAMES),'source_film_duration':FRAME_INFO['duration'],'preview_noindex':not bool(PRODUCTION),'warnings':WARNINGS},ensure_ascii=False,indent=2))
print(json.dumps({'pages':len(PAGES),'projects':len(PROJECTS),'images':len(ASSET_CACHE),'warnings':WARNINGS},ensure_ascii=False))
