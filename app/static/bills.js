// ==========================================================================
// Bills: accounts, add dialog (built from each adapter's own field spec),
// CAPTCHA step, bill detail with chart, share image.
// Loaded after app.js and relies on its helpers (api, openModal, toast, ...).
// ==========================================================================

const BILL_LANGS = ["en", "ur_roman", "ur"];
const BILL_CATEGORY_LABELS = { electricity: "Electricity", gas: "Gas", water: "Water", telecom: "Phone & internet", other: "Other" };
const BILL_CATEGORY_ICONS = { electricity: ICONS.zap, gas: ICONS.activity, water: ICONS.link, telecom: ICONS.devicePhone, other: ICONS.bell };
const BILL_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const BILL_MONTHS_UR = ["جنوری", "فروری", "مارچ", "اپریل", "مئی", "جون", "جولائی", "اگست", "ستمبر", "اکتوبر", "نومبر", "دسمبر"];

let billsCache = [];
let billProviders = null;

function billsEnabled() {
  return document.body.dataset.bills === "1";
}

function billsLang() {
  const lang = document.body.dataset.billsLang;
  return BILL_LANGS.includes(lang) ? lang : "ur_roman";
}

function applyBillsFlag(enabled) {
  document.body.dataset.bills = enabled ? "1" : "0";
  document.querySelectorAll("[data-requires='bills']").forEach((el) => el.classList.toggle("hidden", !enabled));
  const sw = document.getElementById("bills-feature-switch");
  if (sw) {
    sw.classList.toggle("active", enabled);
    sw.setAttribute("aria-checked", enabled ? "true" : "false");
  }
  requestAnimationFrame(() => updateNavIndicators(normalizePath(window.location.pathname)));
}

function applyBillsLanguage(lang) {
  document.body.dataset.billsLang = lang;
  document.querySelectorAll("[data-bills-lang]").forEach((btn) => {
    const active = btn.dataset.billsLang === lang;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-checked", active ? "true" : "false");
  });
}

async function toggleBillsFeature(switchEl) {
  if (switchEl.dataset.busy) return;
  switchEl.dataset.busy = "1";
  const next = !billsEnabled();
  applyBillsFlag(next);
  try {
    const res = await api("/api/me/bills", { method: "PUT", body: JSON.stringify({ enabled: next }) });
    applyBillsFlag(!!res.bills_enabled);
    toast(res.bills_enabled ? "Bills enabled" : "Bills disabled");
  } catch (err) {
    applyBillsFlag(!next);
    toast(err.message);
  } finally {
    delete switchEl.dataset.busy;
  }
}

async function setBillsLanguage(lang) {
  applyBillsLanguage(lang);
  renderBillsList();
  const open = document.getElementById("bill-explain");
  if (open) open.dispatchEvent(new CustomEvent("langchange"));
  try {
    await api("/api/me/bills", { method: "PUT", body: JSON.stringify({ language: lang }) });
  } catch (err) {
    toast(err.message);
  }
}

// ---------- formatting ----------

function rs(value) {
  return value === null || value === undefined ? "-" : "Rs " + Math.round(value).toLocaleString("en-US");
}

function billMonthLabel(ym, long = false) {
  if (!ym) return "";
  const [y, m] = ym.split("-").map(Number);
  return `${BILL_MONTHS[m - 1]} ${long ? y : String(y).slice(2)}`;
}

function billDay(iso, lang = "en") {
  if (!iso) return "-";
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return `${d} ${(lang === "ur" ? BILL_MONTHS_UR : BILL_MONTHS)[m - 1]}`;
}

function daysUntil(iso) {
  if (!iso) return null;
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  const target = new Date(y, m - 1, d);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((target - today) / 86400000);
}

const DUE_TEXT = {
  en: { overdue: (n) => `Overdue by ${n} day${n === 1 ? "" : "s"}`, today: "Due today", tomorrow: "Due tomorrow", soon: (n) => `Due in ${n} days`, later: (d) => `Due ${d}`, paid: "Paid", none: "No bill yet" },
  ur_roman: { overdue: (n) => `${n} din se late`, today: "Aaj due hai", tomorrow: "Kal due hai", soon: (n) => `${n} din mein due`, later: (d) => `Akhri tareekh ${d}`, paid: "Ada ho gaya", none: "Abhi bill nahi" },
  ur: { overdue: (n) => `${n} دن سے تاخیر`, today: "آج واجب الادا", tomorrow: "کل واجب الادا", soon: (n) => `${n} دن میں واجب الادا`, later: (d) => `آخری تاریخ ${d}`, paid: "ادا ہو گیا", none: "ابھی بل نہیں" },
};

function dueStatus(latest) {
  const t = DUE_TEXT[billsLang()];
  if (!latest) return { text: t.none, cls: "pending" };
  if (latest.paid === true) return { text: t.paid, cls: "healthy" };
  const n = daysUntil(latest.due_date);
  if (n === null) return { text: t.later("-"), cls: "pending" };
  if (n < 0) return { text: t.overdue(-n), cls: "down" };
  if (n === 0) return { text: t.today, cls: "down" };
  if (n === 1) return { text: t.tomorrow, cls: "warn" };
  if (n <= 5) return { text: t.soon(n), cls: "warn" };
  return { text: t.later(billDay(latest.due_date, billsLang())), cls: "pending" };
}

// ---------- list ----------

async function loadBills() {
  applyBillsLanguage(billsLang());
  try {
    billsCache = await api("/api/bills/accounts");
  } catch (err) {
    toast(err.message);
    return;
  }
  renderBillsList();
}

function renderBillsList() {
  const list = document.getElementById("bills-list");
  const empty = document.getElementById("bills-empty");
  const count = document.getElementById("bills-count");
  if (!list) return;
  if (count) count.textContent = billsCache.length || "";
  if (!billsCache.length) {
    list.innerHTML = "";
    if (empty) empty.classList.remove("hidden");
    return;
  }
  if (empty) empty.classList.add("hidden");
  list.innerHTML = billsCache
    .map((a) => {
      const status = dueStatus(a.latest);
      const l = a.latest;
      const icon = BILL_CATEGORY_ICONS[a.category] || ICONS.bell;
      return `
      <div class="watchdog-card bill-card" onclick="openBillDetail(${a.id})" style="cursor:pointer;">
        <div class="watchdog-row1">
          <div class="watchdog-title-group">
            <span class="bill-cat-icon">${icon}</span>
            <span class="watchdog-name">${escapeHtml(a.nickname || a.company)}</span>
          </div>
          <span class="watchdog-status-badge ${status.cls}">${escapeHtml(status.text)}</span>
        </div>
        <div class="watchdog-chips-row">
          ${a.nickname ? `<span class="watchdog-chip">${escapeHtml(a.company)}</span>` : ""}
          ${l ? `<span class="watchdog-chip">${billMonthLabel(l.bill_month, true)}</span>` : ""}
          ${l && l.units !== null ? `<span class="watchdog-chip">${l.units} units</span>` : ""}
          ${a.last_error ? `<span class="watchdog-chip bill-chip-error" title="${escapeHtml(a.last_error)}">Last check failed</span>` : ""}
        </div>
        <div class="bill-amount-row">
          <span class="bill-amount">${l ? rs(l.amount_due) : "—"}</span>
          ${l && l.amount_after_due ? `<span class="bill-amount-sub">${rs(l.amount_after_due)} after due date</span>` : ""}
        </div>
      </div>`;
    })
    .join("");
}

// ---------- add dialog ----------

async function openAddBillModal() {
  try {
    if (!billProviders) billProviders = await api("/api/bills/providers");
  } catch (err) {
    toast(err.message);
    return;
  }
  const groups = {};
  billProviders.forEach((p) => (groups[p.category] = groups[p.category] || []).push(p));
  const categories = Object.keys(groups);
  const html = categories
    .map(
      (cat) => `
      <details class="provider-group"${categories.length === 1 ? " open" : ""}>
        <summary class="provider-group-title">
          <span class="provider-group-icon">${BILL_CATEGORY_ICONS[cat] || ""}</span>
          <span>${BILL_CATEGORY_LABELS[cat] || cat}</span>
          <span class="provider-group-count">${groups[cat].length}</span>
          <svg class="provider-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
        </summary>
        <div class="provider-grid">
          ${groups[cat].map((p) => `<button type="button" class="provider-btn" data-provider="${escapeHtml(p.id)}">${escapeHtml(p.name)}</button>`).join("")}
        </div>
      </details>`
    )
    .join("");
  openModal(
    `<p class="card-hint" style="margin:0 0 12px;">Choose the company that sends your bill.</p>${html || "<p>No companies available yet.</p>"}`,
    "Add a bill"
  );
  document.querySelectorAll(".provider-btn").forEach((btn) =>
    btn.addEventListener("click", () => openProviderForm(billProviders.find((p) => p.id === btn.dataset.provider)))
  );
}

// The dialog is drawn from the adapter's plain-data spec; adapters never supply HTML.
function openProviderForm(spec) {
  openModal(
    `
    ${spec.help ? `<p class="card-hint" style="margin:0 0 12px;">${escapeHtml(spec.help)}</p>` : ""}
    <div class="form-group">
      <label for="bf-number">${escapeHtml(spec.label)}</label>
      <input id="bf-number" inputmode="numeric" autocomplete="off" placeholder="${escapeHtml(spec.example)}" autofocus>
      ${spec.hint ? `<span class="card-hint">${escapeHtml(spec.hint)}</span>` : ""}
    </div>
    <div class="form-group">
      <label for="bf-nick">Name (optional)</label>
      <input id="bf-nick" maxlength="40" placeholder="e.g. Home or Shop">
    </div>
    <div id="bf-error" class="form-error hidden"></div>
    <div class="modal-actions">
      <button class="btn-ghost" onclick="openAddBillModal()">Back</button>
      <button class="btn-primary" id="bf-save"><span>Get my bill</span></button>
    </div>`,
    spec.name
  );
  const save = document.getElementById("bf-save");
  const numberInput = document.getElementById("bf-number");
  const submit = async () => {
    const number = numberInput.value.trim();
    const error = document.getElementById("bf-error");
    error.classList.add("hidden");
    if (!new RegExp("^(?:" + spec.pattern + ")$").test(number)) {
      error.textContent = `${spec.label}: ${spec.hint || "check the number"}`;
      error.classList.remove("hidden");
      return;
    }
    save.disabled = true;
    save.innerHTML = `${ICONS.spinner}<span>Fetching…</span>`;
    try {
      const res = await api("/api/bills/accounts", {
        method: "POST",
        body: JSON.stringify({ adapter_id: spec.id, consumer_number: number, nickname: document.getElementById("bf-nick").value }),
      });
      await afterFetch(res, spec);
    } catch (err) {
      save.disabled = false;
      save.innerHTML = "<span>Get my bill</span>";
      error.textContent = err.message;
      error.classList.remove("hidden");
    }
  };
  save.addEventListener("click", submit);
  numberInput.addEventListener("keydown", (e) => e.key === "Enter" && submit());
}

async function afterFetch(res, spec) {
  if (res.status === "challenge") return showChallenge(res, spec);
  closeModal();
  toast("Bill saved");
  await loadBills();
  openBillDetail(res.account.id);
}

// The portal asks for a code: show its image and let the person read it.
function showChallenge(res, spec) {
  const accountId = res.account.id;
  openModal(
    `
    <p class="card-hint" style="margin:0 0 12px;">The company's website wants to check you are a person. Type the code you see.</p>
    <div class="captcha-box"><img src="${res.image}" alt="Code to type"></div>
    <div class="form-group">
      <label for="cf-answer">${escapeHtml(res.prompt || "Code")}</label>
      <input id="cf-answer" autocomplete="off" autocapitalize="off" spellcheck="false" autofocus>
    </div>
    <div id="cf-error" class="form-error hidden"></div>
    <div class="modal-actions">
      <button class="btn-ghost" onclick="closeModal(); loadBills();">Later</button>
      <button class="btn-primary" id="cf-go"><span>Show my bill</span></button>
    </div>`,
    spec ? spec.name : "Type the code"
  );
  const go = document.getElementById("cf-go");
  const answer = document.getElementById("cf-answer");
  const submit = async () => {
    const error = document.getElementById("cf-error");
    error.classList.add("hidden");
    if (!answer.value.trim()) return;
    go.disabled = true;
    go.innerHTML = `${ICONS.spinner}<span>Checking…</span>`;
    try {
      const done = await api(`/api/bills/accounts/${accountId}/challenge`, {
        method: "POST",
        body: JSON.stringify({ token: res.token, answer: answer.value }),
      });
      await afterFetch(done, spec);
    } catch (err) {
      go.disabled = false;
      go.innerHTML = "<span>Show my bill</span>";
      error.textContent = err.message + " Close this and tap Refresh to get a new code.";
      error.classList.remove("hidden");
    }
  };
  go.addEventListener("click", submit);
  answer.addEventListener("keydown", (e) => e.key === "Enter" && submit());
}

// ---------- detail ----------

async function openBillDetail(id) {
  let data;
  try {
    data = await api(`/api/bills/accounts/${id}`);
  } catch (err) {
    toast(err.message);
    return;
  }
  const bill = data.bill;
  if (!bill) {
    openModal(
      `<p class="card-hint">No bill saved yet.</p>
       <div class="modal-actions"><button class="btn-danger" onclick="deleteBillAccount(${id})">Remove</button><button class="btn-primary" onclick="refreshBill(${id})">Fetch now</button></div>`,
      data.title
    );
    return;
  }
  const status = dueStatus(data.latest);
  openModal(
    `
    <div class="bill-hero">
      <div class="bill-hero-amount">${rs(bill.amount_due)}</div>
      <span class="watchdog-status-badge ${status.cls}">${escapeHtml(status.text)}</span>
    </div>
    <div class="watchdog-chips-row" style="margin-bottom:12px;">
      <span class="watchdog-chip">${billMonthLabel(data.latest.bill_month, true)}</span>
      ${bill.units !== null && bill.units !== undefined ? `<span class="watchdog-chip">${bill.units} units</span>` : ""}
      <span class="watchdog-chip">Due ${billDay(bill.due_date)}</span>
      ${bill.amount_after_due ? `<span class="watchdog-chip">${rs(bill.amount_after_due)} after</span>` : ""}
    </div>

    <div id="bill-explain" class="bill-explain"></div>

    <div class="bill-section-title">Breakdown</div>
    <div class="bill-table">${breakdownRows(bill)}</div>

    <div class="bill-section-title">History</div>
    <div class="seg-mini" role="radiogroup">
      <button type="button" class="theme-seg-btn active" data-chart="units">Units</button>
      <button type="button" class="theme-seg-btn" data-chart="billed">Amount</button>
    </div>
    <div id="bill-chart" class="bill-chart"></div>

    <div class="modal-actions bill-actions">
      <button class="btn-danger btn-sm" onclick="deleteBillAccount(${id})">${ICONS.trash}<span>Remove</span></button>
      <button class="btn-ghost btn-sm" onclick="renameBillAccount(${id}, this)" data-nick="${escapeHtml(data.nickname)}">${ICONS.edit}<span>Rename</span></button>
      <button class="btn-ghost btn-sm" id="bill-share-btn">${ICONS.send}<span>Share</span></button>
      <button class="btn-primary btn-sm" onclick="refreshBill(${id})">${ICONS.repeat}<span>Refresh</span></button>
    </div>
    <div class="card-hint" style="margin-top:8px;">Checked ${data.last_checked_at ? timeAgo(data.last_checked_at) : "never"}. Always confirm the amount with your company before paying.</div>`,
    data.title
  );

  const box = document.getElementById("bill-explain");
  const paint = () => {
    const lang = billsLang();
    box.dir = lang === "ur" ? "rtl" : "ltr";
    box.classList.toggle("bill-explain-ur", lang === "ur");
    box.innerHTML = (data.explain[lang] || []).map((p) => `<p>${escapeHtml(p)}</p>`).join("");
  };
  paint();
  box.addEventListener("langchange", paint);

  const drawChart = (key) => (document.getElementById("bill-chart").innerHTML = barChart(data.history, key));
  drawChart("units");
  document.querySelectorAll("[data-chart]").forEach((btn) =>
    btn.addEventListener("click", () => {
      document.querySelectorAll("[data-chart]").forEach((b) => b.classList.toggle("active", b === btn));
      drawChart(btn.dataset.chart);
    })
  );
  document.getElementById("bill-share-btn").addEventListener("click", () => shareBillImage(data));
}

function breakdownRows(bill) {
  const sign = { credit: "−", tax: "+", charge: "", arrears: "+", adjustment: "", total: "" };
  return bill.charges
    .filter((c) => c.amount !== 0 || c.kind === "total")
    .map((c) => {
      const cls = c.kind === "total" ? " bill-row-total" : "";
      return `<div class="bill-row${cls}"><span>${escapeHtml(c.label)}</span><span>${sign[c.kind] || ""} ${rs(c.amount)}</span></div>`;
    })
    .join("");
}

function barChart(history, key) {
  const rows = (history || []).slice(-12);
  const values = rows.map((r) => r[key]).filter((v) => v !== null && v !== undefined);
  if (!values.length) return `<p class="card-hint">No history yet.</p>`;
  const max = Math.max(...values) || 1;
  const width = 320, height = 150, left = 4, bottom = 22, gap = 4;
  const slot = (width - left) / rows.length;
  const bars = rows
    .map((r, i) => {
      const v = r[key] || 0;
      const h = Math.max(1, ((height - bottom - 16) * v) / max);
      const x = left + i * slot + gap / 2;
      const y = height - bottom - h;
      const label = key === "units" ? v : v >= 1000 ? Math.round(v / 100) / 10 + "k" : v;
      return `<rect x="${x}" y="${y}" width="${slot - gap}" height="${h}" rx="3" class="chart-bar"/>
        <text x="${x + (slot - gap) / 2}" y="${y - 3}" text-anchor="middle" class="chart-val">${label}</text>
        <text x="${x + (slot - gap) / 2}" y="${height - 6}" text-anchor="middle" class="chart-lbl">${BILL_MONTHS[Number(r.month.slice(5)) - 1][0]}</text>`;
    })
    .join("");
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Last ${rows.length} months">${bars}</svg>`;
}

// ---------- actions ----------

async function refreshBill(id) {
  try {
    toast("Checking…", ICONS.spinner);
    const res = await api(`/api/bills/accounts/${id}/refresh`, { method: "POST" });
    if (res.status === "challenge") {
      const account = billsCache.find((a) => a.id === id) || res.account;
      return showChallenge(res, { name: account.company });
    }
    toast("Updated");
    await loadBills();
    openBillDetail(id);
  } catch (err) {
    toast(err.message);
  }
}

async function deleteBillAccount(id) {
  if (!confirm("Remove this bill and its saved history?")) return;
  try {
    await api(`/api/bills/accounts/${id}`, { method: "DELETE" });
    closeModal();
    toast("Removed");
    loadBills();
  } catch (err) {
    toast(err.message);
  }
}

async function renameBillAccount(id, btn) {
  const name = prompt("Name for this bill", btn.dataset.nick || "");
  if (name === null) return;
  try {
    await api(`/api/bills/accounts/${id}`, { method: "PUT", body: JSON.stringify({ nickname: name }) });
    await loadBills();
    openBillDetail(id);
  } catch (err) {
    toast(err.message);
  }
}

// ---------- share image ----------

async function shareBillImage(data) {
  const bill = data.bill;
  const W = 1080, pad = 64;
  const lines = bill.charges.filter((c) => c.amount !== 0 && c.kind !== "total");
  const H = 560 + lines.length * 64;
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");
  const font = (px, weight = 400) => `${weight} ${px}px system-ui, -apple-system, "Segoe UI", sans-serif`;

  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = "#6366f1";
  ctx.fillRect(0, 0, W, 16);

  ctx.fillStyle = "#111827";
  ctx.font = font(44, 700);
  ctx.fillText(data.title, pad, 110);
  ctx.fillStyle = "#6b7280";
  ctx.font = font(32);
  ctx.fillText(`${billMonthLabel(data.latest.bill_month, true)}${bill.units != null ? "  ·  " + bill.units + " units" : ""}`, pad, 160);

  ctx.fillStyle = "#111827";
  ctx.font = font(96, 800);
  ctx.fillText(rs(bill.amount_due), pad, 290);
  ctx.fillStyle = "#6b7280";
  ctx.font = font(32);
  ctx.fillText(`Due ${billDay(bill.due_date)}${bill.amount_after_due ? "  ·  " + rs(bill.amount_after_due) + " after" : ""}`, pad, 345);

  ctx.strokeStyle = "#e5e7eb";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(pad, 390);
  ctx.lineTo(W - pad, 390);
  ctx.stroke();

  let y = 450;
  lines.forEach((c) => {
    ctx.fillStyle = "#374151";
    ctx.font = font(34);
    ctx.textAlign = "left";
    ctx.fillText(c.label, pad, y);
    ctx.textAlign = "right";
    ctx.fillText((c.kind === "credit" ? "− " : "") + rs(c.amount), W - pad, y);
    y += 64;
  });
  ctx.textAlign = "left";
  ctx.fillStyle = "#9ca3af";
  ctx.font = font(26);
  ctx.fillText("Made with Notifaybers · please confirm the amount with your company", pad, H - 40);

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  const file = new File([blob], `bill-${data.latest.bill_month}.png`, { type: "image/png" });
  try {
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      await navigator.share({ files: [file], title: data.title });
      return;
    }
  } catch (err) {
    if (err && err.name === "AbortError") return;
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = file.name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}

document.addEventListener("DOMContentLoaded", () => {
  const sw = document.getElementById("bills-feature-switch");
  if (sw) {
    sw.addEventListener("keydown", (e) => {
      if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        toggleBillsFeature(sw);
      }
    });
  }
  applyBillsLanguage(billsLang());
});
