window.LucyThoughtStream = (() => {
  let ws = null;
  let selectedSymbol = "BTC";
  const masterLogs = {};
  const queue = [];
  let isTyping = false;

  function statusEl() {
    return {
      label: document.getElementById("ws-status"),
      dot: document.getElementById("ws-indicator"),
    };
  }

  function setStatus(status) {
    const { label, dot } = statusEl();
    const colors = {
      online: "#00ff41",
      connecting: "#ffcc00",
      offline: "#ff3b30",
    };
    const color = colors[status] || colors.offline;
    if (label) label.textContent = status.toUpperCase();
    if (dot) {
      dot.style.backgroundColor = color;
      dot.style.boxShadow = `0 0 8px ${color}`;
    }
  }

  function logStyle(content) {
    if (content.startsWith("[ERROR]")) return { color: "#ff3b30", fontWeight: "bold" };
    if (content.startsWith("[SUCCESS]")) return { color: "#00ff41" };
    if (content.startsWith("[WARN]")) return { color: "#ffcc00" };
    return { color: "#00d4ff" };
  }

  function appendLog(text) {
    const feed = document.getElementById("thought-log-feed");
    if (!feed) return;

    const row = document.createElement("div");
    row.className = "mb-1";
    Object.assign(row.style, logStyle(text));
    row.innerHTML = `<span class="opacity-50 mr-2">&gt;</span><span class="log-text"></span>`;
    feed.appendChild(row);

    const target = row.querySelector(".log-text");
    const clean = text.replace(/\[.*?\] /, "");
    window.LucyTypewriter.run(target, clean, 15, () => {
      isTyping = false;
      processQueue();
    });

    while (feed.children.length > 20) {
      feed.removeChild(feed.firstChild);
    }
    row.scrollIntoView({ behavior: "smooth", block: "end" });
  }

  function processQueue() {
    if (isTyping || queue.length === 0) return;
    const next = queue.shift();
    if (next) {
      isTyping = true;
      appendLog(next);
    }
  }

  function enqueue(text) {
    queue.push(text);
    processQueue();
  }

  function connect() {
    if (ws) return;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/thoughts`;
    setStatus("connecting");
    ws = new WebSocket(url);

    ws.onopen = () => setStatus("online");
    ws.onclose = () => {
      setStatus("offline");
      ws = null;
      setTimeout(connect, 3000);
    };
    ws.onerror = () => setStatus("offline");

    ws.onmessage = (event) => {
      try {
        const outer = JSON.parse(event.data);
        const data = JSON.parse(outer.content);
        setStatus("online");

        if (data.type === "insight_update" && data.symbol === selectedSymbol) {
          window.LucyDashboard?.applyInsight(data, data.symbol);
          const volatile =
            data.prediction === "Bearish" && (data.probability || 0) > 0.85;
          window.LucyMarket?.setTheme(volatile ? "volatile" : "normal");
        } else if (data.type === "agent_stats" && data.symbol === selectedSymbol) {
          window.LucyDashboard?.applyStats(data);
        }

        if (data.type === "insight_update") {
          const sym = data.symbol;
          const text = data.insight_text;
          if (!masterLogs[sym]) masterLogs[sym] = [];
          masterLogs[sym].push(text);
          if (masterLogs[sym].length > 50) masterLogs[sym].shift();
          if (sym === selectedSymbol) enqueue(text);
        } else if (data.content) {
          enqueue(data.content);
        }
      } catch (e) {
        console.error("WS Error:", e);
        setStatus("offline");
      }
    };
  }

  return {
    init(symbol) {
      selectedSymbol = symbol;
      connect();
    },
    setSymbol(symbol) {
      selectedSymbol = symbol;
      const feed = document.getElementById("thought-log-feed");
      if (feed) feed.innerHTML = "";
      queue.length = 0;
      isTyping = false;
      (masterLogs[symbol] || []).slice(-20).forEach((log) => enqueue(log));
    },
  };
})();
