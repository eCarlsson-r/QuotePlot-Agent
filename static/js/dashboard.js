window.LucyDashboard = (() => {
  let symbol = "BTC";
  let sessionId = "";
  let notificationsEnabled = false;
  let pollTimer = null;

  function showToast(message, type = "success") {
    const root = document.getElementById("toast-root");
    if (!root) return;
    const el = document.createElement("div");
    el.className =
      type === "error"
        ? "bg-red-900/90 text-red-100 border border-red-700 px-4 py-2 rounded-lg text-sm shadow-lg pointer-events-auto"
        : "bg-emerald-900/90 text-emerald-100 border border-emerald-700 px-4 py-2 rounded-lg text-sm shadow-lg pointer-events-auto";
    el.textContent = message;
    root.appendChild(el);
    setTimeout(() => el.remove(), 4000);
  }

  async function fetchJson(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`Request failed: ${path}`);
    return res.json();
  }

  async function syncMarket() {
    try {
      const [tickers, history] = await Promise.all([
        fetchJson("/api/market/tickers"),
        fetchJson(`/api/market/history/${symbol}`),
      ]);
      window.LucyMarket?.updateHistory(history, symbol);
      refreshTickerHxGet();
    } catch (err) {
      console.error("Dashboard sync error:", err);
    }
  }

  async function fetchLucyAnalysis() {
    try {
      const data = await fetchJson("/api/market/insight/" + symbol);
      if (!data.insight) return;
      const text = String(data.insight);
      const upper = text.toUpperCase();
      let prediction = "Neutral";
      if (upper.includes("BULLISH")) prediction = "Bullish";
      else if (upper.includes("BEARISH")) prediction = "Bearish";
      applyInsight(
        { prediction, probability: 0.5, trend_summary: text },
        symbol
      );
    } catch (err) {
      console.error("Lucy analysis error:", err);
    }
  }

  function refreshTickerHxGet() {
    const rows = document.getElementById("ticker-rows");
    const search = document.getElementById("token-search");
    if (!rows) return;
    const q = search?.value?.trim().toUpperCase() || "";
    rows.setAttribute(
      "hx-get",
      `/partials/ticker-rows?symbol=${encodeURIComponent(symbol)}&q=${encodeURIComponent(q)}`
    );
    if (typeof htmx !== "undefined") {
      htmx.process(rows);
      htmx.trigger(rows, "refresh");
    }
  }

  function updateStreakBadge(streak) {
    const badge = document.getElementById("streak-badge");
    const narrative = document.getElementById("streak-narrative");
    if (!badge) return;
    badge.innerHTML = "";
    if (narrative) narrative.classList.add("hidden");

    if (streak >= 2) {
      badge.innerHTML = `<span class="inline-flex items-center rounded-md bg-emerald-900/40 border border-emerald-600/30 px-2 py-1 text-[10px] font-medium text-emerald-300">🔥 ${streak} win streak</span>`;
    } else if (streak <= -2) {
      // De-emphasize loss streak for demos; narrative hook lives in the subtle footer line
      if (narrative) {
        narrative.classList.remove("hidden");
        narrative.textContent =
          "Offline calibration phase — activate Bright Data live feeds to sharpen accuracy.";
      }
    }
  }

  function filterTickerList() {
    const input = document.getElementById("token-search");
    const q = input?.value.trim().toUpperCase() || "";
    let firstVisible = null;

    document.querySelectorAll(".ticker-row").forEach((row) => {
      const sym = row.dataset.symbol || "";
      const match = !q || sym.includes(q);
      row.classList.toggle("hidden", !match);
      row.classList.remove("ring-1", "ring-blue-400/60");
      if (match && !firstVisible) firstVisible = row;
    });

    if (firstVisible) {
      firstVisible.classList.add("ring-1", "ring-blue-400/60");
      firstVisible.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
    return firstVisible;
  }

  function selectSymbol(next) {
    symbol = next.toUpperCase();
    const root = document.getElementById("dashboard-root");
    if (root) root.dataset.symbol = symbol;
    const hidden = document.getElementById("chat-symbol");
    if (hidden) hidden.value = symbol;
    document.querySelectorAll(".ticker-row").forEach((row) => {
      row.classList.toggle(
        "bg-blue-600/30",
        row.dataset.symbol === symbol
      );
    });
    window.LucyThoughtStream?.setSymbol(symbol);
    syncMarket();
    fetchLucyAnalysis();
    const url = new URL(window.location.href);
    url.searchParams.set("symbol", symbol);
    window.history.replaceState({}, "", url);
  }

  function bindTickerClicks() {
    document.getElementById("ticker-rows")?.addEventListener("click", (e) => {
      const row = e.target.closest(".ticker-row");
      if (!row?.dataset.symbol) return;
      selectSymbol(row.dataset.symbol);
    });
  }

  function bindSearch() {
    const input = document.getElementById("token-search");
    if (!input) return;

    let debounce;
    input.addEventListener("input", () => {
      filterTickerList();
      clearTimeout(debounce);
      debounce = setTimeout(refreshTickerHxGet, 250);
    });

    input.addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      e.preventDefault();
      const first =
        filterTickerList() ||
        document.querySelector(".ticker-row:not(.hidden)");
      if (first?.dataset.symbol) selectSymbol(first.dataset.symbol);
    });
  }

  async function refreshBrightDataBadge() {
    const el = document.getElementById("brightdata-status-badge");
    if (!el) return;
    try {
      const data = await fetchJson("/api/agent/brightdata-status");
      el.textContent = data.label || "Bright Data";
      el.classList.toggle("bd-connected", !!data.connected);
      el.classList.toggle("bd-offline", !data.connected);
    } catch {
      el.textContent = "Bright Data: Unavailable";
      el.classList.add("bd-offline");
    }
  }

  function scrollChatToBottom() {
    const el = document.getElementById("chat-messages");
    if (!el) return;
    requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight;
    });
  }

  function bindChatForm() {
    const form = document.getElementById("chat-form");
    const input = document.getElementById("chat-input");
    const chatMessages = document.getElementById("chat-messages");
    if (!form || !input) return;
    form.addEventListener("htmx:beforeRequest", () => {
      document.getElementById("chat-symbol").value = symbol;
    });
    form.addEventListener("htmx:afterRequest", () => {
      input.value = "";
      scrollChatToBottom();
    });
    chatMessages?.addEventListener("click", (e) => {
      const btn = e.target.closest(".top-mover-btn");
      if (btn?.dataset.symbol) selectSymbol(btn.dataset.symbol);
    });
    document.body.addEventListener("htmx:afterSwap", (evt) => {
      if (evt.detail.target?.id === "chat-messages") {
        window.LucyTypewriter.scan(evt.detail.target);
        scrollChatToBottom();
      }
    });
  }

  function bindExport() {
    document.getElementById("export-report-btn")?.addEventListener("click", async () => {
      const el = document.getElementById("report-area");
      if (!el || typeof html2canvas === "undefined") return;
      try {
        const canvas = await html2canvas(el, {
          backgroundColor: "#020617",
          scale: 2,
          logging: false,
          useCORS: true,
        });
        const link = document.createElement("a");
        link.href = canvas.toDataURL("image/png");
        link.download = `Lucy_Analysis_${symbol}_${new Date().toISOString().slice(0, 10)}.png`;
        link.click();
        showToast("Analysis report saved to downloads!");
      } catch (err) {
        console.error(err);
        showToast("Failed to generate report.", "error");
      }
    });
  }

  function bindNotifications() {
    document.getElementById("enable-notifications")?.addEventListener("click", async () => {
      if (!("Notification" in window)) return;
      const permission = await Notification.requestPermission();
      if (permission === "granted") {
        notificationsEnabled = true;
        new Notification("🎯 Lucy Alerts Active", {
          body: "You will now receive high-confidence trade signals.",
        });
      }
    });
    if ("Notification" in window && Notification.permission === "granted") {
      notificationsEnabled = true;
    }
  }

  function bindLogToggle() {
    const btn = document.getElementById("toggle-logs");
    const wrap = document.getElementById("thought-stream-wrap");
    const label = document.getElementById("toggle-logs-label");
    btn?.addEventListener("click", () => {
      const collapsed = wrap?.classList.toggle("h-0");
      wrap?.classList.toggle("opacity-0", collapsed);
      wrap?.classList.toggle("pointer-events-none", collapsed);
      if (label) label.textContent = collapsed ? "Show Internal" : "Hide Internal";
    });
  }

  return {
    init({ symbol: sym, history, insight, sessionId: sid }) {
      symbol = sym;
      sessionId = sid;
      window.LucyMarket.init({ symbol, history, insight });
      window.LucyThoughtStream.init(symbol);
      window.LucyTypewriter.scan();
      bindTickerClicks();
      bindSearch();
      bindChatForm();
      bindExport();
      bindNotifications();
      bindLogToggle();
      scrollChatToBottom();
      applyInsight(insight, symbol);
      syncMarket();
      refreshBrightDataBadge();
      pollTimer = setInterval(syncMarket, 5000);
      setInterval(refreshBrightDataBadge, 60000);
      document.body.addEventListener("htmx:afterSwap", (evt) => {
        if (evt.detail.target?.id === "ticker-rows") {
          bindTickerClicks();
          filterTickerList();
        }
      });
    },

    applyInsight(insight, sym) {
      if (sym && sym.toUpperCase() !== symbol) {
        selectSymbol(sym);
      }
      window.LucyMarket?.setInsight(insight);
      const root = document.getElementById("dashboard-root");
      if (root) root.dataset.insight = JSON.stringify(insight);
    },

    applyStats(stats) {
      const wr = document.getElementById("stat-win-rate");
      const total = document.getElementById("stat-total");
      if (wr) wr.textContent = `${stats.win_rate}%`;
      if (total) total.textContent = stats.total_trades;
      updateStreakBadge(stats.streak);
    },

    maybeNotify(alert) {
      if (!notificationsEnabled || !alert) return;
      if ((alert.confidence || 0) < 0.9) return;
      new Notification(`🚀 High Confidence Alert: ${alert.symbol}`, {
        body: `Lucy is ${Math.round(alert.confidence * 100)}% sure of a ${alert.sentiment} move!`,
        icon: "/static/logo.png",
      });
    },
  };
})();
