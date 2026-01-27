"use client";
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import * as am5 from "@amcharts/amcharts5";
import * as am5xy from "@amcharts/amcharts5/xy";
import am5themes_Animated from "@amcharts/amcharts5/themes/Animated";
import am5themes_Dark from "@amcharts/amcharts5/themes/Dark";
import { Insight, StockHistoryItem } from '@/types/market';

const MarketChart = () => {
    const [insight, setInsight] = useState<Insight>({
      last_price: 0,
      prediction: "",
      probability: 0,
      symbol: "",
      trend_summary: ""
    });

    // Function to poll Lucy for insights
    useEffect(() => {
        const updateLucy = async () => {
          const res = await fetch("http://localhost:8000/api/agent/insight/BTC");
          const data = await res.json();
          setInsight(data);
        };

        updateLucy();
        const interval = setInterval(updateLucy, 60000); // Sync with 5th function
        return () => clearInterval(interval);
    }, []);
    
  const seriesRef = useRef<Record<string, am5xy.LineSeries>>({});

  useLayoutEffect(() => {
    const root = am5.Root.new("chartdiv");
    root.setThemes([am5themes_Animated.new(root), am5themes_Dark.new(root)]);

    const chart = root.container.children.push(
      am5xy.XYChart.new(root, {
        panX: true, panY: true, wheelX: "zoomX", wheelY: "zoomX",
        layout: root.verticalLayout
      })
    );

    const xAxis = chart.xAxes.push(am5xy.DateAxis.new(root, {
      baseInterval: { timeUnit: "minute", count: 1 },
      renderer: am5xy.AxisRendererX.new(root, {})
    }));

    const yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, {
      renderer: am5xy.AxisRendererY.new(root, {})
    }));

    const updateChart = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/market/overview");
        const marketData = await res.json();

        type MarketDataMap = Record<string, StockHistoryItem[]>;

        Object.entries(marketData as MarketDataMap).forEach(([symbol, history]) => {
          const formattedData = history.map((item) => ({
            ...item,
            datetime: new Date(item.datetime).getTime()
          }));

          // If series exists, update data; otherwise, create it
          if (seriesRef.current[symbol]) {
            seriesRef.current[symbol].data.setAll(formattedData);
          } else {
            const series = chart.series.push(am5xy.LineSeries.new(root, {
              name: symbol, xAxis, yAxis, valueYField: "price", valueXField: "datetime",
              tooltip: am5.Tooltip.new(root, { labelText: "{name}: {valueY}" })
            }));
            series.data.setAll(formattedData);
            seriesRef.current[symbol] = series;
          }
        });
      } catch (e) { console.error("Poll failed", e); }
    };

    // Initial load + Polling every 30 seconds
    updateChart();
    const interval = setInterval(updateChart, 30000);

    return () => {
      clearInterval(interval);
      root.dispose();
    };
  }, []);

  return (
    <div className="flex flex-col h-screen w-full bg-slate-900 p-4">
      {/* 1. Insight Box (Top) */}
      <div className="mb-4 p-4 bg-gray-800 border border-blue-500/30 rounded-xl shadow-lg">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🤖</span>
          <div>
            <h3 className="text-blue-400 font-bold text-sm uppercase tracking-wider">Market Insight</h3>
            <p className="text-white text-lg">{insight.trend_summary}</p>
          </div>
          <div className="ml-auto text-right">
            <span className="block text-xs text-gray-400">Confidence</span>
            <span className="text-green-400 font-mono">{(insight.probability * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

      {/* 2. Chart Container (Bottom - Fills remaining space) */}
      <div className="flex-1 w-full bg-gray-800/50 rounded-xl overflow-hidden border border-gray-700">
        <div id="chartdiv" style={{ width: "100%", height: "100%" }}></div>
      </div>
    </div>
  );
};

export default MarketChart;