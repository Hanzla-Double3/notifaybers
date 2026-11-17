/* Theme bootstrap. Loaded synchronously in <head> so the right theme is
   applied before first paint (no flash). Preference is per-device. */
(function () {
  var KEY = "nfb-theme"; // "light" | "dark"; absent = follow the system
  var COLORS = { light: "#f4f5fa", dark: "#090a0f" };
  var mq = window.matchMedia ? window.matchMedia("(prefers-color-scheme: light)") : null;

  function stored() {
    try {
      var v = localStorage.getItem(KEY);
      return v === "light" || v === "dark" ? v : "system";
    } catch (e) {
      return "system";
    }
  }

  function resolve(mode) {
    if (mode === "system") return mq && mq.matches ? "light" : "dark";
    return mode;
  }

  function apply() {
    var theme = resolve(stored());
    document.documentElement.setAttribute("data-theme", theme);
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", COLORS[theme]);
  }

  window.NFBTheme = {
    get: stored,
    set: function (mode) {
      try {
        if (mode === "light" || mode === "dark") localStorage.setItem(KEY, mode);
        else localStorage.removeItem(KEY);
      } catch (e) {}
      apply();
    },
  };

  if (mq) {
    if (mq.addEventListener) mq.addEventListener("change", apply);
    else if (mq.addListener) mq.addListener(apply);
  }
  window.addEventListener("storage", function (e) {
    if (e.key === KEY) apply();
  });
  apply();
})();
