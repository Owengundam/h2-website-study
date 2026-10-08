/* Clear over the landing image; opaque only once the header reaches body copy. */
(() => {
  'use strict';
  const header = document.querySelector('.studio-homepage .site-header');
  const hero = document.querySelector('.studio-landing');
  if (!header || !hero) return;
  let queued = false;
  const update = () => {
    header.classList.toggle('is-past-hero', hero.getBoundingClientRect().bottom <= header.offsetHeight);
    queued = false;
  };
  const schedule = () => { if (!queued) { queued = true; requestAnimationFrame(update); } };
  addEventListener('scroll', schedule, {passive: true});
  addEventListener('resize', schedule, {passive: true});
  addEventListener('pageshow', schedule);
  update();
})();
