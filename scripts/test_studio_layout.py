"""Read-only browser checks for the packaged Studio-as-homepage layout."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json, os
BASE=os.environ.get('H2_TEST_URL','http://127.0.0.1:8765/').rstrip('/')+'/'
OUT=Path(os.environ.get('H2_QA_DIR','layout-qa'))
OUT.mkdir(parents=True,exist_ok=True)
results=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    for width in (320,390,768,1440):
        page=browser.new_page(viewport={'width':width,'height':960 if width>700 else 844})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        for path in ('','cn/'):
            page.goto(BASE+path,wait_until='domcontentloaded')
            page.locator('.studio-landing img').evaluate('(i)=>i.decode()')
            page.wait_for_timeout(180)
            data=page.evaluate('''()=>{let h=document.querySelector('.site-header'),hero=document.querySelector('.studio-landing'),text=document.querySelector('.studio-work-copy'),video=document.querySelector('.studio-work-film');let rect=x=>{let r=x.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom}};return {header:rect(h),hero:rect(hero),text:rect(text),video:rect(video),headerBg:getComputedStyle(h).backgroundColor,blur:getComputedStyle(h).backdropFilter,scrollWidth:document.documentElement.scrollWidth,width:innerWidth,h1s:document.querySelectorAll('main h1').length,film:document.querySelector('.home-film').getAttribute('src'),oldOpening:!!document.querySelector('.home-opening'),first:document.querySelector('main').firstElementChild.className,brand:document.querySelector('.brand-logo').getAttribute('src')}}''')
            assert data['header']['y']==0 and data['hero']['y']==0,data
            assert data['headerBg'].endswith(', 0)'),data
            assert data['blur']=='none' and data['h1s']==1
            assert data['scrollWidth']<=width+1,data
            assert data['first']=='studio-landing' and not data['oldOpening']
            assert '20230928-atmosphere' in data['film'] and 'h2-logo-black.png' in data['brand']
            if width>700:
                assert data['video']['x']>=data['text']['x']+data['text']['width'],data
            else:
                assert data['video']['y']>=data['text']['bottom'],data
            if width==1440 and path=='':
                page.screenshot(path=str(OUT/'studio-home-desktop.jpg'),type='jpeg',quality=88)
            if width==390 and path=='':
                page.screenshot(path=str(OUT/'studio-home-mobile.jpg'),type='jpeg',quality=88)
            if width<=700:
                page.locator('.menu-toggle').click()
                assert page.locator('.main-nav').is_visible()
                assert page.locator('.menu-toggle').get_attribute('aria-expanded')=='true'
                page.keyboard.press('Escape')
                assert page.locator('.menu-toggle').get_attribute('aria-expanded')=='false'
            page.locator('#approach').scroll_into_view_if_needed()
            page.wait_for_timeout(350)
            assert 'is-past-hero' in page.locator('.site-header').get_attribute('class')
            if width==1440 and path=='':
                page.locator('.home-film').scroll_into_view_if_needed()
                page.wait_for_function("document.querySelector('.home-film').readyState>=2 && document.querySelector('.home-film').currentTime>0",timeout=45000)
                page.locator('.film-toggle').click()
                assert page.locator('.home-film').evaluate('(v)=>v.paused')
                page.screenshot(path=str(OUT/'studio-our-work-desktop.jpg'),type='jpeg',quality=88)
                page.locator('.film-toggle').click()
                page.wait_for_function("!document.querySelector('.home-film').paused")
                page.evaluate('scrollTo(0,0)')
                page.wait_for_function("document.querySelector('.home-film').paused")
            assert not errors,errors
            results.append({'width':width,'path':path,'passed':True,'measurements':data})
        page.goto(BASE+'work/',wait_until='domcontentloaded')
        assert page.locator('.project-card').count()==13
        page.locator('[data-filter="city"]').click()
        assert page.locator('.project-card:visible').count()==3
        page.locator('[data-filter="all"]').click()
        assert page.locator('.project-card:visible').count()==13
        assert page.locator('.main-nav a').first.get_attribute('href')=='../index.html'
        page.close()
    ctx=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
    page=ctx.new_page()
    page.goto(BASE,wait_until='domcontentloaded')
    assert page.locator('main h1').count()==1
    assert page.locator('.home-film').get_attribute('controls') is not None
    assert page.locator('.studio-work-copy').inner_text()
    browser.close()
(OUT/'studio-layout-report.json').write_text(json.dumps({'pages':results,'no_js':True,'work_filters':True,'original_film_playback':True},indent=2))
print('Studio landing, split video, original identity, EN/CN, mobile menu, Work filters, film playback and no-JS checks passed.')
