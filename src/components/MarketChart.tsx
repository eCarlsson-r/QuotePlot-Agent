"use client";
import { useEffect, useLayoutEffect, useRef } from 'react';
import * as am5 from "@amcharts/amcharts5";
import * as am5xy from "@amcharts/amcharts5/xy";
import * as am5radar from "@amcharts/amcharts5/radar";
import am5themes_Animated from "@amcharts/amcharts5/themes/Animated";
import am5themes_Dark from "@amcharts/amcharts5/themes/Dark";
import { MarketData, TickerInfo } from '@/types/market';

const MarketChart = (props: MarketData) => {
  // amCharts Refs
  const rootRef = useRef<am5.Root | null>(null);
  const chartRef = useRef<am5xy.XYChart | null>(null);
  const seriesRef = useRef<am5xy.LineSeries | null>(null);
  const xAxisRef = useRef<am5xy.DateAxis<am5xy.AxisRenderer> | null>(null);
  const yAxisRef = useRef<am5xy.ValueAxis<am5xy.AxisRenderer> | null>(null);
  const gaugeHandRef = useRef<am5.DataItem<am5xy.IValueAxisDataItem> | null>(null);
  const clockHandRef = useRef<am5radar.ClockHand | null>(null);
  const percentLabelRef = useRef<am5.Label | null>(null);

  // 1. INITIALIZATION: Setup the Chart and Gauge once.
  useLayoutEffect(() => {
    const root = am5.Root.new("chartdiv");
    root.setThemes([am5themes_Animated.new(root), am5themes_Dark.new(root)]);
    
    const chart = root.container.children.push(
      am5xy.XYChart.new(root, {
        panX: true, panY: true, wheelX: "zoomX", wheelY: "zoomX",
        layout: root.verticalLayout
      })
    );

    // Axes Setup
    const xAxis = chart.xAxes.push(am5xy.DateAxis.new(root, {
      baseInterval: { timeUnit: "minute", count: 1 },
      renderer: am5xy.AxisRendererX.new(root, {}),
      groupData: true
    }));

    const yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, {
      extraMin: 0.1, extraMax: 0.1,
      renderer: am5xy.AxisRendererY.new(root, {}),
      strictMinMax: false 
    }));

    // Gauge Setup
    const gaugeContainer = root.container.children.push(am5.Container.new(root, {
      width: 120, height: 80, x: am5.p100, centerX: am5.p100, y: 0, layer: 100
    }));

    const gaugeChart = gaugeContainer.children.push(am5radar.RadarChart.new(root, {
      width: am5.p100, height: 80, innerRadius: am5.percent(80),
      radius: am5.percent(100), startAngle: 180, endAngle: 360,
      centerY: am5.p100, y: am5.p100
    }));

    const cursorAxis = gaugeChart.xAxes.push(am5xy.ValueAxis.new(root, {
      min: 0, max: 100, strictMinMax: true,
      renderer: am5radar.AxisRendererCircular.new(root, { innerRadius: am5.percent(80), strokeOpacity: 0.1 })
    }));

    const axisDataItem = cursorAxis.makeDataItem({ value: 0 });
    const clockHand = am5radar.ClockHand.new(root, { pinRadius: am5.percent(20), radius: am5.percent(100), bottomWidth: 5, layer: 50 });
    
    axisDataItem.set("bullet", am5xy.AxisBullet.new(root, { sprite: clockHand }));
    cursorAxis.createAxisRange(axisDataItem);

    percentLabelRef.current = gaugeContainer.children.push(am5.Label.new(root, {
      text: "0%", fontSize: "14px", fontWeight: "800", fill: am5.color(0xffffff), centerX: am5.p50, x: am5.p50, y: am5.percent(85) 
    }));

    // Save refs for the update loop
    rootRef.current = root;
    chartRef.current = chart;
    xAxisRef.current = xAxis;
    yAxisRef.current = yAxis;
    gaugeHandRef.current = axisDataItem;
    clockHandRef.current = clockHand;

    return () => root.dispose();
  }, []);

  // 2. DATA INJECTION: Listen for updates from the Dashboard Parent
  useEffect(() => {
    if (!seriesRef.current && chartRef.current && rootRef.current) {
        seriesRef.current = chartRef.current.series.push(
          am5xy.LineSeries.new(rootRef.current, {
            name: props.selectedSymbol,
            xAxis: xAxisRef.current!,
            yAxis: yAxisRef.current!,
            valueYField: "price",
            valueXField: "datetime",
            tooltip: am5.Tooltip.new(rootRef.current, { labelText: "{valueY}" })
          })
        );
    }

    if (seriesRef.current) {
      seriesRef.current.set("name", props.selectedSymbol);
      seriesRef.current.data.setAll(props.data);
    }

    // Update Lucy's Confidence Gauge
    if (gaugeHandRef.current && props.insight) {
      const probValue = (props.insight.probability || 0) * 100;
      gaugeHandRef.current.animate({ key: "value", to: probValue, duration: 800, easing: am5.ease.out(am5.ease.cubic) });

      const color = am5.color(props.insight.prediction === "Bullish" ? 0x4ade80 : 0xf87171);
      clockHandRef.current?.pin.set("fill", color);
      clockHandRef.current?.hand.set("fill", color);
      
      if (percentLabelRef.current) {
        percentLabelRef.current.setAll({ text: `${Math.round(probValue)}%`, fill: color });
      }
    }
  }, [props.data, props.insight, props.selectedSymbol]);

  return (
    <div className="flex flex-col md:flex-row h-screen bg-slate-950 text-slate-200 overflow-hidden">
      {/* Sidebar: Now purely functional, no internal fetch */}
      <section className="w-full md:w-[40%] border-r border-slate-800 flex flex-col">
        <div className="p-4 bg-slate-900/50">
          <h2 className="text-xl font-bold text-blue-400">Web3 Analyst</h2>
        </div>
        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm">
            <tbody>
              {Object.entries(props.tickerData || {}).map(([symbol, info]: [string, TickerInfo]) => (
                <tr key={symbol} onClick={() => props.setSelectedSymbol(symbol)} 
                    className={`cursor-pointer ${props.selectedSymbol === symbol ? 'bg-blue-900/20' : ''}`}>
                  <td className="p-3 font-bold">{symbol}</td>
                  <td className="p-3 text-right">${info.price.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="flex-1 relative">
        <div id="chartdiv" className="w-full h-full" />
      </section>
    </div>
  );
};

export default MarketChart;