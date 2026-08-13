(function initTrackMenu() {
  const menuBtn = document.getElementById('page-menu-btn');
  const overlay = document.getElementById('sections-overlay');
  const closeBtn = document.getElementById('sections-overlay-close');
  if (!menuBtn || !overlay) return;

  let lastFocus = null;

  function openMenu() {
    if (overlay.classList.contains('is-open')) return;
    lastFocus = document.activeElement;
    overlay.classList.add('is-open');
    overlay.setAttribute('aria-hidden', 'false');
    menuBtn.setAttribute('aria-expanded', 'true');
    document.body.classList.add('has-overlay-open');
    (closeBtn || overlay.querySelector('a, button')).focus();
  }

  function closeMenu() {
    if (!overlay.classList.contains('is-open')) return;
    overlay.classList.remove('is-open');
    overlay.setAttribute('aria-hidden', 'true');
    menuBtn.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('has-overlay-open');
    if (lastFocus && typeof lastFocus.focus === 'function') lastFocus.focus();
  }

  menuBtn.addEventListener('click', openMenu);
  if (closeBtn) closeBtn.addEventListener('click', closeMenu);
  overlay.addEventListener('click', (event) => {
    if (event.target === overlay) closeMenu();
  });
  overlay.querySelectorAll('.sections-overlay-link').forEach((link) => {
    link.addEventListener('click', closeMenu);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeMenu();
  });
})();
