/* Theme switch (dark / light). Loaded in <head> so the saved theme is applied before first paint (no flash). */
(function () {
  var KEY = 'rcto-theme', root = document.documentElement;
  function saved() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function apply(t) {
    root.setAttribute('data-theme', t);
    var m = document.querySelector('meta[name="theme-color"]'); if (m) m.setAttribute('content', t === 'light' ? '#EAF4E1' : '#040C07');
    document.querySelectorAll('[data-theme-toggle]').forEach(function (b) {
      var next = t === 'light' ? 'dark' : 'light';
      b.setAttribute('aria-label', 'Switch to ' + next + ' theme'); b.setAttribute('title', 'Switch to ' + next + ' theme');
    });
  }
  apply(saved() === 'light' ? 'light' : 'dark');
  document.addEventListener('DOMContentLoaded', function () {
    apply(root.getAttribute('data-theme'));
    document.querySelectorAll('[data-theme-toggle]').forEach(function (b) {
      b.addEventListener('click', function () {
        var t = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
        apply(t); try { localStorage.setItem(KEY, t); } catch (e) {}
      });
    });
  });
})();
