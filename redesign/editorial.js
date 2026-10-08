/* Minimal icon controls and viewport-aware playback of the original H2 film.
   Native controls remain in the HTML as the no-JavaScript fallback. */
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
  let revealTimer;
  film.muted = true;
  film.defaultMuted = true;
  film.autoplay = false;

  // Fixed SVG paths only: the visible interface is two white icons, not labels.
  const icons = {
    play: '<path d="M8 5v14l11-7z" fill="currentColor" stroke="none"/>',
    pause: '<path d="M8 5v14M16 5v14" stroke="currentColor" stroke-width="3"/>',
    expand: '<path d="M9 4H4v5m11-5h5v5M4 15v5h5m11-5v5h-5" stroke="currentColor" stroke-width="1.8"/>',
    collapse: '<path d="M4 9h5V4m6 0v5h5M9 20v-5H4m11 5v-5h5" stroke="currentColor" stroke-width="1.8"/>'
  };
  const setIcon = (button, name, label) => {
    if (button.dataset.icon !== name) {
      button.innerHTML = '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" aria-hidden="true" focusable="false">' + icons[name] + '</svg>';
      button.dataset.icon = name;
    }
    button.setAttribute('aria-label', label);
    button.removeAttribute('title');
  };
  const isFullscreen = () => document.fullscreenElement === scope || document.fullscreenElement === film || !!film.webkitDisplayingFullscreen;
  const update = () => {
    setIcon(toggle, film.paused ? 'play' : 'pause', film.paused ? (zh ? '播放影片' : 'Play film') : (zh ? '暂停影片' : 'Pause film'));
    setIcon(fullscreen, isFullscreen() ? 'collapse' : 'expand', isFullscreen() ? (zh ? '退出全屏' : 'Exit fullscreen') : (zh ? '全屏播放' : 'Fullscreen'));
    fullscreen.setAttribute('aria-pressed', String(isFullscreen()));
  };
  const revealBriefly = () => {
    scope.classList.add('controls-revealed');
    clearTimeout(revealTimer);
    revealTimer = setTimeout(() => scope.classList.remove('controls-revealed'), 2800);
  };
  const play = async () => {
    try {
      await film.play();
      message.hidden = true;
      scope.classList.remove('needs-play');
    } catch (error) {
      // Autoplay refusal must not restore the browser's boxed control bar.
      if (error.name !== 'AbortError') scope.classList.add('needs-play');
    }
    update();
  };
  const autoplay = () => {
    if ((visible || isFullscreen()) && !document.hidden && !userPaused && !reduced.matches && !saveData) play();
    else film.pause();
  };
  toggle.addEventListener('click', () => {
    if (film.paused) { userPaused = false; play(); }
    else { userPaused = true; film.pause(); }
    update();
  });
  fullscreen.addEventListener('click', async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else if (film.webkitDisplayingFullscreen && film.webkitExitFullscreen) film.webkitExitFullscreen();
      else {
        const target = pictureViewport ? scope : film;
        if (target.requestFullscreen) await target.requestFullscreen();
        else if (film.webkitEnterFullscreen) film.webkitEnterFullscreen();
      }
    } catch (_) { revealBriefly(); }
    update();
  });
  document.addEventListener('fullscreenchange', () => { film.controls = false; update(); });
  ['webkitbeginfullscreen', 'webkitendfullscreen'].forEach(event => film.addEventListener(event, update));
  ['play', 'pause', 'ended'].forEach(event => film.addEventListener(event, update));
  film.addEventListener('playing', () => {
    if ((!visible || document.hidden) && !isFullscreen()) { film.pause(); return; }
    message.hidden = true;
    scope.classList.remove('needs-play');
    film.controls = false;
    update();
  });
  film.addEventListener('error', () => {
    message.textContent = zh ? '影片暂时未能载入。' : 'The film could not load just now. ';
    const link = document.createElement('a');
    link.href = film.currentSrc || film.src;
    link.textContent = zh ? '打开原版影片 ↗' : 'Open the original film ↗';
    link.target = '_blank'; link.rel = 'noopener';
    message.append(document.createElement('br'), link);
    message.hidden = false;
    update();
  });
  // Tap anywhere on touch screens to reveal the controls, without pausing the film.
  scope.addEventListener('pointerup', event => {
    if (event.pointerType === 'touch' || event.pointerType === 'pen') revealBriefly();
  });
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(entries => {
      visible = entries[0].isIntersecting;
      if (!isFullscreen()) autoplay();
    }, {threshold: 0.15}).observe(scope);
  } else {
    visible = true;
    autoplay();
  }
  reduced.addEventListener('change', autoplay);
  document.addEventListener('visibilitychange', autoplay);
  update();
  controls.setAttribute('role', 'group');
  controls.setAttribute('aria-label', zh ? '影片控制' : 'Film controls');
  fullscreen.hidden = !(scope.requestFullscreen || film.requestFullscreen || film.webkitEnterFullscreen);
  // Enhance only after the controls are wired; CSS never changes the film geometry.
  scope.setAttribute('data-icon-controls', '');
  film.controls = false;
  controls.hidden = false;
})();
