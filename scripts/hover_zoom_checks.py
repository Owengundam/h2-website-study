"""Regression checks for a real, clipped hover zoom (not a disabled transform)."""
from __future__ import annotations
import io
import json
import math
from pathlib import Path

STATE = '''el => {
  const image = el.querySelector('.card-image img');
  const frame = image.parentElement;
  const ir = image.getBoundingClientRect(), fr = frame.getBoundingClientRect();
  const s = getComputedStyle(image);
  return {
    scale: new DOMMatrixReadOnly(s.transform).m11,
    duration: parseFloat(s.transitionDuration),
    property: s.transitionProperty,
    frame: [fr.x, fr.y, fr.width, fr.height],
    cover: [fr.left-ir.left, fr.top-ir.top, ir.right-fr.right, ir.bottom-fr.bottom],
    clip: getComputedStyle(frame).clipPath
  };
}'''


def check_zoom(page, link, rest=1.0, zoom=1.02, qa=None, label='tile', pixel_check=False):
    """Sample real pointer enter/leave transitions and all four clipping edges."""
    link.locator('img').evaluate('el => el.decode()')
    link.scroll_into_view_if_needed()
    page.mouse.move(1, 1)
    page.wait_for_timeout(850)
    initial = link.evaluate(STATE)
    assert abs(initial['scale']-rest) < .0002, initial
    assert initial['property'] == 'transform' and initial['duration'] >= .75, initial
    assert initial['clip'].startswith('inset('), initial
    samples, checks = [], 3
    marker = None
    if pixel_check:
        # A deliberately vivid backing makes transient exposed pixels detectable.
        # This CSS exists only in this test's browser, never in the published site.
        marker = page.add_style_tag(content='.project-grid,.project-card,.card-image{background:#ff00ff!important}')

    def sample(phase, delay):
        nonlocal checks
        state = link.evaluate(STATE)
        assert min(state['cover']) >= .9, (phase, delay, state)
        assert max(abs(a-b) for a,b in zip(initial['frame'],state['frame'])) < .05, (phase,state)
        assert rest-.0002 <= state['scale'] <= zoom+.0002, state
        samples.append(dict(phase=phase, delay=delay, **state))
        checks += 3
        if pixel_check:
            from PIL import Image
            data = page.screenshot()
            image = Image.open(io.BytesIO(data)).convert('RGB')
            factor = image.width/page.viewport_size['width']
            x,y,w,h = state['frame']
            # Avoid captions and check thin strips just inside both image edges.
            xs = [x+.5, x+1.5, x+w-1.5, x+w-.5]
            for sx in xs:
                px = min(image.width-1,max(0,math.floor(sx*factor)))
                lo = max(0,math.ceil((y+10)*factor))
                hi = min(image.height,math.floor((y+h*.55)*factor))
                assert hi>lo, ('Target must be onscreen',state)
                for py in range(lo,hi):
                    r,g,b = image.getpixel((px,py))
                    assert not (r>210 and b>210 and g<90), ('Exposed backing',label,phase,delay,px,py)
                checks += 1
            if qa and delay in (16,160,400):
                Path(qa).mkdir(parents=True,exist_ok=True)
                (Path(qa)/f'zoom-{label}-{phase}-{delay}.png').write_bytes(data)
        return state

    try:
        link.hover()
        for delay in [0,16,64,160,240,400]:
            page.wait_for_timeout(delay)
            end = sample('enter',delay)
        assert abs(end['scale']-zoom)<.0002, ('No hover zoom',end)
        assert any(rest+.0001<s['scale']<zoom-.0001 for s in samples), 'Zoom jumped instead of animating'
        checks += 2
        page.mouse.move(1,1)
        for delay in [16,80,160,240,400]:
            page.wait_for_timeout(delay)
            end = sample('leave',delay)
        assert abs(end['scale']-rest)<.0002, ('Zoom did not return',end)
        checks += 1
        # Reverse a transition before it finishes; edges must remain covered.
        link.hover();page.wait_for_timeout(110);sample('reverse-in',0)
        page.mouse.move(1,1);page.wait_for_timeout(50);sample('reverse-out',0)
        link.hover();page.wait_for_timeout(90);sample('reenter',0)
        page.mouse.move(1,1);page.wait_for_timeout(850)
        sample('settled',0)
    finally:
        if marker: marker.evaluate('el=>el.remove()')
    if qa:
        Path(qa).mkdir(parents=True,exist_ok=True)
        (Path(qa)/f'zoom-{label}.json').write_text(json.dumps(samples,indent=2))
    return checks


def check_static_mode(page, link, rest=1.0):
    """Touch/reduced-motion modes keep the normal crop and no transition."""
    link.locator('img').evaluate('el=>el.decode()')
    link.scroll_into_view_if_needed()
    link.hover()
    page.wait_for_timeout(100)
    state=link.evaluate(STATE)
    assert abs(state['scale']-rest)<.0002 and state['duration']==0, state
    assert min(state['cover'])>=.9, state
    return 2
