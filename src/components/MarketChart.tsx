"use client";
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import * as am5 from "@amcharts/amcharts5";
import * as am5xy from "@amcharts/amcharts5/xy";
import * as am5radar from "@amcharts/amcharts5/radar";
import am5themes_Animated from "@amcharts/amcharts5/themes/Animated";
import am5themes_Dark from "@amcharts/amcharts5/themes/Dark";
import { MarketData, TickerInfo } from '@/types/market';

const MarketChart = ({selectedSymbol, setSelectedSymbol, insight, setInsight}: MarketData) => {
  const [tickerData, setTickerData] = useState<Record<string, TickerInfo>>({});
  const [lastSync, setLastSync] = useState<string>("");
  const [syncProgress, setSyncProgress] = useState(0);

  // Change this Ref
  const seriesRef = useRef<am5xy.LineSeries | null>(null);
  const chartRef = useRef<am5xy.XYChart | null>(null);
  const rootRef = useRef<am5.Root | null>(null);
  const xAxisRef = useRef<am5xy.DateAxis<am5xy.AxisRenderer> | null>(null);
  const yAxisRef = useRef<am5xy.ValueAxis<am5xy.AxisRenderer> | null>(null);
  const gaugeHandRef = useRef<am5.DataItem<am5xy.IValueAxisDataItem> | null>(null);
  const clockHandRef = useRef<am5radar.ClockHand | null>(null);
  const percentLabelRef = useRef<am5.Label | null>(null);

  // HELPER: Format currency
  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  // CHART INITIALIZATION (Runs ONCE)
  useLayoutEffect(() => {
    const root = am5.Root.new("chartdiv");
    root.setThemes([am5themes_Animated.new(root), am5themes_Dark.new(root)]);
    
    const chart = root.container.children.push(
      am5xy.XYChart.new(root, {
        panX: true, panY: true, wheelX: "zoomX", wheelY: "zoomX",
        layout: root.verticalLayout
      })
    );

    // Create Axes
    const xAxis = chart.xAxes.push(am5xy.DateAxis.new(root, {
      baseInterval: { timeUnit: "minute", count: 1 },
      renderer: am5xy.AxisRendererX.new(root, {}),
      // These settings ensure the axis "follows" the data
      startLocation: 0.5,
      endLocation: 0.5,
      groupData: true // Helps if history has many points
    }));

    const yAxis = chart.yAxes.push(
      am5xy.ValueAxis.new(root, {
        extraMin: 0.1, 
        extraMax: 0.1,
        renderer: am5xy.AxisRendererY.new(root, {}),
        // This allows the axis to "tighten" around the price
        strictMinMax: false 
      })
    );

    rootRef.current = root;
    chartRef.current = chart;
    xAxisRef.current = xAxis;
    yAxisRef.current = yAxis;

    // 1. Create a container for the Gauge (positioned top-right of chart)
    const gaugeContainer = chart.children.push(am5.Container.new(root, {
      width: 120,
      height: 80,
      x: am5.p100,
      centerX: am5.p100,
      y: 0,
      layout: root.verticalLayout,
      layer: 30
    }));

    // 2. Create the Gauge Chart
    const gaugeChart = gaugeContainer.children.push(am5radar.RadarChart.new(root, {
      innerRadius: am5.percent(70),
      radius: am5.p100,
      startAngle: 180,
      endAngle: 360
    }));

    const percentLabel = gaugeContainer.children.push(am5.Label.new(root, {
      text: "0%",
      fontSize: "14px",
      fontWeight: "800",
      fill: am5.color(0xffffff),
      centerX: am5.p50,
      x: am5.p50,
      y: am5.percent(75) 
    }));
    percentLabelRef.current = percentLabel;

    gaugeContainer.children.push(am5.Label.new(root, {
      text: "CONFIDENCE",
      fontSize: "10px",
      fontWeight: "bold",
      fill: am5.color(0x64748b), // slate-500
      centerX: am5.p50,
      x: am5.p50,
      y: am5.percent(60) // Positioned slightly above the center pin
    }));

    // 3. Create the Axis for the Gauge (0 to 100)
    const cursorAxis = gaugeChart.xAxes.push(am5xy.ValueAxis.new(root, {
      min: 0,
      max: 100,
      renderer: am5radar.AxisRendererCircular.new(root, {
        innerRadius: am5.percent(70)
      })
    }));

    // 4. Create the Hand/Needle
    const axisDataItem = cursorAxis.makeDataItem({ value: 0 });
    const clockHand = am5radar.ClockHand.new(root, {
      pinRadius: am5.percent(20),
      radius: am5.percent(100),
      bottomWidth: 5
    });

    // Store the reference to update it later
    gaugeHandRef.current = axisDataItem;
    clockHandRef.current = clockHand;

    cursorAxis.createAxisRange(axisDataItem);
    axisDataItem.set("bullet", am5xy.AxisBullet.new(root, {
      sprite: clockHand
    }));

    return () => root.dispose();
  }, []);

  useEffect(() => {
    // 1. Reset the existing series data immediately on symbol change
    if (seriesRef.current) {
      seriesRef.current.data.setAll([]);
      // Update name so tooltip/legend matches
      seriesRef.current.set("name", selectedSymbol);
    }

    const syncMarket = async () => {
      try {
        // 2. Optimized Parallel Fetch
        const [tickerRes, historyRes, insightRes, progressRes] = await Promise.all([
          fetch("http://localhost:8000/api/market/tickers"),
          fetch("http://localhost:8000/api/market/overview"),
          fetch(`http://localhost:8000/api/agent/insight/${selectedSymbol}`),
          fetch(`http://localhost:8000/api/market/sync-status/${selectedSymbol}`)
        ]);

        const allTickers = await tickerRes.json();
        const historyData = await historyRes.json();
        const insightData = await insightRes.json();
        const progressData = await progressRes.json();

        setTickerData(allTickers);
        setInsight(insightData);
        setSyncProgress(progressData.progress);
        setLastSync(new Date().toLocaleTimeString());

        // Inside syncMarket...
        if (gaugeHandRef.current && clockHandRef.current) {
          // Move the needle to the probability percentage (e.g., 75)
          gaugeHandRef.current.animate({
            key: "value",
            to: insightData.probability * 100, // Assuming 0.85 -> 85
            duration: 800,
            easing: am5.ease.out(am5.ease.cubic)
          });

          const hand = clockHandRef.current;

          if (hand) {
            const isBullish = insight.prediction === "Bullish";
            const color = am5.color(isBullish ? 0x4ade80 : 0xf87171);

            // 2. Use the .set() method on the components inside the hand
            hand.pin.set("fill", color);
            hand.hand.set("fill", color);
          }
        }

        if (!chartRef.current || !rootRef.current) return;

        // 3. Simple "Get or Create" for the single series
        if (!seriesRef.current) {
          seriesRef.current = chartRef.current.series.push(
            am5xy.LineSeries.new(rootRef.current, {
              name: selectedSymbol,
              xAxis: xAxisRef.current!,
              yAxis: yAxisRef.current!,
              valueYField: "price",
              valueXField: "datetime",
              tooltip: am5.Tooltip.new(rootRef.current, { labelText: "{valueY}" })
            })
          );
        }

        // 4. Data Formatting & Sorting
        const formattedHistory = (historyData[selectedSymbol] || []).map(
          (item: {datetime: string, price: number}) => ({
            datetime: new Date(item.datetime).getTime(),
            price: item.price
          })
        );

        // Add live oracle point
        formattedHistory.push({
          datetime: new Date().getTime(),
          price: insightData.last_price
        });

        // Update the chart
        seriesRef.current.data.setAll(
          formattedHistory.sort(
            (
              a: {datetime: number, price: number}, 
              b: {datetime: number, price: number}
            ) => a.datetime - b.datetime
          )
        );

        if (chartRef.current) {
          if (insight.prediction === "Bearish") {
            chartRef.current.get("background")?.set("fill", am5.color(0x330000)); // Subtle red tint
          } else {
            chartRef.current.get("background")?.set("fill", am5.color(0x000000)); // Black
          }
        }

        if (percentLabelRef.current) {
          const probPercent = Math.round((insightData.probability || 0) * 100);
          
          percentLabelRef.current.set("text", `${probPercent}%`);
          
          // Optional: Change label color to match sentiment
          const textColor = insightData.prediction === "Bullish" ? 0x4ade80 : 0xf87171;
          percentLabelRef.current.set("fill", am5.color(textColor));
        }
      } catch (e) {
        console.error("Sync Error:", e);
      }
    };

    syncMarket();
    const interval = setInterval(syncMarket, 5000);
    return () => clearInterval(interval);
  }, [selectedSymbol, setInsight, insight.prediction]);

  return (
    <div className="flex flex-col md:flex-row h-screen bg-slate-950 text-slate-200 overflow-hidden">
      {/* LEFT SECTION: Real-time Stock Changes (40%) */}
      <section className="w-full md:w-[40%] border-r border-slate-800 flex flex-col">
        <div className="p-4 border-b border-slate-800 bg-slate-900/50">
          <h2 className="text-xl font-bold text-blue-400">Market Monitor</h2>
        </div>
        <div className="flex-1 overflow-auto">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 bg-slate-900 shadow-sm">
              <tr>
                <th className="p-3 text-slate-500 uppercase">Symbol</th>
                <th className="p-3 text-slate-500 uppercase">Price</th>
                <th className="p-3 text-slate-500 uppercase">Change</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(tickerData).map(([symbol, info]) => {
                const isPositive = info.change > 0;
                const isActive = selectedSymbol === symbol;
                const isBullish = isActive && insight.prediction === "Bullish";
                const isBearish = isActive && insight.prediction === "Bearish";

                // Define styles once here
                const rowStyle = isActive 
                  ? (isBullish ? 'bg-green-900/10 border-green-500' : isBearish ? 'bg-red-900/10 border-red-500' : 'bg-blue-900/20 border-blue-500')
                  : 'hover:bg-slate-900 border-transparent';

                const badgeStyle = isBullish ? 'text-green-400 border-green-500/50 bg-green-500/10' : 
                                  isBearish ? 'text-red-400 border-red-500/50 bg-red-500/10' : 
                                  'text-blue-400 border-blue-500/50 bg-blue-500/10';

                return (
                  <tr onClick={() => setSelectedSymbol(symbol)} key={symbol} 
                      className={`cursor-pointer transition-all border-l-4 ${rowStyle}`}>
                    
                    <td className="p-3">
                      <div className="flex flex-col gap-1">
                        <span className="font-bold text-slate-100">{symbol}</span>
                        {isActive && (
                          <span className={`text-[10px] w-fit px-1.5 py-0.5 rounded border uppercase font-mono ${badgeStyle}`}>
                            {insight.prediction}
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="p-3 text-right font-mono text-slate-300">
                      ${formatCurrency(info.price)}
                    </td>

                    <td className={`p-3 text-right font-mono font-medium ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                      {isPositive ? '▲' : '▼'} {Math.abs(info.change).toFixed(2)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="p-3 bg-slate-900/80 border-t border-slate-800 flex justify-between items-center text-[10px] uppercase tracking-widest text-slate-500">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
              Lucy Live
            </div>
            <div>
              Last Sync: {lastSync || "Syncing..."}
            </div>
          </div>
      </section>

      {/* Only show if backfilling is actually happening */}
      {syncProgress > 0 && syncProgress < 100 && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30 w-64 bg-slate-900/90 border border-blue-500/30 p-2 rounded shadow-2xl backdrop-blur-md">
          <div className="flex justify-between mb-1">
            <span className="text-[10px] font-mono text-blue-400">RECONSTRUCTING_HISTORY</span>
            <span className="text-[10px] font-mono text-blue-400">{syncProgress}%</span>
          </div>
          <div className="w-full bg-slate-800 h-1 rounded-full overflow-hidden">
            <div 
              className="bg-blue-500 h-full transition-all duration-700 shadow-[0_0_8px_#3b82f6]"
              style={{ width: `${syncProgress}%` }}
            />
          </div>
        </div>
      )}
      {/* RIGHT SECTION: Lucy's Chart & Insights (60%) */}
      <section className="flex-1 flex flex-col relative">
        {/* The amCharts Graph */}
        <div id="chartdiv" className="flex-1 w-full" />
      </section>
    </div>
  );
};

export default MarketChart;