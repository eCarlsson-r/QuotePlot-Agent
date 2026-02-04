"use client";
import ChatBox from '@/components/ChatBox';
import MarketChart from '@/components/MarketChart';
import { Stats, TickerInfo } from '@/types/market';
import Image from 'next/image';
import { useEffect, useState } from 'react';
import { toast, ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { Download } from 'lucide-react';
import html2canvas from 'html2canvas';
import { requestNotificationPermission } from '@/utils/notifications';

export default function Dashboard() {
  const [marketData, setMarketData] = useState<TickerInfo[]>([]);
  const [tickerData, setTickerData] = useState<TickerInfo[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState("BTC");
  const [insight, setInsight] = useState({ prediction: "Neutral", probability: 0 });
  const [themeMode, setThemeMode] = useState<'normal' | 'volatile'>('normal');
  const theme = {
    bg: themeMode === 'volatile' ? 'bg-red-950/20' : 'bg-slate-950',
    border: themeMode === 'volatile' ? 'border-red-500/50' : 'border-slate-800',
    text: themeMode === 'volatile' ? 'from-red-500 to-orange-500' : 'from-blue-400 to-emerald-400',
    glow: themeMode === 'volatile' ? 'shadow-[0_0_50px_rgba(239,68,68,0.2)]' : ''
  };

  const [logs, setLogs] = useState<string[]>([]);
  const [stats, setStats] = useState<Stats>({ winRate: 0, totalTrades: 0, streak: 0 });

  const [messages, setMessages] = useState([
    { 
      role: 'assistant', 
      content: `System initialized. Current analysis for ${selectedSymbol}: ${insight.prediction}` 
    }
  ]);

  useEffect(() => {
    requestNotificationPermission();
    const syncMarket = async () => {
      try {
        setMarketData([]); 
        setInsight({ prediction: "Analyzing...", probability: 0 });
        // 1. Fetch everything in parallel for maximum speed
        const [tickerRes, historyRes] = await Promise.all([
          fetch("http://localhost:8000/api/market/tickers"),
          fetch(`http://localhost:8000/api/market/history/${selectedSymbol}`)
        ]);

        const [tickers, history] = await Promise.all([
          tickerRes.json(),
          historyRes.json()
        ]);

        // Update state in one batch to ensure all components stay in sync
        setTickerData(tickers);
        setMarketData(history);
      } catch (err) {
        console.error("Dashboard Sync Error:", err);
      }
    };

    const interval = setInterval(syncMarket, 5000);
    syncMarket(); // Initial call
    return () => clearInterval(interval);
  }, [selectedSymbol]); // Re-sync immediately if the user selects a new Web3 token

  const downloadReport = async () => {
    const reportElement = document.getElementById('report-area');
    if (!reportElement) return;

    try {
      // Create the snapshot
      const canvas = await html2canvas(reportElement, {
        backgroundColor: '#020617', // Match slate-950
        scale: 2, // High resolution
        logging: false,
        useCORS: true // Important for external images/logos
      });

      // Convert to image and download
      const image = canvas.toDataURL("image/png");
      const link = document.createElement('a');
      link.href = image;
      link.download = `Lucy_Analysis_${selectedSymbol}_${new Date().toISOString().slice(0,10)}.png`;
      link.click();
      
      toast.success("Analysis report saved to downloads!");
    } catch (err) {
      console.error("Snapshot failed:", err);
      toast.error("Failed to generate report.");
    }
  };

  return (
    <div className={`min-h-screen ${theme.bg} transition-colors duration-1000 px-4 py-2`}>
      <div className={`flex justify-between items-center mb-4 border-b ${theme.border} pb-4`}>
        <div className="flex items-center gap-2">
          <Image src="/logo.png" width="100" height="50" alt="QuotePlot Agent" />
          <h1 className={`text-2xl font-bold bg-gradient-to-r ${theme.text} bg-clip-text text-transparent`}>
            QuotePlot Agent Dashboard
          </h1>
        </div>

        <button 
          onClick={downloadReport}
          className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-xl text-sm font-bold transition-all shadow-lg shadow-emerald-900/20"
        >
          <Download size={18} />
          Export Analysis
        </button>
      </div>

      {/* Main Chart Section */}
      <div id="report-area" className={`grid grid-cols-1 lg:grid-cols-4 gap-6 ${theme.glow}`}>
        <div className="lg:col-span-3 bg-slate-900 rounded-2xl p-6 shadow-2xl border border-slate-800">
          <MarketChart 
            data={marketData} 
            tickerData={tickerData}
            insight={insight} 
            selectedSymbol={selectedSymbol}
            setSelectedSymbol={setSelectedSymbol} 
            themeMode={themeMode}
          />
        </div>

        <ChatBox
          messages={messages} 
          setMessages={setMessages} 
          setSelectedSymbol={setSelectedSymbol} 
          selectedSymbol={selectedSymbol}
          setInsight={setInsight}
          stats={stats}
          logs={logs}
          setLogs={setLogs}
          setStats={setStats}
          setThemeMode={setThemeMode}
        />

        <ToastContainer theme="dark" position="bottom-right" />

        <div className="hidden print:block text-[10px] text-slate-500 italic mt-2">
          Generated by Lucy AI Agent v3.2 - Real-time Web3 Intelligence
        </div>
      </div>
    </div>
  );
}