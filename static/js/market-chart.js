window.LucyMarket = (() => {
  let root = null;
  let chart = null;
  let series = null;
  let xAxis = null;
  let yAxis = null;
  let gaugeHand = null;
  let clockHand = null;
  let percentLabel = null;
  let currentSymbol = "BTC";
  let themeMode = "normal";
  let lastInsight = null;

  function formatPrice(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "N/A";
    if (n >= 1000) return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
    if (n >= 1) return n.toFixed(4);
    return n.toFixed(6);
  }

  function dispose() {
    if (root) {
      root.dispose();
      root = null;
      chart = null;
      series = null;
    }
  }

  function initGauge(containerRoot) {
    const gaugeContainer = containerRoot.container.children.push(
      am5.Container.new(containerRoot, {
        width: 130,
        height: 88,
        x: am5.p100,
        centerX: am5.p100,
        y: am5.p100,
        centerY: am5.p100,
        paddingRight: 12,
        paddingBottom: 12,
        layer: 100,
      })
    );

    gaugeContainer.children.push(
      am5radar.RadarChart.new(containerRoot, {
        width: am5.p100,
        height: 88,
        innerRadius: am5.percent(78),
        radius: am5.percent(100),
        startAngle: 180,
        endAngle: 360,
        centerY: am5.p100,
        y: am5.p100,
      })
    );

    const cursorAxis = gaugeContainer.children
      .getIndex(0)
      .xAxes.push(
        am5xy.ValueAxis.new(containerRoot, {
          min: 0,
          max: 100,
          strictMinMax: true,
          renderer: am5radar.AxisRendererCircular.new(containerRoot, {
            innerRadius: am5.percent(78),
            strokeOpacity: 0.1,
          }),
        })
      );

    gaugeHand = cursorAxis.makeDataItem({ value: 0 });
    clockHand = am5radar.ClockHand.new(containerRoot, {
      pinRadius: am5.percent(20),
      radius: am5.percent(100),
      bottomWidth: 5,
      layer: 50,
    });
    gaugeHand.set(
      "bullet",
      am5xy.AxisBullet.new(containerRoot, { sprite: clockHand })
    );
    cursorAxis.createAxisRange(gaugeHand);

    percentLabel = gaugeContainer.children.push(
      am5.Label.new(containerRoot, {
        text: "0%",
        fontSize: "13px",
        fontWeight: "800",
        fill: am5.color(0xffffff),
        centerX: am5.p50,
        x: am5.p50,
        y: am5.percent(82),
      })
    );
  }

  function ensureChart() {
    if (root) return;
    root = am5.Root.new("chartdiv");
    root.setThemes([
      am5themes_Animated.new(root),
      am5themes_Dark.new(root),
    ]);

    chart = root.container.children.push(
      am5xy.XYChart.new(root, {
        panX: true,
        panY: true,
        wheelX: "zoomX",
        wheelY: "zoomX",
        layout: root.verticalLayout,
        paddingTop: 8,
        paddingRight: 8,
        paddingLeft: 8,
        paddingBottom: 100,
      })
    );

    xAxis = chart.xAxes.push(
      am5xy.DateAxis.new(root, {
        baseInterval: { timeUnit: "minute", count: 1 },
        renderer: am5xy.AxisRendererX.new(root, {}),
        groupData: true,
      })
    );

    yAxis = chart.yAxes.push(
      am5xy.ValueAxis.new(root, {
        extraMin: 0.08,
        extraMax: 0.08,
        renderer: am5xy.AxisRendererY.new(root, {}),
        strictMinMax: false,
      })
    );

    initGauge(root);
  }

  function ensureSeries() {
    ensureChart();
    if (series) return;
    series = chart.series.push(
      am5xy.LineSeries.new(root, {
        name: currentSymbol,
        xAxis,
        yAxis,
        valueYField: "price",
        valueXField: "datetime",
        tooltip: am5.Tooltip.new(root, {
          pointerOrientation: "horizontal",
          getFillFromSprite: false,
          fill: am5.color(0x0f172a),
          labelText:
            "[bold]{name}[/]\nPrice: [bold]${valueY.formatNumber('#.#####')}[/]",
        }),
      })
    );
    series.get("tooltip").get("background").setAll({
      stroke: am5.color(0x3b82f6),
      strokeOpacity: 0.5,
    });
  }

  function setData(history, symbol) {
    ensureSeries();
    currentSymbol = symbol;
    series.set("name", symbol);
    series.data.setAll(history || []);

    const strokeColor =
      themeMode === "volatile" ? am5.color(0xef4444) : am5.color(0x3b82f6);
    series.set("stroke", strokeColor);
    series.set("fill", strokeColor);
  }

  function setInsight(insight) {
    if (!insight) return;
    lastInsight = insight;

    const probRaw = insight.probability;
    const probValue = Number.isFinite(Number(probRaw))
      ? Number(probRaw) * 100
      : 0;

    if (gaugeHand) {
      gaugeHand.animate({
        key: "value",
        to: probValue,
        duration: 800,
        easing: am5.ease.out(am5.ease.cubic),
      });
    }

    const prediction = insight.prediction || "Neutral";
    const color = am5.color(
      prediction === "Bullish" ? 0x4ade80 : 0xf87171
    );
    clockHand?.pin?.set("fill", color);
    clockHand?.hand?.set("fill", color);
    percentLabel?.setAll({
      text: `${Math.round(probValue)}%`,
      fill: color,
    });

    const badge = document.getElementById("insight-badge");
    if (badge) {
      badge.textContent = prediction;
    }
  }

  function setTheme(mode) {
    themeMode = mode;
    if (series) {
      const strokeColor =
        mode === "volatile" ? am5.color(0xef4444) : am5.color(0x3b82f6);
      series.set("stroke", strokeColor);
      series.set("fill", strokeColor);
    }
    const dash = document.getElementById("dashboard-root");
    if (dash) {
      dash.classList.toggle("theme-volatile", mode === "volatile");
    }
  }

  return {
    init({ symbol, history, insight }) {
      currentSymbol = symbol;
      ensureChart();
      setData(history, symbol);
      setInsight(insight);
    },
    updateHistory(history, symbol) {
      if (symbol) currentSymbol = symbol;
      setData(history, currentSymbol);
      if (lastInsight) setInsight(lastInsight);
    },
    setInsight,
    setTheme,
    dispose,
  };
})();
