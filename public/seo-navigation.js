(() => {
  const allowedViews = new Set(["tracker", "globe", "passes", "rf", "radar"]);
  let lastView = null;
  try { lastView = window.sessionStorage.getItem("satlinkActiveView"); } catch (_) {}
  if (!allowedViews.has(lastView)) return;
  const returnUrl = `/?view=${encodeURIComponent(lastView)}`;
  document.querySelectorAll("[data-console-return]").forEach((link) => { link.href = returnUrl; });
})();
