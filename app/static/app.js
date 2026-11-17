// ==========================================================================
// Notifaybers — Core Client Application Logic & SPA Router
// ==========================================================================

// ---------- SVG Icon Helpers ----------
const ICONS = {
  bell: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>`,
  clock: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
  calendar: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`,
  repeat: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>`,
  zap: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
  webhook: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 16.98h-5.99c-1.1 0-1.95.94-2.48 1.9A4 4 0 0 1 2 17c0-2.21 1.79-4 4-4h7"/><path d="M6 13V7a4 4 0 0 1 4-4h4"/><circle cx="18" cy="7" r="3"/><circle cx="18" cy="17" r="3"/><circle cx="6" cy="17" r="3"/></svg>`,
  send: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>`,
  edit: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`,
  trash: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>`,
  link: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>`,
  check: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
  copy: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`,
  close: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
  devicePhone: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>`,
  deviceTablet: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>`,
  deviceLaptop: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="2" y1="20" x2="22" y2="20"/></svg>`,
  deviceDesktop: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>`,
  key: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2l-2 2m-1.5 1.5L16 7l-4 4-2-2-4 4 1.5 1.5L6 16l-4 4 4-4 1.5 1.5 1.5-1.5 4-4-2-2 4-4 1.5 1.5 1.5-1.5"/></svg>`,
  spinner: `<svg class="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>`,
  activity: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>`,
  sparkle: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>`,
};

// ---------- API & Network Helpers ----------

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = formatApiErrorDetail(data && data.detail, detail);
    } catch (e) { }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

function formatApiErrorDetail(detail, fallback) {
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail.length) {
    // FastAPI/Pydantic 422 validation errors: [{loc, msg, type}, ...]
    return detail
      .map((d) => {
        if (d && typeof d.msg === "string") {
          const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : "";
          return field ? `${field}: ${d.msg}` : d.msg;
        }
        return typeof d === "string" ? d : JSON.stringify(d);
      })
      .join("; ");
  }
  if (detail && typeof detail === "object") {
    try {
      return JSON.stringify(detail);
    } catch (e) {
      return fallback;
    }
  }
  return fallback;
}

function toast(message, iconSvg = ICONS.check) {
  const root = document.getElementById("toast-root");
  if (!root) return;
  const el = document.createElement("div");
  el.className = "toast";
  el.innerHTML = `<span class="toast-icon">${iconSvg}</span><span>${escapeHtml(message)}</span>`;
  root.appendChild(el);

  setTimeout(() => {
    el.classList.add("toast-out");
    setTimeout(() => el.remove(), 220);
  }, 2600);
}

function closeModal() {
  const root = document.getElementById("modal-root");
  if (root) root.innerHTML = "";
  document.removeEventListener("keydown", handleModalKeydown);
}

function handleModalKeydown(e) {
  if (e.key === "Escape") closeModal();
}

function openModal(innerHtml, title = "") {
  const root = document.getElementById("modal-root");
  if (!root) return;

  const headerHtml = title ? `
    <div class="modal-header">
      <div class="modal-title">${escapeHtml(title)}</div>
      <button class="modal-close-btn" onclick="closeModal()" title="Close">
        ${ICONS.close}
      </button>
    </div>` : "";

  root.innerHTML = `
    <div class="modal-overlay" id="modal-overlay">
      <div class="modal">
        <span class="modal-drag-handle"></span>
        ${headerHtml}
        ${innerHtml}
      </div>
    </div>`;

  document.getElementById("modal-overlay").addEventListener("click", (e) => {
    if (e.target.id === "modal-overlay") closeModal();
  });
  document.addEventListener("keydown", handleModalKeydown);
}

function timeAgo(iso) {
  if (!iso) return "";
  const dateStr = iso.endsWith("Z") ? iso : iso + "Z";
  const date = new Date(dateStr);
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 45) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function formatDateTime(iso) {
  if (!iso) return "";
  const dateStr = iso.endsWith("Z") ? iso : iso + "Z";
  return new Date(dateStr).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function escapeHtml(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)));
}

function arrayBufferToBase64Url(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  bytes.forEach((b) => (binary += String.fromCharCode(b)));
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function isIOS() {
  return (
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
  );
}

function isStandalone() {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true
  );
}

// Copy to clipboard helper with fallback
async function copyToClipboard(text, btnElement, successText = "Copied!") {
  try {
    await navigator.clipboard.writeText(text);
  } catch (e) {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
  }
  if (btnElement) {
    const originalHtml = btnElement.innerHTML;
    btnElement.innerHTML = `${ICONS.check} <span>${successText}</span>`;
    setTimeout(() => {
      btnElement.innerHTML = originalHtml;
    }, 2000);
  }
}

// Webhook snippet copy
function baseUrl() {
  return (document.body.dataset.baseUrl || window.location.origin).replace(/\/$/, "");
}

function copyWebhookSnippet() {
  const curlCmd = `curl -X POST ${baseUrl()}/api/webhook \\
  -H "X-API-Key: YOUR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"title": "Deploy Finished", "body": "prod is live", "url": "https://..."}'`;
  copyToClipboard(curlCmd, document.getElementById("copy-curl-btn"), "Copied cURL!");
  toast("cURL snippet copied to clipboard");
}

// ---------- Notifications & Service Worker Flow ----------

async function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return null;
  return navigator.serviceWorker.register("/sw.js", { scope: "/" });
}

async function getExistingSubscription() {
  if (!("serviceWorker" in navigator)) return null;
  const reg = await Promise.race([
    navigator.serviceWorker.ready,
    new Promise((resolve) => setTimeout(() => resolve(null), 5000)),
  ]);
  if (!reg) return null;
  return reg.pushManager.getSubscription();
}

async function needsNotificationSetup() {
  if (!("Notification" in window) || !("serviceWorker" in navigator) || !("PushManager" in window)) {
    return false;
  }
  if (Notification.permission === "denied") return false;
  const sub = await getExistingSubscription();
  return !sub || Notification.permission !== "granted";
}

async function subscribeForPush() {
  const { publicKey } = await api("/api/vapid-public-key");
  if (!publicKey) throw new Error("Server has no VAPID key configured yet.");

  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("Push permission was not granted.");

  const reg = await navigator.serviceWorker.ready;
  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    });
  }

  await api("/api/subscriptions", {
    method: "POST",
    body: JSON.stringify({
      endpoint: sub.endpoint,
      keys: {
        p256dh: arrayBufferToBase64Url(sub.getKey("p256dh")),
        auth: arrayBufferToBase64Url(sub.getKey("auth")),
      },
      user_agent: navigator.userAgent,
    }),
  });
}

function renderEnableModal() {
  if (isIOS() && !isStandalone()) {
    openModal(`
      <p style="color:var(--text-secondary); line-height:1.5; font-size:14px;">
        iOS Web Push notifications require Notifaybers to be installed on your Home Screen.
      </p>
      <div style="background:var(--surface-input); border:1px solid var(--border); border-radius:12px; padding:14px; display:flex; flex-direction:column; gap:8px; font-size:13px; color:var(--text);">
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="background:var(--accent-light); color:var(--accent); width:20px; height:20px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:11px;">1</span>
          <span>Tap the <strong>Share</strong> button in Safari</span>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="background:var(--accent-light); color:var(--accent); width:20px; height:20px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:11px;">2</span>
          <span>Select <strong>"Add to Home Screen"</strong></span>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="background:var(--accent-light); color:var(--accent); width:20px; height:20px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:11px;">3</span>
          <span>Open the app from your Home Screen to enable alerts</span>
        </div>
      </div>
      <div class="modal-actions">
        <button class="btn-primary" onclick="closeModal()">Understood</button>
      </div>
    `, "Add to Home Screen First");
    return;
  }

  openModal(`
    <p style="color:var(--text-secondary); line-height:1.5; font-size:14px;">
      Allow Notifaybers to deliver real-time notifications, webhook updates, and scheduled reminders directly to this device.
    </p>
    <div class="modal-actions">
      <button class="btn-ghost" onclick="closeModal()">Later</button>
      <button class="btn-primary" id="enable-notif-confirm">
        <span id="enable-notif-btn-text">Enable Notifications</span>
      </button>
    </div>
  `, "Enable Push Notifications");

  document.getElementById("enable-notif-confirm").addEventListener("click", async (e) => {
    const btn = document.getElementById("enable-notif-confirm");
    const btnText = document.getElementById("enable-notif-btn-text");
    btn.disabled = true;
    btnText.textContent = "Requesting permission...";
    try {
      await subscribeForPush();
      closeModal();
      toast("Push notifications enabled!");
      const banner = document.getElementById("notif-banner");
      if (banner) banner.classList.add("hidden");
      if (typeof loadDevices === "function") loadDevices();
    } catch (err) {
      toast(err.message, ICONS.bell);
      btn.disabled = false;
      btnText.textContent = "Enable Notifications";
    }
  });
}

async function checkNotificationPrompt() {
  await registerServiceWorker();
  const needsSetup = await needsNotificationSetup();
  const banner = document.getElementById("notif-banner");

  if (needsSetup) {
    if (banner) {
      banner.classList.remove("hidden");
      const bannerBtn = document.getElementById("notif-banner-btn");
      if (bannerBtn && !bannerBtn.dataset.bound) {
        bannerBtn.dataset.bound = "1";
        bannerBtn.addEventListener("click", renderEnableModal);
      }
    }
    if (!sessionStorage.getItem("notif_modal_shown")) {
      sessionStorage.setItem("notif_modal_shown", "1");
      renderEnableModal();
    }
  } else if (banner) {
    banner.classList.add("hidden");
  }
}

// ==========================================================================
// SPA Router & Navigation
// ==========================================================================

const SPA_ROUTES = {
  "/": "dashboard",
  "/reminders": "reminders",
  "/watchdogs": "watchdogs",
  "/settings": "settings",
};

const ROUTE_INDICES = {
  "/": 0,
  "/reminders": 1,
  "/watchdogs": 2,
  "/settings": 3,
};

let currentRouteIndex = ROUTE_INDICES[normalizePath(window.location.pathname)] ?? 0;

function normalizePath(pathname) {
  if (!pathname || pathname === "") return "/";
  if (pathname.length > 1 && pathname.endsWith("/")) {
    return pathname.slice(0, -1);
  }
  return pathname;
}

function updateNavIndicators(cleanPath) {
  // Mobile floating dock indicator
  const mobileContainer = document.querySelector(".tabbar-container");
  const mobileIndicator = document.getElementById("tabbar-indicator");
  const activeTab = document.querySelector(`.tab[data-path="${cleanPath}"]`);

  if (mobileContainer && mobileIndicator && activeTab) {
    const containerRect = mobileContainer.getBoundingClientRect();
    const tabRect = activeTab.getBoundingClientRect();
    const leftOffset = tabRect.left - containerRect.left;
    const width = tabRect.width;

    mobileIndicator.style.opacity = "1";
    mobileIndicator.style.transform = `translateX(${leftOffset}px)`;
    mobileIndicator.style.width = `${width}px`;
  }

  // Desktop topbar indicator
  const desktopContainer = document.querySelector(".desktop-nav");
  const desktopIndicator = document.getElementById("desktop-nav-indicator");
  const activeNavItem = document.querySelector(`.nav-item[data-path="${cleanPath}"]`);

  if (desktopContainer && desktopIndicator && activeNavItem) {
    const containerRect = desktopContainer.getBoundingClientRect();
    const itemRect = activeNavItem.getBoundingClientRect();
    const leftOffset = itemRect.left - containerRect.left;
    const width = itemRect.width;

    desktopIndicator.style.opacity = "1";
    desktopIndicator.style.transform = `translateX(${leftOffset}px)`;
    desktopIndicator.style.width = `${width}px`;
  }
}

// Window resize updates indicator positions
window.addEventListener("resize", () => {
  const currentPath = normalizePath(window.location.pathname);
  if (SPA_ROUTES[currentPath]) {
    updateNavIndicators(currentPath);
  }
});

function navigateTo(path, push = true) {
  let cleanPath = normalizePath(path);
  if (cleanPath === "/watchdogs" && !watchdogsEnabled()) {
    // Watchdogs is an opt-in feature (Settings > Features); send people to Settings.
    cleanPath = "/settings";
    if (!push) history.replaceState({ path: cleanPath }, "", cleanPath);
  }
  const viewName = SPA_ROUTES[cleanPath] || "dashboard";
  const newIndex = ROUTE_INDICES[cleanPath] ?? 0;
  const isMovingRight = newIndex > currentRouteIndex;
  const isMovingLeft = newIndex < currentRouteIndex;
  const isInitial = !document.querySelector(".spa-view.active-view, .spa-view.slide-from-right, .spa-view.slide-from-left");

  currentRouteIndex = newIndex;

  if (push && window.location.pathname !== cleanPath) {
    history.pushState({ path: cleanPath }, "", cleanPath);
  }

  // Update document title
  const titles = {
    dashboard: "Notifaybers — Inbox",
    reminders: "Notifaybers — Reminders",
    watchdogs: "Notifaybers — Watchdogs",
    settings: "Notifaybers — Settings",
  };
  document.title = titles[viewName] || "Notifaybers";

  // Update tabs & desktop navigation active indicator
  document.querySelectorAll(".tab, .nav-item").forEach((el) => {
    if (el.dataset.path === cleanPath) {
      el.classList.add("active");
    } else {
      el.classList.remove("active");
    }
  });

  // Smoothly move the bottom & desktop nav sliding indicator
  requestAnimationFrame(() => {
    updateNavIndicators(cleanPath);
  });

  // Switch SPA views with left/right directional animation
  document.querySelectorAll(".spa-view").forEach((view) => {
    view.classList.remove("active-view", "slide-from-right", "slide-from-left");
    if (view.id === `view-${viewName}`) {
      view.classList.remove("hidden-view");
      if (isInitial) {
        view.classList.add("active-view");
      } else if (isMovingRight) {
        view.classList.add("slide-from-right");
      } else if (isMovingLeft) {
        view.classList.add("slide-from-left");
      } else {
        view.classList.add("active-view");
      }
    } else {
      view.classList.add("hidden-view");
    }
  });

  // Scroll to top of page
  window.scrollTo({ top: 0, behavior: "instant" });

  // Load/refresh view data
  if (viewName === "dashboard") {
    loadHistory();
  } else if (viewName === "reminders") {
    loadReminders();
  } else if (viewName === "watchdogs") {
    loadWatchdogs();
  } else if (viewName === "settings") {
    loadSettings();
  }
}

// Intercept clicks on links for SPA navigation
document.addEventListener("click", (e) => {
  const link = e.target.closest("a[data-path], a[href='/'], a[href='/reminders'], a[href='/watchdogs'], a[href='/settings'], .brand-link");
  if (!link) return;

  let href = link.getAttribute("href") || link.dataset.path;
  if (!href) return;

  if (link.classList.contains("brand-link")) {
    href = "/";
  }

  const cleanPath = normalizePath(href);
  if (SPA_ROUTES[cleanPath]) {
    e.preventDefault();
    navigateTo(cleanPath);
  }
});

// Handle browser back and forward history buttons
window.addEventListener("popstate", () => {
  navigateTo(window.location.pathname, false);
});

// Setup common event listeners once
function setupCommonEventListeners() {
  // Test push button
  const testBtn = document.getElementById("test-push-btn");
  if (testBtn && !testBtn.dataset.bound) {
    testBtn.dataset.bound = "1";
    testBtn.addEventListener("click", async () => {
      testBtn.disabled = true;
      const originalText = testBtn.innerHTML;
      testBtn.innerHTML = `${ICONS.spinner} <span>Sending...</span>`;
      try {
        const res = await api("/api/test-push", { method: "POST" });
        if (res.status === "sent") {
          toast("Test push notification delivered!");
        } else if (res.status === "no_subscriptions") {
          toast("No device subscribed yet. Enable push first.", ICONS.bell);
        } else {
          toast(`Push status: ${res.status}`);
        }
        await loadHistory();
      } catch (err) {
        toast(err.message);
      } finally {
        testBtn.disabled = false;
        testBtn.innerHTML = originalText;
      }
    });
  }

  // Add reminder button
  const addReminderBtn = document.getElementById("add-reminder-btn");
  if (addReminderBtn && !addReminderBtn.dataset.bound) {
    addReminderBtn.dataset.bound = "1";
    addReminderBtn.addEventListener("click", () => openReminderModal());
  }

  // Add API key button
  const addKeyBtn = document.getElementById("add-key-btn");
  if (addKeyBtn && !addKeyBtn.dataset.bound) {
    addKeyBtn.dataset.bound = "1";
    addKeyBtn.addEventListener("click", openCreateKeyModal);
  }

  // Add watchdog button
  const addWatchdogBtn = document.getElementById("add-watchdog-btn");
  if (addWatchdogBtn && !addWatchdogBtn.dataset.bound) {
    addWatchdogBtn.dataset.bound = "1";
    addWatchdogBtn.addEventListener("click", () => openCreateWatchdogModal());
  }

  // AI assistant triggers
  const openAiBtn = document.getElementById("ai-chat-btn") || document.getElementById("open-ai-chat-btn");
  if (openAiBtn && !openAiBtn.dataset.bound) {
    openAiBtn.dataset.bound = "1";
    openAiBtn.addEventListener("click", () => openAiChatModal());
  }

  const askAiReminderBtn = document.getElementById("ask-ai-reminder-btn");
  if (askAiReminderBtn && !askAiReminderBtn.dataset.bound) {
    askAiReminderBtn.dataset.bound = "1";
    askAiReminderBtn.addEventListener("click", () => openAiChatModal());
  }

  // Timezone select listener
  const timezoneSelect = document.getElementById("timezone-select");
  if (timezoneSelect && !timezoneSelect.dataset.bound) {
    timezoneSelect.dataset.bound = "1";
    timezoneSelect.addEventListener("change", async () => {
      try {
        await api("/api/me/timezone", { method: "PUT", body: JSON.stringify({ timezone: timezoneSelect.value }) });
        toast("Timezone preference saved!");
      } catch (err) {
        toast(err.message);
      }
    });
  }
}

// ==========================================================================
// Pull to Refresh (Native iOS / Mobile PWA Feel)
// ==========================================================================

function initPullToRefresh() {
  const indicator = document.getElementById("pull-refresh-indicator");
  const meter = document.getElementById("pull-meter");
  const arrow = document.getElementById("pull-arrow");
  const check = document.getElementById("pull-check");
  const content = document.querySelector(".content");

  if (!indicator) return;

  // Circle radius is 13, circumference = 2 * PI * 13 ≈ 81.68
  const CIRCUMFERENCE = 81.68;
  const PULL_THRESHOLD = 68;
  const MAX_PULL = 110;
  const START_Y = -54; // tucked directly behind sticky glass topbar
  const RESTING_Y = 18; // rests cleanly just below topbar border without displacing content

  let touchStartY = 0;
  let touchStartX = 0;
  let isPulling = false;
  let isRefreshing = false;
  let pullDistance = 0;
  let hasCrossedThreshold = false;

  // Set initial SVG meter dashoffset
  if (meter) {
    meter.style.strokeDasharray = `${CIRCUMFERENCE}`;
    meter.style.strokeDashoffset = `${CIRCUMFERENCE}`;
  }

  function updatePullVisuals(dist) {
    const progress = Math.min(1, dist / PULL_THRESHOLD);

    // Continuous, smooth emergence from behind topbar without sudden jumps
    let translateY;
    if (dist <= PULL_THRESHOLD) {
      translateY = START_Y + (RESTING_Y - START_Y) * progress;
    } else {
      const extra = (dist - PULL_THRESHOLD) * 0.16;
      translateY = RESTING_Y + extra;
    }

    indicator.style.transition = "none";
    indicator.style.opacity = Math.min(1, progress * 1.35).toString();
    indicator.style.transform = `translate(-50%, ${translateY}px)`;

    // Update circular progress meter
    if (meter) {
      const offset = CIRCUMFERENCE * (1 - progress);
      meter.style.strokeDashoffset = `${offset}`;
    }

    // Toggle threshold reached class (flips arrow 180° in CSS)
    if (dist >= PULL_THRESHOLD) {
      if (!indicator.classList.contains("threshold-reached")) {
        indicator.classList.add("threshold-reached");
        if (!hasCrossedThreshold) {
          hasCrossedThreshold = true;
          if (navigator.vibrate) {
            try { navigator.vibrate(10); } catch (e) { }
          }
        }
      }
    } else {
      if (indicator.classList.contains("threshold-reached")) {
        indicator.classList.remove("threshold-reached");
        hasCrossedThreshold = false;
      }
    }
  }

  function snapToRefreshPosition() {
    indicator.classList.remove("threshold-reached");
    indicator.classList.add("is-refreshing");
    indicator.style.transition = "transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease";
    indicator.style.opacity = "1";
    indicator.style.transform = `translate(-50%, ${RESTING_Y}px)`;
  }

  function showSuccessAndReset() {
    indicator.classList.remove("is-refreshing");
    indicator.classList.add("is-success");

    if (navigator.vibrate) {
      try { navigator.vibrate(14); } catch (e) { }
    }

    // Hold success checkmark briefly so user perceives confirmation
    setTimeout(() => {
      indicator.style.transition = "transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.25s ease";
      indicator.style.opacity = "0";
      indicator.style.transform = `translate(-50%, ${START_Y}px)`;

      setTimeout(() => {
        indicator.classList.remove("is-refreshing", "is-success", "threshold-reached");
        if (meter) meter.style.strokeDashoffset = `${CIRCUMFERENCE}`;
        isRefreshing = false;
        hasCrossedThreshold = false;
      }, 320);
    }, 400);
  }

  function resetPullVisuals() {
    indicator.classList.remove("threshold-reached");
    indicator.style.transition = "transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease";
    indicator.style.opacity = "0";
    indicator.style.transform = `translate(-50%, ${START_Y}px)`;

    setTimeout(() => {
      if (meter) meter.style.strokeDashoffset = `${CIRCUMFERENCE}`;
      hasCrossedThreshold = false;
    }, 300);
  }

  async function triggerPullRefresh() {
    isRefreshing = true;
    snapToRefreshPosition();

    if (navigator.vibrate) {
      try { navigator.vibrate([10, 30, 10]); } catch (e) { }
    }

    const minDelay = new Promise((resolve) => setTimeout(resolve, 600));

    try {
      const currentPath = normalizePath(window.location.pathname);
      const viewName = SPA_ROUTES[currentPath] || "dashboard";

      let fetchPromise;
      if (viewName === "dashboard") {
        fetchPromise = loadHistory();
      } else if (viewName === "reminders") {
        fetchPromise = loadReminders();
      } else if (viewName === "watchdogs") {
        fetchPromise = loadWatchdogs();
      } else if (viewName === "settings") {
        fetchPromise = loadSettings();
      } else {
        fetchPromise = Promise.resolve();
      }

      await Promise.all([fetchPromise, minDelay]);
      showSuccessAndReset();
    } catch (err) {
      toast("Refresh failed: " + err.message);
      resetPullVisuals();
      isRefreshing = false;
    }
  }

  // Touch event handlers for mobile / iOS home screen PWA
  document.addEventListener("touchstart", (e) => {
    if (isRefreshing) return;
    if (document.querySelector(".modal-backdrop:not(.hidden)")) return;

    // Do not initiate pull-to-refresh from the fixed topbar or bottom tabbar
    if (e.target.closest(".topbar, .tabbar")) return;

    const scrollY = window.scrollY || document.documentElement.scrollTop || 0;
    if (scrollY > 1) return;

    touchStartY = e.touches[0].clientY;
    touchStartX = e.touches[0].clientX;
    isPulling = false;
    pullDistance = 0;
    hasCrossedThreshold = false;
  }, { passive: true });

  document.addEventListener("touchmove", (e) => {
    if (isRefreshing) return;
    if (document.querySelector(".modal-backdrop:not(.hidden)")) return;

    // Completely prevent touch dragging on the topbar or tabbar
    if (e.target.closest(".topbar, .tabbar")) {
      if (e.cancelable) e.preventDefault();
      return;
    }

    const scrollY = window.scrollY || document.documentElement.scrollTop || 0;
    if (scrollY > 1 && !isPulling) return;

    const currentY = e.touches[0].clientY;
    const currentX = e.touches[0].clientX;
    const deltaY = currentY - touchStartY;
    const deltaX = Math.abs(currentX - touchStartX);

    // If swipe is horizontal or upwards, do not pull
    if (deltaY <= 0 || deltaX > deltaY) return;

    if (scrollY <= 0) {
      if (e.cancelable) {
        e.preventDefault();
      }
      isPulling = true;
      pullDistance = Math.min(MAX_PULL, deltaY * 0.45);
      updatePullVisuals(pullDistance);
    }
  }, { passive: false });

  document.addEventListener("touchend", () => {
    if (!isPulling || isRefreshing) return;
    isPulling = false;

    if (pullDistance >= PULL_THRESHOLD) {
      triggerPullRefresh();
    } else {
      resetPullVisuals();
    }
  }, { passive: true });

  document.addEventListener("touchcancel", () => {
    if (!isPulling || isRefreshing) return;
    isPulling = false;
    resetPullVisuals();
  }, { passive: true });

  // Mouse event handlers for desktop testing / preview
  let isMouseDown = false;
  let mouseStartY = 0;
  let mouseStartX = 0;

  document.addEventListener("mousedown", (e) => {
    if (isRefreshing || e.button !== 0) return;
    if (document.querySelector(".modal-backdrop:not(.hidden)")) return;
    if (e.target.closest(".topbar, .tabbar")) return;

    const scrollY = window.scrollY || document.documentElement.scrollTop || 0;
    if (scrollY <= 0 && e.clientY < 110) {
      isMouseDown = true;
      mouseStartY = e.clientY;
      mouseStartX = e.clientX;
      isPulling = false;
      pullDistance = 0;
      hasCrossedThreshold = false;
    }
  });

  document.addEventListener("mousemove", (e) => {
    if (!isMouseDown || isRefreshing) return;

    const deltaY = e.clientY - mouseStartY;
    const deltaX = Math.abs(e.clientX - mouseStartX);

    if (deltaY > 6 && deltaY > deltaX) {
      isPulling = true;
      pullDistance = Math.min(MAX_PULL, deltaY * 0.45);
      updatePullVisuals(pullDistance);
    }
  });

  document.addEventListener("mouseup", () => {
    if (!isMouseDown) return;
    isMouseDown = false;

    if (isPulling && !isRefreshing) {
      isPulling = false;
      if (pullDistance >= PULL_THRESHOLD) {
        triggerPullRefresh();
      } else {
        resetPullVisuals();
      }
    }
  });
}

// Global page initialization
document.addEventListener("DOMContentLoaded", () => {
  checkNotificationPrompt();

  // If on login page, skip SPA management
  if (document.body.classList.contains("auth-body")) return;

  setupCommonEventListeners();
  syncThemeControl();
  const featureSwitch = document.getElementById("watchdogs-feature-switch");
  if (featureSwitch) {
    featureSwitch.addEventListener("keydown", (e) => {
      if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        toggleWatchdogsFeature(featureSwitch);
      }
    });
  }
  initPullToRefresh();
  navigateTo(window.location.pathname, false);
  setTimeout(() => {
    updateNavIndicators(normalizePath(window.location.pathname));
  }, 60);
});

// ---------- Dashboard ----------

async function loadHistory() {
  const list = document.getElementById("history-list");
  const empty = document.getElementById("history-empty");
  const countEl = document.getElementById("history-count");
  if (!list) return;

  try {
    const items = await api("/api/notifications?limit=50");

    if (countEl) {
      countEl.textContent = items && items.length > 0 ? items.length : "";
    }

    if (!items || items.length === 0) {
      list.innerHTML = "";
      if (empty) empty.classList.remove("hidden");
      return;
    }
    if (empty) empty.classList.add("hidden");

    const statusBadge = (status) => {
      if (status === "sent") {
        return `<span class="badge success"><span class="badge-dot"></span>Delivered</span>`;
      }
      if (status === "no_subscriptions") {
        return `<span class="badge"><span class="badge-dot"></span>No device</span>`;
      }
      return `<span class="badge danger"><span class="badge-dot"></span>Failed</span>`;
    };

    const sourceAvatar = (source) => {
      if (source === "webhook") {
        return `<div class="item-avatar source-webhook" title="Webhook">${ICONS.webhook}</div>`;
      }
      if (source === "reminder") {
        return `<div class="item-avatar source-reminder" title="Reminder">${ICONS.clock}</div>`;
      }
      if (source === "watchdog") {
        return `<div class="item-avatar source-watchdog" title="Watchdog Heartbeat">${ICONS.activity}</div>`;
      }
      return `<div class="item-avatar source-test" title="Test Push">${ICONS.zap}</div>`;
    };

    list.innerHTML = items
      .map((n) => {
        const urlBadge = n.url && n.url !== "/" ? `
          <a href="${escapeHtml(n.url)}" target="_blank" rel="noopener" class="item-link-badge">
            ${ICONS.link} <span>Open URL</span>
          </a>` : "";

        return `
        <div class="list-item">
          <div class="list-item-main">
            ${sourceAvatar(n.source)}
            <div class="item-details">
              <span class="list-item-title">${escapeHtml(n.title)}</span>
              ${n.body ? `<span class="list-item-sub">${escapeHtml(n.body)}</span>` : ""}
              ${urlBadge}
            </div>
          </div>
          <div class="item-action-col">
            ${statusBadge(n.status)}
            <span class="time-stamp">${timeAgo(n.created_at)}</span>
            <button class="icon-btn" onclick="openSnoozeModal('notification', ${n.id})" title="Snooze as reminder">
              ${ICONS.clock} <span>Snooze</span>
            </button>
          </div>
        </div>`;
      })
      .join("");
  } catch (err) {
    toast(err.message);
  }
}

// ---------- Reminders ----------

async function loadReminders() {
  const list = document.getElementById("reminders-list");
  const empty = document.getElementById("reminders-empty");
  const countEl = document.getElementById("reminders-count");
  if (!list) return;

  try {
    const items = await api("/api/reminders");

    if (countEl) {
      countEl.textContent = items && items.length > 0 ? items.length : "";
    }

    if (!items || items.length === 0) {
      list.innerHTML = "";
      if (empty) empty.classList.remove("hidden");
      return;
    }
    if (empty) empty.classList.add("hidden");

    list.innerHTML = items
      .map((r) => {
        const nextTime = r.next_run_at ? formatDateTime(r.next_run_at) : "Paused";
        const categoryBadge = r.category
          ? `<span class="reminder-chip chip-category">#${escapeHtml(r.category)}</span>`
          : "";
        const urlBadge = r.url
          ? `<a href="${escapeHtml(r.url)}" target="_blank" rel="noopener" class="reminder-chip" onclick="event.stopPropagation()">
              ${ICONS.link} <span>Link</span>
            </a>`
          : "";

        return `
        <div class="reminder-card">
          <div class="reminder-card-row1">
            <div class="reminder-title-area" onclick="openReminderModal(${r.id})">
              <span class="list-item-title">${escapeHtml(r.title)}</span>
            </div>
            <div class="switch-control ${r.enabled ? "active" : ""}" 
                 onclick="toggleReminder(${r.id})" 
                 title="${r.enabled ? 'Click to pause' : 'Click to resume'}">
              <div class="switch-track">
                <div class="switch-thumb"></div>
              </div>
            </div>
          </div>

          ${r.body ? `<div class="list-item-sub" onclick="openReminderModal(${r.id})" style="cursor:pointer;">${escapeHtml(r.body)}</div>` : ""}

          <div class="reminder-chips-row" onclick="openReminderModal(${r.id})">
            ${categoryBadge}
            <span class="reminder-chip">${ICONS.repeat} ${scheduleSummary(r)}</span>
            <span class="reminder-chip chip-next">${ICONS.clock} ${nextTime}</span>
            ${urlBadge}
          </div>

          <div class="reminder-card-actions">
            <button class="btn-ghost btn-sm" onclick="openReminderModal(${r.id})">
              ${ICONS.edit} <span>Edit</span>
            </button>
            <button class="btn-ghost btn-sm" onclick="openSnoozeModal('reminder', ${r.id})">
              ${ICONS.clock} <span>Snooze</span>
            </button>
            <button class="btn-danger btn-sm" onclick="deleteReminder(${r.id})">
              ${ICONS.trash} <span>Delete</span>
            </button>
          </div>
        </div>`;
      })
      .join("");
  } catch (err) {
    toast(err.message);
  }
}

function scheduleSummary(r) {
  const v = r.schedule_value || {};
  if (r.schedule_type === "once") {
    const formatted = v.datetime ? v.datetime.replace("T", " ") : "date";
    return `Once (${formatted})`;
  }
  if (r.schedule_type === "daily") return `Daily at ${v.time || "09:00"}`;
  if (r.schedule_type === "weekly") {
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    return `Weekly (${days[v.weekday] || "Day"} at ${v.time || "09:00"})`;
  }
  if (r.schedule_type === "monthly") return `Monthly on day ${v.day || 1} at ${v.time || "09:00"}`;
  if (r.schedule_type === "cron") return `Cron: ${v.expr || "* * * * *"}`;
  return r.schedule_type;
}

async function toggleReminder(id) {
  try {
    const updated = await api(`/api/reminders/${id}/toggle`, { method: "POST" });
    toast(updated.enabled ? "Reminder resumed" : "Reminder paused");
    await loadReminders();
  } catch (err) {
    toast(err.message);
  }
}

async function deleteReminder(id) {
  if (!confirm("Are you sure you want to delete this reminder?")) return;
  try {
    await api(`/api/reminders/${id}`, { method: "DELETE" });
    toast("Reminder deleted");
    await loadReminders();
  } catch (err) {
    toast(err.message);
  }
}

// ---------- Snooze Modal ----------

function openSnoozeModal(kind, id) {
  openModal(`
    <p style="color:var(--text-secondary); font-size:13.5px; margin-bottom:12px;">
      Delay notification and remind again in:
    </p>

    <!-- Quick Presets -->
    <div class="snooze-presets">
      <button class="snooze-preset-btn" onclick="setSnooze(15, 'minutes')">+15m</button>
      <button class="snooze-preset-btn" onclick="setSnooze(1, 'hours')">+1h</button>
      <button class="snooze-preset-btn" onclick="setSnooze(3, 'hours')">+3h</button>
      <button class="snooze-preset-btn" onclick="setSnooze(1, 'days')">+1d</button>
    </div>

    <div style="display:flex; gap:10px; margin-top:6px;">
      <div style="flex:1;">
        <label for="snooze-amount">Amount</label>
        <input id="snooze-amount" type="number" min="1" value="1">
      </div>
      <div style="flex:1.2;">
        <label for="snooze-unit">Unit</label>
        <div class="select-wrapper">
          <select id="snooze-unit">
            <option value="minutes">Minutes</option>
            <option value="hours" selected>Hours</option>
            <option value="days">Days</option>
          </select>
          <svg class="select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </div>
      </div>
    </div>

    <div class="modal-actions">
      <button class="btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn-primary" id="snooze-confirm">
        <span>Snooze</span>
      </button>
    </div>
  `, "Snooze Alert");

  window.setSnooze = (amt, unit) => {
    document.getElementById("snooze-amount").value = amt;
    document.getElementById("snooze-unit").value = unit;
  };

  document.getElementById("snooze-confirm").addEventListener("click", async (e) => {
    const amount = parseInt(document.getElementById("snooze-amount").value, 10);
    const unit = document.getElementById("snooze-unit").value;
    if (!amount || amount <= 0) {
      toast("Please enter a valid positive number");
      return;
    }
    const btn = document.getElementById("snooze-confirm");
    btn.disabled = true;
    try {
      const path =
        kind === "reminder" ? `/api/reminders/${id}/snooze` : `/api/notifications/${id}/snooze`;
      await api(path, { method: "POST", body: JSON.stringify({ amount, unit }) });
      closeModal();
      toast(`Snoozed for ${amount} ${unit}`);
      if (kind === "reminder") await loadReminders();
      else await loadHistory();
    } catch (err) {
      toast(err.message);
      btn.disabled = false;
    }
  });
}

// ---------- Add / Edit Reminder Modal ----------

async function openReminderModal(id) {
  let reminder = null;
  if (id) {
    const items = await api("/api/reminders");
    reminder = items.find((r) => r.id === id);
  }
  const v = reminder ? reminder.schedule_value : {};
  const type = reminder ? reminder.schedule_type : "daily";
  const categories = await api("/api/reminders/categories").catch(() => []);

  openModal(`
    <div class="form-group">
      <label for="rf-title">Reminder Title</label>
      <input id="rf-title" value="${reminder ? escapeHtml(reminder.title) : ""}" placeholder="e.g. Server Backup Check or Billing" required autofocus>
    </div>

    <div class="form-group">
      <label for="rf-body">Description or Notes (optional)</label>
      <input id="rf-body" value="${reminder ? escapeHtml(reminder.body || "") : ""}" placeholder="Additional context or checklist">
    </div>

    <div class="form-group">
      <label for="rf-url">Link URL (optional)</label>
      <input id="rf-url" type="url" value="${reminder ? escapeHtml(reminder.url || "") : ""}" placeholder="https://dash.example.com">
    </div>

    <div class="form-group">
      <label for="rf-category">Category (optional)</label>
      <input id="rf-category" list="rf-category-list" value="${reminder ? escapeHtml(reminder.category || "") : ""}" placeholder="e.g. Work, Bills, Dev">
      <datalist id="rf-category-list">
        ${categories.map((c) => `<option value="${escapeHtml(c)}">`).join("")}
      </datalist>
    </div>

    <div class="form-group">
      <label for="rf-type">Repeats</label>
      <div class="select-wrapper">
        <select id="rf-type">
          <option value="once" ${type === "once" ? "selected" : ""}>Once (One-time alert)</option>
          <option value="daily" ${type === "daily" ? "selected" : ""}>Daily</option>
          <option value="weekly" ${type === "weekly" ? "selected" : ""}>Weekly</option>
          <option value="monthly" ${type === "monthly" ? "selected" : ""}>Monthly</option>
          <option value="cron" ${type === "cron" ? "selected" : ""}>Cron Expression (Advanced)</option>
        </select>
        <svg class="select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </div>
    </div>

    <div id="rf-fields" class="form-group"></div>

    <div class="modal-actions">
      <button class="btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn-primary" id="rf-save">
        <span>${reminder ? "Save Changes" : "Create Reminder"}</span>
      </button>
    </div>
  `, reminder ? "Edit Reminder" : "New Reminder");

  const renderFields = () => {
    const currentType = document.getElementById("rf-type").value;
    const fields = document.getElementById("rf-fields");
    if (currentType === "once") {
      fields.innerHTML = `
        <label for="rf-datetime">Target Date & Time</label>
        <input type="datetime-local" id="rf-datetime" value="${v.datetime || ""}" required>`;
    } else if (currentType === "daily") {
      fields.innerHTML = `
        <label for="rf-time">Fire Time</label>
        <input type="time" id="rf-time" value="${v.time || "09:00"}" required>`;
    } else if (currentType === "weekly") {
      const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
      fields.innerHTML = `
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
          <div>
            <label for="rf-weekday">Day of Week</label>
            <div class="select-wrapper">
              <select id="rf-weekday">
                ${days.map((d, i) => `<option value="${i}" ${v.weekday === i ? "selected" : ""}>${d}</option>`).join("")}
              </select>
              <svg class="select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
            </div>
          </div>
          <div>
            <label for="rf-time">Time</label>
            <input type="time" id="rf-time" value="${v.time || "09:00"}" required>
          </div>
        </div>`;
    } else if (currentType === "monthly") {
      fields.innerHTML = `
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
          <div>
            <label for="rf-day">Day of Month (1-31)</label>
            <input type="number" min="1" max="31" id="rf-day" value="${v.day || 1}" required>
          </div>
          <div>
            <label for="rf-time">Time</label>
            <input type="time" id="rf-time" value="${v.time || "09:00"}" required>
          </div>
        </div>`;
    } else if (currentType === "cron") {
      fields.innerHTML = `
        <label for="rf-cron">Cron Expression (5 fields: min hour day month weekday)</label>
        <input id="rf-cron" value="${v.expr || ""}" placeholder="0 9 * * 1-5" style="font-family:var(--font-mono);" required>
        <span style="font-size:11.5px; color:var(--text-muted); margin-top:4px;">Example: <code>0 9 28 * *</code> (9:00 AM on the 28th of every month)</span>`;
    }
  };

  document.getElementById("rf-type").addEventListener("change", renderFields);
  renderFields();

  document.getElementById("rf-save").addEventListener("click", async (e) => {
    const currentType = document.getElementById("rf-type").value;
    let schedule_value = {};
    if (currentType === "once") {
      const dt = document.getElementById("rf-datetime").value;
      if (!dt) { toast("Please pick a date and time"); return; }
      schedule_value = { datetime: dt };
    } else if (currentType === "daily") {
      schedule_value = { time: document.getElementById("rf-time").value };
    } else if (currentType === "weekly") {
      schedule_value = {
        weekday: parseInt(document.getElementById("rf-weekday").value, 10),
        time: document.getElementById("rf-time").value,
      };
    } else if (currentType === "monthly") {
      schedule_value = {
        day: parseInt(document.getElementById("rf-day").value, 10),
        time: document.getElementById("rf-time").value,
      };
    } else if (currentType === "cron") {
      const expr = document.getElementById("rf-cron").value.trim();
      if (!expr) { toast("Please enter a valid cron expression"); return; }
      schedule_value = { expr };
    }

    const titleVal = document.getElementById("rf-title").value.trim();
    if (!titleVal) {
      toast("Reminder title is required");
      return;
    }

    const body = {
      title: titleVal,
      body: document.getElementById("rf-body").value.trim() || null,
      url: document.getElementById("rf-url").value.trim() || null,
      category: document.getElementById("rf-category").value.trim() || null,
      schedule_type: currentType,
      schedule_value,
    };

    e.target.disabled = true;
    try {
      if (reminder) {
        await api(`/api/reminders/${reminder.id}`, { method: "PUT", body: JSON.stringify(body) });
        toast("Reminder updated");
      } else {
        await api("/api/reminders", { method: "POST", body: JSON.stringify(body) });
        toast("Reminder created");
      }
      closeModal();
      await loadReminders();
    } catch (err) {
      toast(err.message);
      e.target.disabled = false;
    }
  });
}

// ---------- Settings ----------

async function loadSettings() {
  const sections = [loadTimezone(), loadFeatureFlags(), loadAiSettings(), loadDevices(), loadApiKeys()];
  const results = await Promise.allSettled(sections);
  results.forEach((r) => {
    if (r.status === "rejected") toast(r.reason?.message || "Failed to load settings section");
  });
}

async function loadTimezone() {
  const [me, zones] = await Promise.all([api("/api/me"), api("/api/timezones")]);
  const select = document.getElementById("timezone-select");
  if (!select) return;

  select.innerHTML = zones
    .map((z) => `<option value="${z}" ${z === me.timezone ? "selected" : ""}>${z}</option>`)
    .join("");
}

function getDeviceIcon(ua) {
  if (!ua) return ICONS.deviceDesktop;
  if (/iPad/.test(ua)) return ICONS.deviceTablet;
  if (/iPhone|Android.*Mobile/.test(ua)) return ICONS.devicePhone;
  if (/Android/.test(ua)) return ICONS.deviceTablet;
  if (/Macintosh|Windows|Linux/.test(ua)) return ICONS.deviceLaptop;
  return ICONS.deviceDesktop;
}

function describeDevice(ua) {
  if (!ua) return "Unknown Device";
  if (/iPhone/.test(ua)) return "Apple iPhone";
  if (/iPad/.test(ua)) return "Apple iPad";
  if (/Android/.test(ua)) return "Android Device";
  if (/Macintosh/.test(ua)) return "Mac Computer";
  if (/Windows/.test(ua)) return "Windows PC";
  if (/Linux/.test(ua)) return "Linux Workstation";
  return "Web Browser";
}

async function loadDevices() {
  const list = document.getElementById("devices-list");
  const empty = document.getElementById("devices-empty");
  const countEl = document.getElementById("devices-count");
  if (!list) return;

  try {
    const items = await api("/api/subscriptions");

    if (countEl) {
      countEl.textContent = items && items.length > 0 ? items.length : "";
    }

    if (!items || items.length === 0) {
      list.innerHTML = "";
      if (empty) empty.classList.remove("hidden");
      return;
    }
    if (empty) empty.classList.add("hidden");

    list.innerHTML = items
      .map(
        (d) => `
      <div class="list-item">
        <div class="list-item-main">
          <div class="item-avatar">${getDeviceIcon(d.user_agent)}</div>
          <div class="item-details">
            <span class="list-item-title">${describeDevice(d.user_agent)}</span>
            <span class="list-item-sub">Registered ${timeAgo(d.created_at)}${d.last_used_at ? "<br>Active " + timeAgo(d.last_used_at) : ""}</span>
          </div>
        </div>
        <div class="list-item-actions">
          <button class="btn-danger btn-sm" onclick="removeDevice(${d.id})">
            ${ICONS.trash} <span>Remove</span>
          </button>
        </div>
      </div>`
      )
      .join("");
  } catch (err) {
    toast(err.message);
  }
}

async function removeDevice(id) {
  if (!confirm("Remove this device? It will immediately stop receiving notifications.")) return;
  try {
    const res = await api(`/api/subscriptions/${id}`, { method: "DELETE" });
    // If this browser is the removed device, drop its push subscription too.
    try {
      const own = await getExistingSubscription();
      if (own && res && own.endpoint === res.endpoint) await own.unsubscribe();
    } catch (e) { }
    toast("Device unsubscribed");
    await loadDevices();
  } catch (err) {
    toast(err.message);
  }
}

async function loadApiKeys() {
  const list = document.getElementById("keys-list");
  const empty = document.getElementById("keys-empty");
  const countEl = document.getElementById("keys-count");
  if (!list) return;

  try {
    const items = await api("/api/api-keys");

    if (countEl) {
      countEl.textContent = items && items.length > 0 ? items.length : "";
    }

    if (!items || items.length === 0) {
      list.innerHTML = "";
      if (empty) empty.classList.remove("hidden");
      return;
    }
    if (empty) empty.classList.add("hidden");

    list.innerHTML = items
      .map(
        (k) => `
      <div class="list-item">
        <div class="list-item-main">
          <div class="item-avatar">${ICONS.key}</div>
          <div class="item-details">
            <span class="list-item-title">${escapeHtml(k.name)}</span>
            <span class="list-item-sub" style="font-family:var(--font-mono); font-size:12px;">
              ${escapeHtml(k.key_prefix)}•••••••• &middot; created ${timeAgo(k.created_at)}
            </span>
          </div>
        </div>
        <div class="list-item-actions">
          <button class="btn-danger btn-sm" onclick="revokeApiKey(${k.id})">
            ${ICONS.trash} <span>Revoke</span>
          </button>
        </div>
      </div>`
      )
      .join("");
  } catch (err) {
    toast(err.message);
  }
}

async function revokeApiKey(id) {
  if (!confirm("Revoke this API key? Any webhook or script using it will stop working immediately.")) {
    return;
  }
  try {
    await api(`/api/api-keys/${id}`, { method: "DELETE" });
    toast("API key revoked");
    await loadApiKeys();
  } catch (err) {
    toast(err.message);
  }
}

function openCreateKeyModal() {
  openModal(`
    <div class="form-group">
      <label for="key-name">Key Identifier or Service Name</label>
      <input id="key-name" placeholder="e.g. GitHub Actions, Backups, Billing Bot" required autofocus>
    </div>
    <div class="modal-actions">
      <button class="btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn-primary" id="key-create-btn">
        <span>Generate Key</span>
      </button>
    </div>
  `, "Generate API Key");

  document.getElementById("key-create-btn").addEventListener("click", async (e) => {
    const name = document.getElementById("key-name").value.trim();
    if (!name) {
      toast("Name is required");
      return;
    }
    e.target.disabled = true;
    try {
      const res = await api("/api/api-keys", { method: "POST", body: JSON.stringify({ name }) });
      openModal(`
        <p style="color:var(--text-secondary); font-size:13.5px; line-height:1.5;">
          This token will only be shown once. Copy and store it securely.
        </p>
        <div class="key-reveal-wrap">
          <div class="key-reveal" id="generated-key-display">${escapeHtml(res.key)}</div>
          <button class="btn-ghost btn-sm" id="modal-copy-key-btn" onclick="copyToClipboard('${escapeHtml(res.key)}', this, 'Copied Token!')">
            ${ICONS.copy} <span>Copy Token</span>
          </button>
        </div>
        <div class="modal-actions">
          <button class="btn-primary btn-block" onclick="closeModal(); loadApiKeys();">Done</button>
        </div>
      `, "Save Your API Key");
    } catch (err) {
      toast(err.message);
      e.target.disabled = false;
    }
  });
}

// ==========================================================================
// Settings: Appearance & Feature flags
// ==========================================================================

function syncThemeControl() {
  if (!window.NFBTheme) return;
  const current = window.NFBTheme.get();
  document.querySelectorAll("[data-theme-choice]").forEach((btn) => {
    const active = btn.dataset.themeChoice === current;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-checked", active ? "true" : "false");
  });
}

function setThemeChoice(mode) {
  if (!window.NFBTheme) return;
  window.NFBTheme.set(mode);
  syncThemeControl();
}

function watchdogsEnabled() {
  return document.body.dataset.watchdogs === "1";
}

function applyWatchdogsFlag(enabled) {
  document.body.dataset.watchdogs = enabled ? "1" : "0";
  document.querySelectorAll("[data-requires='watchdogs']").forEach((el) => {
    el.classList.toggle("hidden", !enabled);
  });
  const sw = document.getElementById("watchdogs-feature-switch");
  if (sw) {
    sw.classList.toggle("active", enabled);
    sw.setAttribute("aria-checked", enabled ? "true" : "false");
  }
  // Tab widths change when an item appears/disappears; re-measure the sliding indicators.
  requestAnimationFrame(() => updateNavIndicators(normalizePath(window.location.pathname)));
}

async function loadFeatureFlags() {
  try {
    const me = await api("/api/me");
    applyWatchdogsFlag(!!me.watchdogs_enabled);
  } catch (e) { }
}

async function toggleWatchdogsFeature(switchEl) {
  if (switchEl.dataset.busy) return;
  switchEl.dataset.busy = "1";
  const next = !watchdogsEnabled();
  applyWatchdogsFlag(next);
  try {
    const res = await api("/api/me/watchdogs", {
      method: "PUT",
      body: JSON.stringify({ enabled: next }),
    });
    applyWatchdogsFlag(!!res.watchdogs_enabled);
    toast(res.watchdogs_enabled ? "Watchdogs enabled" : "Watchdogs disabled");
  } catch (err) {
    applyWatchdogsFlag(!next);
    toast(err.message);
  } finally {
    delete switchEl.dataset.busy;
  }
}

// ==========================================================================
// AI LLM Configuration
// ==========================================================================

async function loadAiSettings() {
  try {
    const me = await api("/api/me");
    const keyInput = document.getElementById("setting-ai-key");
    const urlInput = document.getElementById("setting-ai-url");
    const modelInput = document.getElementById("setting-ai-model");

    if (keyInput) {
      if (me.openai_configured) {
        keyInput.placeholder = "•••••••••••••••• (API Key Configured)";
      } else {
        keyInput.placeholder = "sk-...";
      }
    }
    if (urlInput && me.openai_base_url) {
      urlInput.value = me.openai_base_url;
    }
    if (modelInput && me.openai_model) {
      modelInput.value = me.openai_model;
    }
  } catch (e) { }
}

async function saveAiSettings() {
  const keyInput = document.getElementById("setting-ai-key");
  const urlInput = document.getElementById("setting-ai-url");
  const modelInput = document.getElementById("setting-ai-model");
  const btn = document.getElementById("save-ai-btn");

  const payload = {};
  if (keyInput && keyInput.value.trim()) {
    payload.openai_api_key = keyInput.value.trim();
  }
  if (urlInput) {
    payload.openai_base_url = urlInput.value.trim() || "https://api.openai.com/v1";
  }
  if (modelInput) {
    payload.openai_model = modelInput.value.trim() || "gpt-4o-mini";
  }

  if (btn) btn.disabled = true;
  try {
    await api("/api/me/ai", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    toast("AI settings saved successfully");
    if (keyInput && keyInput.value.trim()) {
      keyInput.value = "";
      keyInput.placeholder = "•••••••••••••••• (API Key Configured)";
    }
  } catch (err) {
    toast(err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function testAiConnection() {
  const btn = document.getElementById("test-ai-btn");
  const keyInput = document.getElementById("setting-ai-key");
  const urlInput = document.getElementById("setting-ai-url");
  const modelInput = document.getElementById("setting-ai-model");

  const payload = {};
  if (keyInput && keyInput.value.trim()) payload.openai_api_key = keyInput.value.trim();
  if (urlInput && urlInput.value.trim()) payload.openai_base_url = urlInput.value.trim();
  if (modelInput && modelInput.value.trim()) payload.openai_model = modelInput.value.trim();

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `${ICONS.spinner} <span>Testing...</span>`;
  }
  try {
    const res = await api("/api/me/ai/test", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    toast(`AI connected! Model response: "${res.sample_response || "OK"}"`);
  } catch (err) {
    toast("AI test failed: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="22" y1="2" x2="11" y2="13"/>
          <polygon points="22 2 15 22 11 13 2 9 22 2"/>
        </svg>
        <span>Test Connection</span>`;
    }
  }
}

function toggleApiKeyVisibility() {
  const keyInput = document.getElementById("setting-ai-key");
  if (!keyInput) return;
  keyInput.type = keyInput.type === "password" ? "text" : "password";
}

// ==========================================================================
// Watchdogs Client Logic
// ==========================================================================

function formatSeconds(secs) {
  if (!secs) return "0s";
  if (secs % 86400 === 0) return `${secs / 86400}d`;
  if (secs % 3600 === 0) return `${secs / 3600}h`;
  if (secs % 60 === 0) return `${secs / 60}m`;
  return `${secs}s`;
}

function parseSeconds(val, unit) {
  const num = parseFloat(val) || 0;
  if (unit === "d") return Math.round(num * 86400);
  if (unit === "h") return Math.round(num * 3600);
  if (unit === "m") return Math.round(num * 60);
  return Math.round(num);
}

function decomposeSeconds(secs) {
  if (secs >= 86400 && secs % 86400 === 0) return { val: secs / 86400, unit: "d" };
  if (secs >= 3600 && secs % 3600 === 0) return { val: secs / 3600, unit: "h" };
  if (secs >= 60 && secs % 60 === 0) return { val: secs / 60, unit: "m" };
  return { val: secs, unit: "s" };
}

async function loadWatchdogs() {
  const list = document.getElementById("watchdogs-list");
  const empty = document.getElementById("watchdogs-empty");
  const countEl = document.getElementById("watchdogs-count");
  if (!list) return;

  try {
    const items = await api("/api/watchdogs");
    if (countEl) {
      countEl.textContent = items && items.length > 0 ? items.length : "";
    }

    if (!items || items.length === 0) {
      list.innerHTML = "";
      if (empty) empty.classList.remove("hidden");
      return;
    }
    if (empty) empty.classList.add("hidden");

    const origin = baseUrl();

    list.innerHTML = items
      .map((w) => {
        const pingUrl = `${origin}/api/ping/${w.token}`;
        let statusClass = "pending";
        let statusLabel = "Awaiting Ping";
        let dotClass = "pending";

        if (!w.enabled) {
          statusClass = "paused";
          statusLabel = "Paused";
          dotClass = "paused";
        } else if (w.status === "healthy") {
          statusClass = "healthy";
          statusLabel = "Healthy";
          dotClass = "healthy";
        } else if (w.status === "down") {
          statusClass = "down";
          statusLabel = "Down";
          dotClass = "down";
        }

        return `
        <div class="watchdog-card" data-id="${w.id}">
          <div class="watchdog-row1">
            <div class="watchdog-title-group" onclick="openCreateWatchdogModal(${w.id})" style="cursor:pointer;">
              <span class="watchdog-status-dot ${dotClass}"></span>
              <span class="watchdog-name">${escapeHtml(w.name)}</span>
            </div>
            <div class="switch-control ${w.enabled ? "active" : ""}"
                 onclick="toggleWatchdog(${w.id}, this)"
                 title="${w.enabled ? "Disable watchdog" : "Enable watchdog"}">
              <div class="switch-track">
                <div class="switch-thumb"></div>
              </div>
            </div>
          </div>

          <div class="watchdog-chips-row">
            <span class="watchdog-status-badge ${statusClass}">${statusLabel}</span>
            <span class="watchdog-chip">
              ${ICONS.clock} Every ${formatSeconds(w.ping_interval_seconds)}
            </span>
            <span class="watchdog-chip">
              +${formatSeconds(w.grace_period_seconds)} grace
            </span>
            <span class="watchdog-chip">
              ${w.last_ping_at ? `Pinged ${timeAgo(w.last_ping_at)}` : "No pings yet"}
            </span>
          </div>

          <div class="watchdog-ping-box">
            <span class="watchdog-ping-url" title="${pingUrl}">${escapeHtml(pingUrl)}</span>
            <div style="display:flex; gap:6px; flex-shrink:0;">
              <button class="btn-ghost btn-sm" onclick="testWatchdogPing('${w.token}', this)" title="Send a test ping right now">
                ${ICONS.zap} <span>Ping</span>
              </button>
              <button class="btn-copy-code" onclick="copyToClipboard('${pingUrl}', this, 'Copied!')">
                ${ICONS.copy} <span>Copy URL</span>
              </button>
            </div>
          </div>

          <div class="watchdog-actions-row">
            <button class="btn-ghost btn-sm" onclick="openCreateWatchdogModal(${w.id})">
              ${ICONS.edit} <span>Edit</span>
            </button>
            <button class="btn-danger btn-sm" onclick="deleteWatchdog(${w.id})">
              ${ICONS.trash} <span>Delete</span>
            </button>
          </div>
        </div>`;
      })
      .join("");
  } catch (err) {
    toast(err.message);
  }
}

async function testWatchdogPing(token, btn) {
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `${ICONS.spinner} <span>...</span>`;
  }
  try {
    const res = await api(`/api/ping/${token}`, { method: "POST" });
    toast(`Ping OK! Watchdog "${res.watchdog}" status is now ${res.status}`);
    await loadWatchdogs();
  } catch (err) {
    toast("Ping failed: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `${ICONS.zap} <span>Ping</span>`;
    }
  }
}

async function toggleWatchdog(id, switchEl) {
  const prevActive = switchEl.classList.contains("active");
  switchEl.classList.toggle("active");
  try {
    const res = await api(`/api/watchdogs/${id}/toggle`, { method: "POST" });
    toast(res.enabled ? "Watchdog enabled" : "Watchdog paused");
    await loadWatchdogs();
  } catch (err) {
    switchEl.classList.toggle("active", prevActive);
    toast(err.message);
  }
}

async function deleteWatchdog(id) {
  if (!confirm("Delete this watchdog? Heartbeat monitoring will cease immediately.")) return;
  try {
    await api(`/api/watchdogs/${id}`, { method: "DELETE" });
    toast("Watchdog deleted");
    await loadWatchdogs();
  } catch (err) {
    toast(err.message);
  }
}

async function openCreateWatchdogModal(id) {
  let watchdog = null;
  let me = {};
  try {
    const [meData, items] = await Promise.all([
      api("/api/me"),
      id ? api("/api/watchdogs") : Promise.resolve([]),
    ]);
    me = meData || {};
    if (id && items) {
      watchdog = items.find((w) => w.id === id);
    }
  } catch (err) {
    toast(err.message);
    return;
  }

  const minAllowed = me.watchdog_min_ping_seconds || 60;
  const currentInterval = watchdog ? decomposeSeconds(watchdog.ping_interval_seconds) : { val: 5, unit: "m" };
  const currentGrace = watchdog ? decomposeSeconds(watchdog.grace_period_seconds) : { val: 2, unit: "m" };

  openModal(`
    <div class="form-group">
      <label for="wf-name">Watchdog Name</label>
      <input id="wf-name" value="${watchdog ? escapeHtml(watchdog.name) : ""}" placeholder="e.g. Postgres DB Backup or Cron Sync" required autofocus>
    </div>

    <div class="form-group">
      <label for="wf-interval-val">Expected Ping Frequency</label>
      <div style="display:flex; gap:8px;">
        <input id="wf-interval-val" type="number" min="1" step="1" value="${currentInterval.val}" required style="flex:1;">
        <div class="select-wrapper" style="width:140px;">
          <select id="wf-interval-unit">
            <option value="s" ${currentInterval.unit === "s" ? "selected" : ""}>Seconds</option>
            <option value="m" ${currentInterval.unit === "m" ? "selected" : ""}>Minutes</option>
            <option value="h" ${currentInterval.unit === "h" ? "selected" : ""}>Hours</option>
            <option value="d" ${currentInterval.unit === "d" ? "selected" : ""}>Days</option>
          </select>
          <svg class="select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </div>
      </div>
      <span class="card-hint">Safety floor for your account: minimum ${minAllowed} seconds</span>
    </div>

    <div class="form-group">
      <label for="wf-grace-val">Grace Period (Extra window before alert fires)</label>
      <div style="display:flex; gap:8px;">
        <input id="wf-grace-val" type="number" min="0" step="1" value="${currentGrace.val}" required style="flex:1;">
        <div class="select-wrapper" style="width:140px;">
          <select id="wf-grace-unit">
            <option value="s" ${currentGrace.unit === "s" ? "selected" : ""}>Seconds</option>
            <option value="m" ${currentGrace.unit === "m" ? "selected" : ""}>Minutes</option>
            <option value="h" ${currentGrace.unit === "h" ? "selected" : ""}>Hours</option>
            <option value="d" ${currentGrace.unit === "d" ? "selected" : ""}>Days</option>
          </select>
          <svg class="select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </div>
      </div>
    </div>

    <div class="modal-actions">
      <button class="btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn-primary" id="wf-save-btn">
        <span>${watchdog ? "Save Changes" : "Create Watchdog"}</span>
      </button>
    </div>
  `, watchdog ? "Edit Watchdog" : "New Watchdog");

  const saveBtn = document.getElementById("wf-save-btn");
  if (saveBtn) {
    saveBtn.addEventListener("click", async () => {
      const name = document.getElementById("wf-name").value.trim();
      const intVal = document.getElementById("wf-interval-val").value;
      const intUnit = document.getElementById("wf-interval-unit").value;
      const graceVal = document.getElementById("wf-grace-val").value;
      const graceUnit = document.getElementById("wf-grace-unit").value;

      if (!name) {
        toast("Please provide a watchdog name");
        return;
      }

      const intervalSecs = parseSeconds(intVal, intUnit);
      const graceSecs = parseSeconds(graceVal, graceUnit);

      if (intervalSecs < minAllowed) {
        toast(`Interval cannot be less than your policy minimum (${minAllowed}s)`);
        return;
      }

      saveBtn.disabled = true;
      try {
        if (watchdog) {
          await api(`/api/watchdogs/${watchdog.id}`, {
            method: "PUT",
            body: JSON.stringify({
              name,
              ping_interval_seconds: intervalSecs,
              grace_period_seconds: graceSecs,
            }),
          });
          toast("Watchdog updated");
        } else {
          await api("/api/watchdogs", {
            method: "POST",
            body: JSON.stringify({
              name,
              ping_interval_seconds: intervalSecs,
              grace_period_seconds: graceSecs,
            }),
          });
          toast("Watchdog created");
        }
        closeModal();
        await loadWatchdogs();
      } catch (err) {
        toast(err.message);
        saveBtn.disabled = false;
      }
    });
  }
}

// ==========================================================================
// AI Assistant Drawer & Conversational Chat
// ==========================================================================

let isAiSending = false;
let aiConversationHistory = [];
const AI_HISTORY_SENT_LIMIT = 20; // cap what's sent to the LLM each turn

function openAiChatModal() {
  const drawer = document.getElementById("ai-chat-drawer");
  if (!drawer) return;
  drawer.classList.remove("hidden");
  drawer.setAttribute("aria-hidden", "false");
  document.body.classList.add("ai-chat-open");
  const input = document.getElementById("ai-chat-input");
  if (input) {
    setTimeout(() => input.focus(), 150);
  }
}

function closeAiChatModal() {
  const drawer = document.getElementById("ai-chat-drawer");
  if (!drawer) return;
  drawer.classList.add("hidden");
  drawer.setAttribute("aria-hidden", "true");
  document.body.classList.remove("ai-chat-open");
}

function sendQuickAiPrompt(text) {
  const input = document.getElementById("ai-chat-input");
  if (input) {
    input.value = text;
    handleAiFormSubmit(new Event("submit"));
  }
}

async function handleAiFormSubmit(e) {
  if (e && e.preventDefault) e.preventDefault();
  if (isAiSending) return;

  const input = document.getElementById("ai-chat-input");
  const sendBtn = document.getElementById("ai-send-btn");
  if (!input) return;

  const prompt = input.value.trim();
  if (!prompt) return;

  input.value = "";
  isAiSending = true;
  if (sendBtn) sendBtn.disabled = true;

  appendAiBubble("user", prompt);
  aiConversationHistory.push({ role: "user", content: prompt });
  const typingIndicator = appendAiTypingIndicator();

  try {
    const res = await api("/api/ai/chat", {
      method: "POST",
      body: JSON.stringify({ messages: aiConversationHistory.slice(-AI_HISTORY_SENT_LIMIT) }),
    });
    aiConversationHistory.push({ role: "assistant", content: res.reply || "" });

    if (typingIndicator) typingIndicator.remove();

    appendAiBubble("assistant", res.reply || "Done!", res.executed_tools);

    // If tools updated reminders or watchdogs, refresh the corresponding view!
    if (res.executed_tools && res.executed_tools.length > 0) {
      const toolNames = res.executed_tools.map((t) => t.name);
      if (toolNames.some((n) => n.includes("reminder"))) {
        loadReminders().catch(() => {});
      }
      if (toolNames.some((n) => n.includes("watchdog"))) {
        loadWatchdogs().catch(() => {});
      }
    }
  } catch (err) {
    if (typingIndicator) typingIndicator.remove();
    appendAiBubble("assistant", `⚠️ Error: ${err.message}. Make sure your OpenAI API Key is configured in Settings.`);
  } finally {
    isAiSending = false;
    if (sendBtn) sendBtn.disabled = false;
    input.focus();
  }
}

let markedConfigured = false;

function renderAiMarkdown(content) {
  // marked/DOMPurify are loaded as separate <script defer> tags -- if either
  // failed to load (blocked, offline, etc.) fall back to plain escaped text
  // instead of breaking the whole chat.
  if (typeof marked === "undefined" || typeof DOMPurify === "undefined") {
    return escapeHtml(content).replace(/\n/g, "<br>");
  }

  if (!markedConfigured) {
    marked.setOptions({ gfm: true, breaks: true });
    DOMPurify.addHook("afterSanitizeAttributes", (node) => {
      if (node.tagName === "A") {
        node.setAttribute("target", "_blank");
        node.setAttribute("rel", "noopener noreferrer");
      }
    });
    markedConfigured = true;
  }

  // Tool results (reminder titles, watchdog names, etc.) can contain
  // attacker-controlled text from webhooks the LLM might echo back
  // verbatim -- sanitize the rendered HTML before it ever hits innerHTML.
  const rawHtml = marked.parse(content || "");
  return DOMPurify.sanitize(rawHtml, { ADD_ATTR: ["target"] });
}

function appendAiBubble(role, content, toolsExecuted = []) {
  const container = document.getElementById("ai-messages");
  if (!container) return null;

  const bubble = document.createElement("div");
  bubble.className = `ai-bubble ai-bubble-${role}`;

  let toolsHtml = "";
  if (toolsExecuted && toolsExecuted.length > 0) {
    toolsHtml = toolsExecuted
      .map(
        (t) => `
      <div class="ai-tool-badge">
        ${ICONS.zap}
        <span>Executed <strong>${escapeHtml(t.name)}</strong></span>
      </div>`
      )
      .join("");
  }

  if (role === "assistant") {
    bubble.innerHTML = `
      <div class="ai-bubble-avatar">
        ${ICONS.sparkle || ICONS.zap}
      </div>
      <div class="ai-bubble-content">
        ${toolsHtml}
        <div class="ai-markdown">${renderAiMarkdown(content)}</div>
      </div>`;
  } else {
    bubble.innerHTML = `
      <div class="ai-bubble-content">
        ${escapeHtml(content).replace(/\n/g, "<br>")}
      </div>`;
  }

  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
  return bubble;
}

function appendAiTypingIndicator() {
  const container = document.getElementById("ai-messages");
  if (!container) return null;

  const el = document.createElement("div");
  el.className = "ai-bubble ai-bubble-assistant";
  el.innerHTML = `
    <div class="ai-bubble-avatar">${ICONS.sparkle || ICONS.zap}</div>
    <div class="ai-typing-indicator">
      <span class="ai-dot"></span>
      <span class="ai-dot"></span>
      <span class="ai-dot"></span>
    </div>`;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
  return el;
}
