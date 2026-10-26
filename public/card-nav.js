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

  const specularButtons = document.querySelectorAll('.card-nav-quick--radar');
  specularButtons.forEach((button) => {
    const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
    window.addEventListener('pointermove', (event) => {
      const rect = button.getBoundingClientRect();
      const width = Math.max(rect.width, 1);
      const height = Math.max(rect.height, 1);
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const dx = Math.max(rect.left - event.clientX, 0, event.clientX - rect.right);
      const dy = Math.max(rect.top - event.clientY, 0, event.clientY - rect.bottom);
      const distance = Math.hypot(dx, dy);
      const proximity = 250;
      const near = clamp(1 - distance / proximity, 0, 1);
      const intensity = .32 + .68 * near * near * (3 - 2 * near);
      const radius = Math.min(11, width / 2, height / 2);
      let edgeX = clamp(x, radius, width - radius);
      let edgeY = clamp(y, radius, height - radius);

      if (x >= 0 && x <= width && y >= 0 && y <= height) {
        const edges = [
          { distance: y, x: edgeX, y: radius },
          { distance: width - x, x: width - radius, y: edgeY },
          { distance: height - y, x: edgeX, y: height - radius },
          { distance: x, x: radius, y: edgeY }
        ].sort((a, b) => a.distance - b.distance);
        edgeX = edges[0].x;
        edgeY = edges[0].y;
      } else {
        edgeX = clamp(x, radius, width - radius);
        edgeY = clamp(y, radius, height - radius);
        if (x < radius) edgeX = radius;
        else if (x > width - radius) edgeX = width - radius;
        if (y < radius) edgeY = radius;
        else if (y > height - radius) edgeY = height - radius;
      }

      const angle = Math.atan2(edgeY - height / 2, edgeX - width / 2) * 180 / Math.PI + 90;
      button.style.setProperty('--sb-angle', `${angle}deg`);
      button.style.setProperty('--sb-x', `${clamp(x / width * 100, 0, 100)}%`);
      button.style.setProperty('--sb-y', `${clamp(y / height * 100, 0, 100)}%`);
      button.style.setProperty('--sb-light', intensity.toFixed(3));
    }, { passive: true });
  });
})();
