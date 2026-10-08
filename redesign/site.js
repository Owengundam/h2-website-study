/* Progressive enhancement: all projects, text and links work without JavaScript. */
(() => {
  'use strict';
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => Array.from(root.querySelectorAll(s));
  const zh = document.documentElement.lang.startsWith('zh');
  const header = $('.site-header');
  const menu = $('.menu-toggle');
  function closeMenu() {
    header?.classList.remove('is-open');
    menu?.setAttribute('aria-expanded', 'false');
    if (menu) $('.menu-icon', menu).textContent = '+';
  }
  menu?.addEventListener('click', () => {
    const open = header.classList.toggle('is-open');
    menu.setAttribute('aria-expanded', String(open));
    $('.menu-icon', menu).textContent = open ? '−' : '+';
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && header?.classList.contains('is-open')) { closeMenu(); menu?.focus(); }
  });
  $$('.main-nav a').forEach(a => a.addEventListener('click', closeMenu));
  window.matchMedia('(min-width: 701px)').addEventListener('change', e => { if (e.matches) closeMenu(); });

  const grid = $('.project-grid');
  if (grid) {
    const cards = $$('.project-card', grid);
    const filters = $$('[data-filter]');
    const count = $('[data-project-count]');
    const empty = $('.no-results');
    function filter(category, updateUrl = true) {
      if (!filters.some(b => b.dataset.filter === category)) category = 'all';
      let visible = 0;
      cards.forEach(card => {
        card.hidden = category !== 'all' && card.dataset.category !== category;
        if (!card.hidden) visible++;
      });
      filters.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.filter === category)));
      if (count) count.textContent = String(visible).padStart(2, '0');
      $$('[data-filter-decoration]').forEach(el => { el.hidden = category !== 'all'; });
      if (empty) empty.hidden = visible > 0;
      if (updateUrl) {
        const url = new URL(location.href);
        if (category === 'all') url.searchParams.delete('filter');
        else url.searchParams.set('filter', category);
        history.replaceState(null, '', url);
      }
    }
    filters.forEach(button => button.addEventListener('click', () => filter(button.dataset.filter)));
    filter(new URLSearchParams(location.search).get('filter') || 'all', false);
    const viewButtons = $$('[data-view-button]');
    function setView(view) {
      view = view === 'index' ? 'index' : 'grid';
      grid.dataset.view = view;
      viewButtons.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.viewButton === view)));
      try { sessionStorage.setItem('h2-portfolio-view', view); } catch (_) { /* optional preference */ }
    }
    viewButtons.forEach(button => button.addEventListener('click', () => setView(button.dataset.viewButton)));
    try { setView(sessionStorage.getItem('h2-portfolio-view')); } catch (_) { setView('grid'); }
  }

  const dialog = $('.lightbox');
  const gallery = $$('a[data-lightbox]');
  let imageIndex = 0;
  let previousFocus = null;
  if (dialog && typeof dialog.showModal === 'function') {
    const image = $('.lightbox-image', dialog);
    const caption = $('.lightbox-caption', dialog);
    const counter = $('.lightbox-count', dialog);
    function show(index) {
      imageIndex = (index + gallery.length) % gallery.length;
      const link = gallery[imageIndex];
      image.src = link.href;
      image.alt = link.dataset.caption || $('img', link)?.alt || '';
      caption.textContent = image.alt;
      counter.textContent = `${imageIndex + 1} / ${gallery.length}`;
    }
    gallery.forEach((link, index) => link.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      previousFocus = link;
      show(index);
      dialog.showModal();
      document.body.style.overflow = 'hidden';
    }));
    $('[data-lightbox-close]', dialog).addEventListener('click', () => dialog.close());
    $('[data-lightbox-prev]', dialog).addEventListener('click', () => show(imageIndex - 1));
    $('[data-lightbox-next]', dialog).addEventListener('click', () => show(imageIndex + 1));
    dialog.addEventListener('keydown', event => {
      if (event.key === 'ArrowLeft') { event.preventDefault(); show(imageIndex - 1); }
      if (event.key === 'ArrowRight') { event.preventDefault(); show(imageIndex + 1); }
    });
    dialog.addEventListener('close', () => { document.body.style.overflow = ''; previousFocus?.focus(); });
  }

  let toastTimer;
  function toast(message) {
    let node = $('.toast');
    if (!node) { node = document.createElement('div'); node.className = 'toast'; node.setAttribute('role', 'status'); document.body.append(node); }
    node.textContent = message;
    node.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { node.hidden = true; }, 3500);
  }
  $$('[data-share]').forEach(button => button.addEventListener('click', async () => {
    const url = new URL(location.href); url.hash = '';
    try {
      if (navigator.share && window.matchMedia('(max-width:700px)').matches) await navigator.share({title: document.title, url: url.href});
      else if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(url.href);
        toast(zh ? '项目链接已复制' : 'Project link copied');
      } else {
        window.prompt(zh ? '复制项目链接' : 'Copy project link', url.href);
      }
    } catch (error) {
      if (error.name !== 'AbortError') window.prompt(zh ? '复制项目链接' : 'Copy project link', url.href);
    }
  }));

  const back = $('.back-top');
  if (back) {
    const update = () => back.classList.toggle('visible', window.scrollY > 700);
    window.addEventListener('scroll', update, {passive:true}); update();
  }
  // Never hide the content until a functioning observer is installed.
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.remove('pending'); observer.unobserve(entry.target); }
    }), {rootMargin:'0px 0px 100px 0px', threshold:0.02});
    document.documentElement.classList.add('enhanced');
    $$('[data-reveal]').forEach(element => {
      if (element.getBoundingClientRect().top > innerHeight) { element.classList.add('pending'); observer.observe(element); }
    });
  }
})();
