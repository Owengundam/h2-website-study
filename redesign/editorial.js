/* Native video fallback remains available without JavaScript. */
(() => {
  'use strict';
  const film = document.querySelector('.home-film');
  if (!film) return;
  const zh = document.documentElement.lang.startsWith('zh');
  const controls = document.querySelector('.film-controls');
  const toggle = document.querySelector('.film-toggle');
  const fullscreen = document.querySelector('.film-fullscreen');
  const message = document.querySelector('.film-message');
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const saveData = navigator.connection?.saveData;
  film.muted = true;
  film.defaultMuted = true;
  controls.hidden = false;
  const update = () => {
    toggle.textContent = film.paused ? (zh ? '播放影片' : 'Play film') : (zh ? '暂停影片' : 'Pause film');
    toggle.setAttribute('aria-label', toggle.textContent);
  };
  const play = async () => {
    try { await film.play(); message.hidden = true; }
    catch (_) { film.controls = true; }
    update();
  };
  toggle.addEventListener('click', () => { if (film.paused) play(); else film.pause(); });
  fullscreen.addEventListener('click', async () => {
    try {
      if (film.requestFullscreen) { film.controls = true; await film.requestFullscreen(); }
      else if (film.webkitEnterFullscreen) film.webkitEnterFullscreen();
    } catch (_) { film.controls = true; }
  });
  document.addEventListener('fullscreenchange', () => { film.controls = !!document.fullscreenElement; });
  ['play', 'pause', 'ended'].forEach(event => film.addEventListener(event, update));
  film.addEventListener('playing', () => { message.hidden = true; film.controls = !!document.fullscreenElement; });
  film.addEventListener('error', () => {
    message.textContent = zh ? '影片暂时未能载入。' : 'The film could not load just now. ';
    const link = document.createElement('a');
    link.href = film.currentSrc || film.src;
    link.textContent = zh ? '打开原版影片 ↗' : 'Open the original film ↗';
    link.target = '_blank'; link.rel = 'noopener';
    message.append(document.createElement('br'), link); message.hidden = false;
    film.controls = true; update();
  });
  if (reduced.matches || saveData) { film.autoplay = false; film.pause(); }
  else play();
  reduced.addEventListener('change', e => { if (e.matches) film.pause(); });
  let resume = false;
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { resume = !film.paused; film.pause(); }
    else if (resume && !reduced.matches && !saveData) { resume = false; play(); }
  });
  update();
})();
