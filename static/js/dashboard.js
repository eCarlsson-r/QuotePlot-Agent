class LucyDashboardTerminal {
  constructor() {
    this.symbol = "BTC";
    this.sessionId = "";
    this.notificationsEnabled = false;
    this.pollTimer = null;
  }

  showToast(message, type = "success") {
    const root = document.getElementById("toast-root");
    if (!root) return;
    const el = document.createElement("div");
    el.className = type === "error"
        ? "bg-red-900/90 text-red-100 border border-red-700 px-4 py-2 rounded-lg text-sm shadow-lg"
        : "bg-emerald-900/90 text-emerald-100 border border-emerald-700 px-4 py-2 rounded-lg text-sm shadow-lg";
    el.textContent = message;
    root.appendChild(el);
    setTimeout(() => el.remove(), 4000);
  }

  async fetchJson(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`Request failed: ${path}`);
    return res.json();
  }

  async syncMarket() {
    try {
      const [tickers, history] = await Promise.all([
        this.fetchJson("/api/market/tickers"),
        this.fetchJson(`/api/market/history/${this.symbol}`),
      ]);
      window.LucyMarket?.updateHistory(history, this.symbol);
      this.refreshTickerHxGet();
    } catch (err) {
      console.error("Dashboard sync error:", err);
    }
  }

  async fetchLucyAnalysis() {
    try {
      const data = await this.fetchJson("/api/market/insight/" + this.symbol);
      if (!data.insight) return;
      const text = String(data.insight);
      const upper = text.toUpperCase();
      let prediction = "Neutral";
      if (upper.includes("BULLISH")) prediction = "Bullish";
      else if (upper.includes("BEARISH")) prediction = "Bearish";
      
      this.applyInsight({ prediction, probability: 0.5, trend_summary: text }, this.symbol);
    } catch (err) {
      console.error("Lucy analysis error:", err);
    }
  }

  refreshTickerHxGet() {
    const rows = document.getElementById("ticker-rows");
    const search = document.getElementById("token-search");
    if (!rows) return;
    const q = search?.value?.trim().toUpperCase() || "";
    rows.setAttribute(
      "hx-get",
      `/partials/ticker-rows?symbol=${encodeURIComponent(this.symbol)}&q=${encodeURIComponent(q)}`
    );
    if (typeof htmx !== "undefined") {
      htmx.process(rows);
      htmx.trigger(rows, "refresh");
    }
  }

  updateStreakBadge(streak) {
    const badge = document.getElementById("streak-badge");
    const narrative = document.getElementById("streak-narrative");
    if (!badge) return;
    badge.innerHTML = "";
    if (narrative) narrative.classList.add("hidden");

    if (streak >= 2) {
      badge.innerHTML = `<span class="inline-flex items-center rounded-md bg-emerald-900/40 border border-emerald-600/30 px-2 py-1 text-[10px] font-medium text-emerald-300">🔥 ${streak} win streak</span>`;
    } else if (streak <= -2 && narrative) {
      narrative.classList.remove("hidden");
      narrative.textContent = "Offline calibration phase — activate Bright Data live feeds to sharpen accuracy.";
    }
  }

  filterTickerList() {
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
      firstVisible.scrollIntoView({ block: "center", behavior: "smooth" });
    }
    return firstVisible;
  }

  selectSymbol(next) {
    this.symbol = next.toUpperCase();
    const root = document.getElementById("dashboard-root");
    if (root) root.dataset.symbol = this.symbol;
    const hidden = document.getElementById("chat-symbol");
    if (hidden) hidden.value = this.symbol;
    
    document.querySelectorAll(".ticker-row").forEach((row) => {
      row.classList.toggle("bg-blue-600/30", row.dataset.symbol === this.symbol);
    });
    
    window.LucyThoughtStream?.setSymbol(this.symbol);
    this.syncMarket();
    this.fetchLucyAnalysis();
    
    const url = new URL(window.location.href);
    url.searchParams.set("symbol", this.symbol);
    window.history.replaceState({}, "", url);
  }

  bindTickerClicks() {
    document.getElementById("ticker-rows")?.addEventListener("click", (e) => {
      const row = e.target.closest(".ticker-row");
      if (!row?.dataset.symbol) return;
      this.selectSymbol(row.dataset.symbol);
    });
  }

  bindSearch() {
    const input = document.getElementById("token-search");
    if (!input) return;

    let debounce;
    input.addEventListener("input", () => {
      this.filterTickerList();
      clearTimeout(debounce);
      debounce = setTimeout(() => this.refreshTickerHxGet(), 250);
    });

    input.addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      e.preventDefault();
      const first = this.filterTickerList() || document.querySelector(".ticker-row:not(.hidden)");
      if (first?.dataset.symbol) this.selectSymbol(first.dataset.symbol);
    });
  }

  async refreshBrightDataBadge() {
    const el = document.getElementById("brightdata-status-badge");
    if (!el) return;
    try {
      const data = await this.fetchJson("/api/agent/brightdata-status");
      el.textContent = data.label || "Bright Data";
      el.classList.toggle("bd-connected", !!data.connected);
      el.classList.toggle("bd-offline", !data.connected);
    } catch {
      el.textContent = "Bright Data: Unavailable";
      el.classList.add("bd-offline");
    }
  }

  scrollChatToBottom() {
    const el = document.getElementById("chat-messages");
    if (!el) return;
    requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight;
    });
  }

  bindChatForm() {
    const form = document.getElementById("chat-form");
    const input = document.getElementById("chat-input");
    const chatMessages = document.getElementById("chat-messages");
    if (!form || !input) return;
    
    form.addEventListener("htmx:beforeRequest", () => {
      document.getElementById("chat-symbol").value = this.symbol;
    });
    form.addEventListener("htmx:afterRequest", () => {
      input.value = "";
      this.scrollChatToBottom();
    });
    chatMessages?.addEventListener("click", (e) => {
      const btn = e.target.closest(".top-mover-btn");
      if (btn?.dataset.symbol) this.selectSymbol(btn.dataset.symbol);
    });

    // 🌟 UNBREAKABLE UNIFORM PARSER: Handles both plain prose text and numbered asset lists perfectly
    chatMessages?.addEventListener("htmx:afterSwap", (evt) => {
      const targets = chatMessages.querySelectorAll(".typewriter-target");
      if (targets.length > 0) {
        const newestTarget = targets[targets.length - 1];
        
        // 1. Extract the full raw markdown string directly from the backend's data attribute
        let rawMarkdown = newestTarget.getAttribute("data-text");
        
        if (rawMarkdown && typeof marked !== "undefined") {
          marked.setOptions({
            mangle: false,
            headerIds: false,
            breaks: true
          });

          // 2. Clean up hidden list spacing anomalies from the raw string stream
          rawMarkdown = rawMarkdown.replace(/\u00a0/g, " ");
          rawMarkdown = rawMarkdown.replace(/hover=\s*["']\s*bg-blue-500\/50\s*["']/g, "");

          // 3. Turn the raw Markdown text into beautiful, finalized HTML elements instantly
          const renderedHTML = marked.parse(rawMarkdown);

          // 4. Update the data-text attribute with our clean, star-free HTML 
          // This ensures your typewriter engine prints finished HTML tags rather than raw symbols!
          newestTarget.setAttribute("data-text", renderedHTML);
          
          // Fallback: If your typewriter breaks on raw HTML tags, you can inject it directly:
          // newestTarget.innerHTML = renderedHTML;
        }
      }

      // 5. Fire your typewriter scan to print out the clean elements smoothly
      if (window.LucyTypewriter) {
        window.LucyTypewriter.scan(chatMessages);
      }

      // 6. Enforce Tailwind list styles to any list blocks present in the container
      setTimeout(() => {
        const textContainers = chatMessages.querySelectorAll(".prose");
        chatMessages.querySelectorAll(".top-mover-btn").forEach(btn => {
          // Explicitly ensure all design system standards are active
          btn.classList.add(
            "px-2", "py-1", "mx-1", 
            "bg-blue-600/30", "border", "border-blue-500/50", 
            "rounded", "text-xs", "transition-all", "font-mono",
            "hover:bg-blue-500/50" // Safe from the markdown compiler here!
          );
        });
        
        const newestBubble = textContainers[textContainers.length - 1];
        if (newestBubble) {
          newestBubble.querySelectorAll("ol").forEach(ol => {
            ol.classList.add("list-decimal", "pl-6", "my-3", "space-y-2", "text-slate-200");
          });
          newestBubble.querySelectorAll("ul").forEach(ul => {
            ul.classList.add("list-disc", "pl-6", "my-3", "space-y-2", "text-slate-200");
          });
        }
        this.scrollChatToBottom();
      }, 100);
    });
  }

  bindExport() {
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
        link.download = `Lucy_Analysis_${this.symbol}_${new Date().toISOString().slice(0, 10)}.png`;
        link.click();
        this.showToast("Analysis report saved to downloads!");
      } catch (err) {
        console.error(err);
        this.showToast("Failed to generate report.", "error");
      }
    });
  }

  bindNotifications() {
    document.getElementById("enable-notifications")?.addEventListener("click", async () => {
      if (!("Notification" in window)) return;
      const permission = await Notification.requestPermission();
      if (permission === "granted") {
        this.notificationsEnabled = true;
        new Notification("🎯 Lucy Alerts Active", {
          body: "You will now receive high-confidence trade signals.",
        });
      }
    });
    if ("Notification" in window && Notification.permission === "granted") {
      this.notificationsEnabled = true;
    }
  }

  bindLogToggle() {
    const btn = document.getElementById("toggle-logs");
    const wrap = document.getElementById("thought-stream-wrap");
    const label = document.getElementById("toggle-logs-label");
    btn?.addEventListener("click", () => {
      const collapsed = wrap?.classList.toggle("h-0");
      if (collapsed) wrap?.classList.remove("h-36");
      else wrap?.classList.add("h-36");
      wrap?.classList.toggle("opacity-0", collapsed);
      wrap?.classList.toggle("pointer-events-none", collapsed);
      if (label) label.textContent = collapsed ? "Show Internal" : "Hide Internal";
    });
  }

  init({ symbol: sym, history, insight, sessionId: sid }) {
    this.symbol = sym;
    this.sessionId = sid;
    window.LucyMarket.init({ symbol: this.symbol, history, insight });
    window.LucyThoughtStream.init(this.symbol);
    window.LucyTypewriter.scan();
    
    this.bindTickerClicks();
    this.bindSearch();
    this.bindChatForm();
    this.bindExport();
    this.bindNotifications();
    this.bindLogToggle();
    this.scrollChatToBottom();
    
    this.applyInsight(insight, this.symbol);
    this.syncMarket();
    this.refreshBrightDataBadge();
    
    // Highlight initial row
    document.querySelectorAll(".ticker-row").forEach((row) => {
      const isSelected = row.dataset.symbol === this.symbol;
      row.classList.toggle("bg-blue-600/30", isSelected);
      
      // 🌟 NEW: Center the default token on application startup
      if (isSelected) {
        row.scrollIntoView({ block: "center", behavior: "smooth" });
      }
    });

    this.pollTimer = setInterval(() => this.syncMarket(), 5000);
    setInterval(() => this.refreshBrightDataBadge(), 60000);

    const tickerContainer = document.getElementById("ticker-table");
    tickerContainer?.addEventListener("htmx:afterSwap", (evt) => {
      this.bindTickerClicks();
      this.filterTickerList();
      
      // 1. Re-apply the active visual background color classes smoothly
      document.querySelectorAll(".ticker-row").forEach((row) => {
        row.classList.toggle("bg-blue-600/30", row.dataset.symbol === this.symbol);
      });

      // 🌟 2. AUTOMATIC SCROLL FIX: Find the selected element and bring it into view!
      const activeRow = document.querySelector(`.ticker-row[data-symbol="${this.symbol}"]`);
      if (activeRow) {
        activeRow.scrollIntoView({
          block: "center",    // Prevents jumping the whole browser page down
          behavior: "smooth"   // Adds a clean, natural slider slide transition animation
        });
      }
    });
  }

  applyInsight(insight, sym) {
    if (sym && sym.toUpperCase() !== this.symbol) {
      this.selectSymbol(sym);
    }
    window.LucyMarket?.setInsight(insight);
    const root = document.getElementById("dashboard-root");
    if (root) root.dataset.insight = JSON.stringify(insight);
  }

  applyStats(stats) {
    const wr = document.getElementById("stat-win-rate");
    const total = document.getElementById("stat-total");
    if (wr) wr.textContent = `${stats.win_rate}%`;
    if (total) total.textContent = stats.total_trades;
    this.updateStreakBadge(stats.streak);
  }

  maybeNotify(alert) {
    if (!this.notificationsEnabled || !alert) return;
    if ((alert.confidence || 0) < 0.9) return;
    new Notification(`🚀 High Confidence Alert: ${alert.symbol}`, {
      body: `Lucy is ${Math.round(alert.confidence * 100)}% sure of a ${alert.sentiment} move!`,
      icon: "/static/favicon.svg",
    });
  }
}

// Global instantiation block
window.LucyDashboard = new LucyDashboardTerminal();
