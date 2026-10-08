/* Native fallback and viewport-aware playback of the original H2 film. */
(() => {
  'use strict';
  const film = document.querySelector('.home-film');
  if (!film) return;
  const scope = film.closest('.home-cinema');
  const controls = scope?.querySelector('.film-controls');
  const toggle = scope?.querySelector('.film-toggle');
  const fullscreen = scope?.querySelector('.film-fullscreen');
  const message = scope?.querySelector('.film-message');
  if (!controls || !toggle || !fullscreen || !message) return;
  const zh = document.documentElement.lang.startsWith('zh');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const saveData = !!navigator.connection?.saveData;
  const pictureViewport = !!scope.closest('.studio-work-film');
  let visible = false;
  let userPaused = false;
  film.muted = true;
  film.defaultMuted = true;
  film.autoplay = false;
  controls.hidden = false;
  // This particular source embeds a centred 16:9 picture in a square export.
  // CSS hides only those black margins. Do not reset the viewport to videoWidth /
  // videoHeight: that would reintroduce the source's padding after metadata loads.
  const update = () => {
    toggle.textContent = film.paused ? (zh ? '播放影片' : 'Play film') : (zh ? '暂停影片' : 'Pause film');
    toggle.setAttribute('aria-label', toggle.textContent);
  };
  const play = async () => {
    try { await film.play(); message.hidden = true; }
    catch (_) { film.controls = true; }
    update();
  };
  const autoplay = () => {
    if (visible && !document.hidden && !userPaused && !reduced.matches && !saveData) play();
    else film.pause();
  };
  toggle.addEventListener('click', () => {
    if (film.paused) { userPaused = false; play(); }
    else { userPaused = true; film.pause(); }
  });
  fullscreen.addEventListener('click', async () => {
    try {
      const target = pictureViewport ? scope : film;
      if (target.requestFullscreen) { film.controls = true; await target.requestFullscreen(); }
      else if (film.webkitEnterFullscreen) film.webkitEnterFullscreen();
    } catch (_) { film.controls = true; }
  });
  document.addEventListener('fullscreenchange', () => { film.controls = !!document.fullscreenElement; });
  ['play', 'pause', 'ended'].forEach(event => film.addEventListener(event, update));
  film.addEventListener('playing', () => {
    if ((!visible || document.hidden) && !document.fullscreenElement) { film.pause(); return; }
    message.hidden = true; film.controls = !!document.fullscreenElement;
  });
  film.addEventListener('error', () => {
    message.textContent = zh ? '影片暂时未能载入。' : 'The film could not load just now. ';
    const link = document.createElement('a');
    link.href = film.currentSrc || film.src;
    link.textContent = zh ? '打开原版影片 ↗' : 'Open the original film ↗';
    link.target = '_blank'; link.rel = 'noopener';
    message.append(document.createElement('br'), link); message.hidden = false;
    film.controls = true; update();
  });
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(entries => {
      visible = entries[0].isIntersecting;
      if (!document.fullscreenElement) autoplay();
    }, {threshold: 0.15}).observe(film);
  } else {
    visible = true;
    autoplay();
  }
  reduced.addEventListener('change', autoplay);
  document.addEventListener('visibilitychange', autoplay);
  update();
})();
