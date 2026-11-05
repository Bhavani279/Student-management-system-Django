(function () {
  // Dark-mode toggle (remembered in localStorage)
  var toggle = document.getElementById('themeToggle');
  if (toggle) toggle.addEventListener('click', function () {
    var next = document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-bs-theme', next);
    localStorage.setItem('theme', next);
  });

  // Highlight the current menu item
  document.querySelectorAll('.sidebar .nav-link').forEach(function (a) {
    var here = location.pathname;
    if (a.getAttribute('href') === here || (a.getAttribute('href') !== '/' && here.startsWith(a.getAttribute('href')))) a.classList.add('active');
  });

  // Show/hide password on login
  var pwToggle = document.getElementById('pwToggle');
  if (pwToggle) pwToggle.addEventListener('click', function () {
    var f = document.getElementById('pw');
    f.type = f.type === 'password' ? 'text' : 'password';
  });

  // Attendance: all present / all absent + live counter
  var boxes = document.querySelectorAll('.att-box');
  function count() {
    var el = document.getElementById('presentCount');
    if (!el) return;
    var on = Array.from(boxes).filter(function (b) { return b.checked; }).length;
    el.textContent = on + ' present, ' + (boxes.length - on) + ' absent';
  }
  document.querySelectorAll('[data-set-all]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      boxes.forEach(function (b) { b.checked = btn.dataset.setAll === '1'; });
      count();
    });
  });
  boxes.forEach(function (b) { b.addEventListener('change', count); });
  count();

  // Auto-dismiss success alerts (keep the ones that show passwords)
  setTimeout(function () {
    document.querySelectorAll('.alert-success').forEach(function (a) {
      if (a.textContent.indexOf('Temporary password') === -1) bootstrap.Alert.getOrCreateInstance(a).close();
    });
  }, 5000);
})();
