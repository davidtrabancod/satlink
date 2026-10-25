(() => {
  document.querySelectorAll('.sat-card-nav').forEach((nav) => {
    const toggle = nav.querySelector('.card-nav-toggle');
    const panel = nav.querySelector('.card-nav-panel');
    const label = nav.querySelector('.card-nav-toggle-label');
    if (!toggle || !panel) return;
    const setOpen = (open, restoreFocus = false) => {
      nav.dataset.open = String(open);
      toggle.setAttribute('aria-expanded', String(open));
      if (label) label.textContent = open ? 'Cerrar' : 'Menú';
      if (!open && restoreFocus) toggle.focus();
    };
    toggle.addEventListener('click', () => setOpen(nav.dataset.open !== 'true'));
    nav.querySelectorAll('.card-nav-card').forEach((card) => card.addEventListener('click', () => setOpen(false)));
    document.addEventListener('pointerdown', (event) => { if (!nav.contains(event.target)) setOpen(false); });
    document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && nav.dataset.open === 'true') setOpen(false, true); });
    if (nav.closest('.card-nav-host')) {
      const cards = [...nav.querySelectorAll('.card-nav-card')];
      const syncCurrent = () => {
        const guides = document.getElementById('guias');
        const atGuides = location.hash === '#guias' || (guides && guides.getBoundingClientRect().top < window.innerHeight * .55);
        cards.forEach((card, index) => {
          const current = index === (atGuides ? 1 : 0);
          card.classList.toggle('is-current', current);
          if (current) card.setAttribute('aria-current', atGuides ? 'location' : 'page');
          else card.removeAttribute('aria-current');
        });
      };
      let scrollFrame = 0;
      window.addEventListener('scroll', () => {
        if (scrollFrame) return;
        scrollFrame = requestAnimationFrame(() => { scrollFrame = 0; syncCurrent(); });
      }, { passive: true });
      syncCurrent();
    }
  });
})();
