/**
 * Single dark-mode component for all incident-ui pages.
 *
 * Usage (every page, in <head> before CSS):
 *   <script src="/theme.js"></script>
 *   <link rel="stylesheet" href="/theme.css" />
 */
(function () {
  var STORAGE_KEY = 'agent-theme';
  var CHANGE_EVENT = 'incident-ui:theme-change';
  var TOGGLE_ID = 'dark-mode-toggle';

  function getTheme() {
    return document.documentElement.getAttribute('data-theme') || 'dark';
  }

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {}
    window.dispatchEvent(new CustomEvent(CHANGE_EVENT, { detail: { theme: theme } }));
  }

  function toggleTheme() {
    setTheme(getTheme() === 'dark' ? 'light' : 'dark');
  }

  function syncToggle(button) {
    var theme = getTheme();
    button.textContent = theme === 'dark' ? '☀️' : '🌙';
    button.title = 'Switch to ' + (theme === 'dark' ? 'light' : 'dark') + ' mode';
    button.setAttribute('aria-label', 'Toggle color theme');
  }

  function mountToggle() {
    var button = document.getElementById(TOGGLE_ID);
    if (!button) {
      button = document.createElement('button');
      button.type = 'button';
      button.id = TOGGLE_ID;
      document.body.appendChild(button);
    }

    syncToggle(button);

    if (!button.dataset.mounted) {
      button.dataset.mounted = '1';
      button.addEventListener('click', function () {
        toggleTheme();
        syncToggle(button);
      });
      window.addEventListener(CHANGE_EVENT, function () {
        syncToggle(button);
      });
    }

    document.body.classList.add('has-dark-mode-toggle');
  }

  // Apply theme before first paint.
  try {
    var saved = localStorage.getItem(STORAGE_KEY);
    var theme =
      saved ||
      (window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: light)').matches
        ? 'light'
        : 'dark');
    document.documentElement.setAttribute('data-theme', theme);
  } catch (e) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }

  // Mount the single fixed top-right toggle once DOM is ready.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mountToggle);
  } else {
    mountToggle();
  }
})();
