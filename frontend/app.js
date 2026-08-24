/**
 * Speaklist — Voice Shopping Assistant (frontend)
 *
 * Capture (Web Speech API, with a typed fallback) → send the transcript to the
 * FastAPI /api/command endpoint → render the updated list, suggestions and any
 * search results. A tiny hash router switches between the landing page and the
 * app. Auth + "create order" are optional extras wired to the same backend.
 */

// --------------------------------------------------------------------------- //
// Config + state                                                              //
// --------------------------------------------------------------------------- //
const API_BASE = (window.APP_CONFIG && window.APP_CONFIG.API_BASE) || "";
const api = (path) => `${API_BASE}/api${path}`;

const state = {
  items: [],
  lang: "en-US",
  busy: false,
  token: localStorage.getItem("speaklist-token") || null,
  user: JSON.parse(localStorage.getItem("speaklist-user") || "null"),
  lastOrderId: null,
};

const CATEGORY_META = {
  produce: { emoji: "🥬", label: "Produce" },
  dairy: { emoji: "🥛", label: "Dairy" },
  "meat & seafood": { emoji: "🥩", label: "Meat & seafood" },
  bakery: { emoji: "🍞", label: "Bakery" },
  pantry: { emoji: "🫙", label: "Pantry" },
  frozen: { emoji: "🧊", label: "Frozen" },
  beverages: { emoji: "🧃", label: "Beverages" },
  snacks: { emoji: "🍿", label: "Snacks" },
  household: { emoji: "🧻", label: "Household" },
  "personal care": { emoji: "🧴", label: "Personal care" },
  baby: { emoji: "🍼", label: "Baby" },
  pet: { emoji: "🐾", label: "Pet" },
  other: { emoji: "🛒", label: "Other" },
};
const CATEGORY_ORDER = Object.keys(CATEGORY_META);

// --------------------------------------------------------------------------- //
// Elements                                                                    //
// --------------------------------------------------------------------------- //
const $ = (id) => document.getElementById(id);
const el = {
  viewLanding: $("view-landing"),
  viewApp: $("view-app"),
  // voice
  orb: $("mic-btn"),
  orbStatus: $("orb-status"),
  transcript: $("transcript"),
  reply: $("reply"),
  langSelect: $("lang-select"),
  engineDot: $("engine-dot"),
  commandForm: $("command-form"),
  commandInput: $("command-input"),
  commandSend: $("command-send"),
  speechNote: $("speech-note"),
  examples: $("examples"),
  // list / suggestions / search
  listBody: $("list-body"),
  listEmpty: $("list-empty"),
  listProgress: $("list-progress"),
  clearBtn: $("clear-btn"),
  orderBtn: $("order-btn"),
  suggestionsBody: $("suggestions-body"),
  searchPanel: $("search-panel"),
  searchBody: $("search-body"),
  searchClose: $("search-close"),
  // auth
  authBtn: $("auth-btn"),
  authModal: $("auth-modal"),
  loginPane: $("login-pane"),
  registerPane: $("register-pane"),
  loginForm: $("login-form"),
  registerForm: $("register-form"),
  // checkout
  checkoutModal: $("checkout-modal"),
  checkoutItems: $("checkout-items"),
  checkoutTotal: $("checkout-total"),
  placeOrderBtn: $("place-order-btn"),
  confirmModal: $("confirm-modal"),
  confirmOrderId: $("confirm-order-id"),
  downloadInvoiceBtn: $("download-invoice-btn"),
  confirmCloseBtn: $("confirm-close-btn"),
  // misc
  toasts: $("toasts"),
};

// --------------------------------------------------------------------------- //
// Helpers                                                                     //
// --------------------------------------------------------------------------- //
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );
}
function fmtQty(q) {
  const n = Number(q);
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, "");
}
function toast(message, type = "info") {
  const node = document.createElement("div");
  node.className = `toast toast-${type}`;
  node.textContent = message;
  el.toasts.appendChild(node);
  requestAnimationFrame(() => node.classList.add("show"));
  setTimeout(() => {
    node.classList.remove("show");
    setTimeout(() => node.remove(), 250);
  }, 3200);
}
function authHeaders() {
  return state.token ? { Authorization: `Bearer ${state.token}` } : {};
}
async function request(path, options = {}) {
  const res = await fetch(api(path), {
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body && body.detail) detail = body.detail;
    } catch (_) {
      /* non-JSON body */
    }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.status === 204 ? null : res.json();
}

// --------------------------------------------------------------------------- //
// Router                                                                      //
// --------------------------------------------------------------------------- //
function route() {
  const isApp = location.hash.replace(/^#/, "").startsWith("/app");
  el.viewLanding.hidden = isApp;
  el.viewApp.hidden = !isApp;
  window.scrollTo(0, 0);
  if (isApp) {
    // Load fresh data whenever the app view is opened.
    checkHealth();
    loadItems();
    refreshSuggestions();
  }
}

// --------------------------------------------------------------------------- //
// Theme (shared across both views)                                            //
// --------------------------------------------------------------------------- //
function initTheme() {
  const saved = localStorage.getItem("speaklist-theme") || "light";
  applyTheme(saved);
}
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  document.querySelectorAll(".theme-icon").forEach((n) => {
    n.textContent = theme === "dark" ? "☀️" : "🌙";
  });
}
function toggleTheme() {
  const next =
    document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
  localStorage.setItem("speaklist-theme", next);
  applyTheme(next);
}

// --------------------------------------------------------------------------- //
// Busy state                                                                  //
// --------------------------------------------------------------------------- //
function setBusy(busy) {
  state.busy = busy;
  el.commandSend.disabled = busy;
  el.commandInput.disabled = busy;
  el.orb.classList.toggle("is-thinking", busy);
  if (busy) {
    el.orb.classList.remove("is-listening");
    el.orbStatus.textContent = "Working…";
  } else if (!listening) {
    el.orbStatus.textContent = speechSupported ? "Tap to speak" : "Type a command";
  }
}

// --------------------------------------------------------------------------- //
// Command dispatch                                                            //
// --------------------------------------------------------------------------- //
async function sendCommand(transcript) {
  const text = (transcript || "").trim();
  if (!text || state.busy) return;

  el.transcript.textContent = text;
  el.transcript.classList.remove("is-empty", "is-interim");
  el.reply.textContent = "";
  setBusy(true);

  try {
    const lang = (state.lang || "en").split("-")[0];
    const result = await request("/command", {
      method: "POST",
      body: JSON.stringify({ transcript: text, language: lang }),
    });

    el.reply.textContent = result.message || "";
    if (result.intent === "search") renderSearch(result.search_results || [], text);

    await loadItems();
    renderSuggestions(result.suggestions || []);
  } catch (err) {
    el.reply.textContent = "";
    toast(err.message || "Something went wrong. Try again.", "error");
  } finally {
    setBusy(false);
  }
}

// --------------------------------------------------------------------------- //
// List                                                                        //
// --------------------------------------------------------------------------- //
async function loadItems() {
  try {
    state.items = await request("/items");
    renderList();
  } catch (err) {
    el.listBody.innerHTML = `<p class="loading">Couldn't load your list — ${esc(err.message)}</p>`;
  }
}

function renderList() {
  const items = state.items;
  const checkedCount = items.filter((i) => i.checked).length;

  el.clearBtn.hidden = items.length === 0;
  el.orderBtn.hidden = items.length === 0;
  el.listProgress.textContent = items.length ? `${checkedCount}/${items.length} got` : "";

  if (items.length === 0) {
    el.listBody.innerHTML = "";
    el.listEmpty.classList.remove("is-hidden");
    return;
  }
  el.listEmpty.classList.add("is-hidden");

  const groups = {};
  for (const item of items) {
    const cat = CATEGORY_META[item.category] ? item.category : "other";
    (groups[cat] ||= []).push(item);
  }

  el.listBody.innerHTML = CATEGORY_ORDER.filter((cat) => groups[cat])
    .map((cat) => {
      const meta = CATEGORY_META[cat];
      return `
        <div class="category-group">
          <div class="category-label">
            <span class="cat-emoji" aria-hidden="true">${meta.emoji}</span>${esc(meta.label)}
          </div>
          ${groups[cat].map(itemRow).join("")}
        </div>`;
    })
    .join("");
}

function itemRow(item) {
  const meta = [];
  if (item.quantity && Number(item.quantity) !== 1) meta.push(`×${fmtQty(item.quantity)}`);
  if (item.unit) meta.push(esc(item.unit));
  if (item.price != null) meta.push(`$${Number(item.price).toFixed(2)}`);
  const metaLine = meta.length ? `<div class="item-meta">${meta.join(" · ")}</div>` : "";

  return `
    <div class="item ${item.checked ? "is-checked" : ""}" data-id="${item.id}">
      <button class="check ${item.checked ? "is-checked" : ""}" data-action="check" data-id="${item.id}"
              aria-label="${item.checked ? "Uncheck" : "Check off"} ${esc(item.name)}" aria-pressed="${item.checked}">✓</button>
      <div class="item-body">
        <div class="item-name">${esc(item.name)}</div>
        ${metaLine}
      </div>
      <div class="qty">
        <button class="qty-btn" data-action="dec" data-id="${item.id}" aria-label="Decrease quantity">−</button>
        <span class="qty-val">${fmtQty(item.quantity || 1)}</span>
        <button class="qty-btn" data-action="inc" data-id="${item.id}" aria-label="Increase quantity">+</button>
      </div>
      <button class="remove-btn" data-action="remove" data-id="${item.id}" aria-label="Remove ${esc(item.name)}">🗑</button>
    </div>`;
}

async function patchItem(id, patch) {
  const updated = await request(`/items/${id}`, { method: "PATCH", body: JSON.stringify(patch) });
  const idx = state.items.findIndex((i) => i.id === id);
  if (idx !== -1) state.items[idx] = updated;
  renderList();
}

async function onListClick(e) {
  const btn = e.target.closest("[data-action]");
  if (!btn) return;
  const id = Number(btn.dataset.id);
  const item = state.items.find((i) => i.id === id);
  if (!item) return;

  try {
    if (btn.dataset.action === "check") {
      await patchItem(id, { checked: !item.checked });
    } else if (btn.dataset.action === "inc") {
      await patchItem(id, { quantity: (Number(item.quantity) || 1) + 1 });
    } else if (btn.dataset.action === "dec") {
      await patchItem(id, { quantity: Math.max(1, (Number(item.quantity) || 1) - 1) });
    } else if (btn.dataset.action === "remove") {
      await request(`/items/${id}`, { method: "DELETE" });
      state.items = state.items.filter((i) => i.id !== id);
      renderList();
      toast(`Removed ${item.name}`);
      refreshSuggestions();
    }
  } catch (err) {
    toast(err.message || "Couldn't update that item.", "error");
  }
}

async function clearList() {
  if (state.items.length === 0) return;
  try {
    await request("/items", { method: "DELETE" });
    state.items = [];
    renderList();
    toast("List cleared");
    refreshSuggestions();
  } catch (err) {
    toast(err.message || "Couldn't clear the list.", "error");
  }
}

async function addByName(name, extra = {}) {
  try {
    await request("/items", { method: "POST", body: JSON.stringify({ name, quantity: 1, ...extra }) });
    await loadItems();
    toast(`Added ${name}`, "success");
    refreshSuggestions();
  } catch (err) {
    toast(err.message || "Couldn't add that.", "error");
  }
}

// --------------------------------------------------------------------------- //
// Suggestions                                                                 //
// --------------------------------------------------------------------------- //
async function refreshSuggestions() {
  try {
    renderSuggestions(await request("/suggestions"));
  } catch (_) {
    /* non-critical */
  }
}
function renderSuggestions(suggestions) {
  if (!suggestions || suggestions.length === 0) {
    el.suggestionsBody.innerHTML =
      `<p class="loading">No suggestions right now — add a few items and they'll appear.</p>`;
    return;
  }
  el.suggestionsBody.innerHTML = suggestions
    .map(
      (s) => `
      <div class="suggestion">
        <div class="suggestion-body">
          <div class="suggestion-name">${esc(s.name)}</div>
          <div class="suggestion-reason">${esc(s.reason || "")}</div>
        </div>
        <span class="tag tag-${esc(s.type)}">${esc(s.type)}</span>
        <button class="add-btn" data-suggest="${esc(s.name)}" aria-label="Add ${esc(s.name)}">+</button>
      </div>`,
    )
    .join("");
}
function onSuggestionClick(e) {
  const btn = e.target.closest("[data-suggest]");
  if (btn) addByName(btn.dataset.suggest);
}

// --------------------------------------------------------------------------- //
// Search                                                                      //
// --------------------------------------------------------------------------- //
function renderSearch(results, query) {
  el.searchPanel.classList.remove("is-hidden");
  if (!results || results.length === 0) {
    el.searchBody.innerHTML = `<p class="loading">No products matched “${esc(query)}”.</p>`;
    return;
  }
  el.searchBody.innerHTML = results
    .map((p) => {
      const meta = [p.brand, p.size].filter(Boolean).map(esc).join(" · ");
      const payload = esc(JSON.stringify({ name: p.name, price: p.price, category: p.category }));
      return `
        <div class="result">
          <div class="result-body">
            <div class="result-name">${esc(p.name)}</div>
            <div class="result-meta">${meta}</div>
          </div>
          <span class="result-price">$${Number(p.price).toFixed(2)}</span>
          <button class="add-btn" data-result='${payload}' aria-label="Add ${esc(p.name)}">+</button>
        </div>`;
    })
    .join("");
}
function onSearchClick(e) {
  const btn = e.target.closest("[data-result]");
  if (!btn) return;
  try {
    const p = JSON.parse(btn.dataset.result);
    addByName(p.name, { price: p.price, category: p.category });
  } catch (_) {
    /* ignore */
  }
}

// --------------------------------------------------------------------------- //
// Speech recognition                                                          //
// --------------------------------------------------------------------------- //
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const speechSupported = Boolean(SpeechRecognition);
let recognition = null;
let listening = false;

function setupSpeech() {
  if (!speechSupported) {
    el.orbStatus.textContent = "Type a command";
    el.speechNote.textContent =
      "Voice input isn't supported in this browser. Type your commands below — everything still works.";
    el.speechNote.classList.remove("is-hidden");
    return;
  }

  recognition = new SpeechRecognition();
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;
  recognition.continuous = false;

  let finalText = "";

  recognition.onstart = () => {
    listening = true;
    finalText = "";
    el.orb.classList.add("is-listening");
    el.orb.setAttribute("aria-pressed", "true");
    el.orb.setAttribute("aria-label", "Stop listening");
    el.orbStatus.textContent = "Listening…";
    el.reply.textContent = "";
    el.transcript.textContent = "…";
    el.transcript.classList.remove("is-empty");
    el.transcript.classList.add("is-interim");
  };

  recognition.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const chunk = event.results[i][0].transcript;
      if (event.results[i].isFinal) finalText += chunk;
      else interim += chunk;
    }
    el.transcript.textContent = (finalText + interim).trim() || "…";
  };

  recognition.onerror = (event) => {
    if (event.error === "not-allowed" || event.error === "service-not-allowed") {
      toast("Microphone access is blocked. Allow it in your browser, or type instead.", "error");
    } else if (event.error === "no-speech") {
      toast("Didn't catch that — try again.", "info");
    } else if (event.error !== "aborted") {
      toast("Voice input hit a snag. You can type your command instead.", "error");
    }
  };

  recognition.onend = () => {
    listening = false;
    el.orb.classList.remove("is-listening");
    el.orb.setAttribute("aria-pressed", "false");
    el.orb.setAttribute("aria-label", "Start listening");
    el.transcript.classList.remove("is-interim");
    if (!state.busy) el.orbStatus.textContent = "Tap to speak";

    const text = finalText.trim();
    if (text) {
      sendCommand(text);
    } else if (el.transcript.textContent === "…") {
      el.transcript.textContent = "Say something like “add two avocados”";
      el.transcript.classList.add("is-empty");
    }
  };
}

function toggleListening() {
  if (!speechSupported || state.busy) {
    if (!speechSupported) el.commandInput.focus();
    return;
  }
  if (listening) {
    recognition.stop();
    return;
  }
  try {
    recognition.lang = state.lang;
    recognition.start();
  } catch (_) {
    /* start() throws if called twice quickly — ignore */
  }
}

// --------------------------------------------------------------------------- //
// Auth                                                                        //
// --------------------------------------------------------------------------- //
function openAuth(which = "login") {
  showAuthPane(which);
  el.authModal.classList.remove("is-hidden");
}
function closeAuth() {
  el.authModal.classList.add("is-hidden");
}
function showAuthPane(which) {
  el.loginPane.classList.toggle("is-hidden", which !== "login");
  el.registerPane.classList.toggle("is-hidden", which !== "register");
}
function setSession(token, user) {
  state.token = token;
  state.user = user;
  localStorage.setItem("speaklist-token", token);
  localStorage.setItem("speaklist-user", JSON.stringify(user));
  updateAuthUI();
}
function clearSession() {
  state.token = null;
  state.user = null;
  localStorage.removeItem("speaklist-token");
  localStorage.removeItem("speaklist-user");
  updateAuthUI();
}
function updateAuthUI() {
  if (state.user) {
    el.authBtn.textContent = `👤 ${String(state.user.full_name || "").split(" ")[0] || "Account"}`;
    el.authBtn.dataset.role = "user";
  } else {
    el.authBtn.textContent = "Sign in";
    el.authBtn.dataset.role = "guest";
  }
}
async function handleLogin(e) {
  e.preventDefault();
  try {
    const data = await request("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: $("login-email").value,
        password: $("login-password").value,
      }),
    });
    setSession(data.access_token, data.user);
    closeAuth();
    el.loginForm.reset();
    toast(`Signed in as ${data.user.full_name}`, "success");
  } catch (err) {
    toast(err.message || "Sign in failed.", "error");
  }
}
async function handleRegister(e) {
  e.preventDefault();
  try {
    const data = await request("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        full_name: $("register-name").value,
        email: $("register-email").value,
        password: $("register-password").value,
      }),
    });
    setSession(data.access_token, data.user);
    closeAuth();
    el.registerForm.reset();
    toast(`Welcome, ${data.user.full_name}!`, "success");
  } catch (err) {
    toast(err.message || "Couldn't create account.", "error");
  }
}
function onAuthBtn() {
  if (state.user) {
    clearSession();
    toast("Signed out");
  } else {
    openAuth("login");
  }
}

// --------------------------------------------------------------------------- //
// Checkout (turn the list into a priced order + invoice)                      //
// --------------------------------------------------------------------------- //
async function openCheckout() {
  if (state.items.length === 0) return;
  if (!state.user) {
    toast("Sign in to create an order and invoice.", "info");
    openAuth("login");
    return;
  }
  // Preview prices from the catalogue so the user sees a real total.
  let total = 0;
  const rows = await Promise.all(
    state.items.map(async (it) => {
      let price = it.price;
      if (price == null) {
        try {
          const matches = await request(`/search?query=${encodeURIComponent(it.name)}`);
          price = matches[0] ? matches[0].price : 3.99;
        } catch (_) {
          price = 3.99;
        }
      }
      const qty = Number(it.quantity) || 1;
      const sub = price * qty;
      total += sub;
      return `<div class="checkout-row"><span class="co-name">${esc(it.name)} ×${fmtQty(qty)}</span><span class="co-price">$${sub.toFixed(2)}</span></div>`;
    }),
  );
  el.checkoutItems.innerHTML = rows.join("");
  el.checkoutTotal.textContent = `$${total.toFixed(2)}`;
  el.checkoutModal.classList.remove("is-hidden");
}
async function placeOrder() {
  el.placeOrderBtn.disabled = true;
  el.placeOrderBtn.textContent = "Placing…";
  try {
    const order = await request("/list/checkout", { method: "POST" });
    state.lastOrderId = order.id;
    el.checkoutModal.classList.add("is-hidden");
    el.confirmOrderId.textContent = `#${String(order.id).padStart(6, "0")}`;
    el.confirmModal.classList.remove("is-hidden");
  } catch (err) {
    toast(err.message || "Checkout failed.", "error");
  } finally {
    el.placeOrderBtn.disabled = false;
    el.placeOrderBtn.textContent = "Place order";
  }
}
async function downloadInvoice() {
  if (!state.lastOrderId) return;
  try {
    const res = await fetch(api(`/orders/${state.lastOrderId}/invoice`), { headers: authHeaders() });
    if (!res.ok) throw new Error("Couldn't fetch the invoice.");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `invoice-${String(state.lastOrderId).padStart(6, "0")}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast("Invoice downloaded", "success");
  } catch (err) {
    toast(err.message || "Invoice download failed.", "error");
  }
}

// --------------------------------------------------------------------------- //
// Health                                                                      //
// --------------------------------------------------------------------------- //
async function checkHealth() {
  try {
    const health = await request("/health");
    if (health.llm_enabled) {
      el.engineDot.className = "engine-dot is-smart";
      el.engineDot.title = "Smart parsing on (LLM understands free-form phrases)";
    } else {
      el.engineDot.className = "engine-dot is-basic";
      el.engineDot.title = "Basic parsing (rule-based). Set GROQ_API_KEY for smarter understanding.";
    }
  } catch (_) {
    el.engineDot.className = "engine-dot is-down";
    el.engineDot.title = "Can't reach the service.";
  }
}

// --------------------------------------------------------------------------- //
// Wire up + init                                                              //
// --------------------------------------------------------------------------- //
function init() {
  initTheme();
  updateAuthUI();
  setupSpeech();

  // Theme toggles (both views)
  document.querySelectorAll("#theme-toggle, #theme-toggle-landing").forEach((b) =>
    b.addEventListener("click", toggleTheme),
  );

  // Language
  el.langSelect.value = state.lang;
  el.langSelect.addEventListener("change", () => {
    state.lang = el.langSelect.value;
  });

  // Voice + command bar
  el.orb.addEventListener("click", toggleListening);
  el.commandForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = el.commandInput.value.trim();
    if (!text) return;
    el.commandInput.value = "";
    sendCommand(text);
  });
  el.examples.addEventListener("click", (e) => {
    const chip = e.target.closest("[data-cmd]");
    if (chip) sendCommand(chip.dataset.cmd);
  });

  // List / suggestions / search
  el.listBody.addEventListener("click", onListClick);
  el.suggestionsBody.addEventListener("click", onSuggestionClick);
  el.searchBody.addEventListener("click", onSearchClick);
  el.clearBtn.addEventListener("click", clearList);
  el.orderBtn.addEventListener("click", openCheckout);
  el.searchClose.addEventListener("click", () => el.searchPanel.classList.add("is-hidden"));

  // Auth
  document.querySelectorAll("[data-auth-open]").forEach((b) =>
    b.addEventListener("click", (e) => {
      // On the app top bar, the same button doubles as sign-out when logged in.
      if (b.id === "auth-btn") onAuthBtn();
      else openAuth("login");
    }),
  );
  document.querySelectorAll("[data-auth-close]").forEach((b) => b.addEventListener("click", closeAuth));
  el.authModal.addEventListener("click", (e) => {
    if (e.target === el.authModal) closeAuth();
  });
  document.querySelectorAll("[data-show]").forEach((b) =>
    b.addEventListener("click", () => showAuthPane(b.dataset.show)),
  );
  el.loginForm.addEventListener("submit", handleLogin);
  el.registerForm.addEventListener("submit", handleRegister);

  // Checkout
  document.querySelectorAll("[data-checkout-close]").forEach((b) =>
    b.addEventListener("click", () => el.checkoutModal.classList.add("is-hidden")),
  );
  el.checkoutModal.addEventListener("click", (e) => {
    if (e.target === el.checkoutModal) el.checkoutModal.classList.add("is-hidden");
  });
  el.placeOrderBtn.addEventListener("click", placeOrder);
  el.downloadInvoiceBtn.addEventListener("click", downloadInvoice);
  el.confirmCloseBtn.addEventListener("click", () => el.confirmModal.classList.add("is-hidden"));

  // Keyboard shortcut: "/" focuses the type box in the app view.
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && !el.viewApp.hidden && document.activeElement !== el.commandInput) {
      e.preventDefault();
      el.commandInput.focus();
    }
    if (e.key === "Escape") {
      closeAuth();
      el.checkoutModal.classList.add("is-hidden");
      el.confirmModal.classList.add("is-hidden");
    }
  });

  // Router
  window.addEventListener("hashchange", route);
  route();
}

document.addEventListener("DOMContentLoaded", init);
