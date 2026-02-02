"use client";
import ChatBox from '@/components/ChatBox';
import MarketChart from '@/components/MarketChart';
import { TickerInfo } from '@/types/market';
import Image from 'next/image';
import { useEffect, useState } from 'react';

export default function Dashboard() {
  const [marketData, setMarketData] = useState<TickerInfo[]>([]);
  const [tickerData, setTickerData] = useState<TickerInfo[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState("BTC");
  const [insight, setInsight] = useState({ prediction: "Neutral", probability: 0 });
  const [messages, setMessages] = useState([
    { 
      role: 'assistant', 
      content: `System initialized. Current analysis for ${selectedSymbol}: ${insight.prediction}` 
    }
  ]);

  useEffect(() => {
    const syncMarket = async () => {
      try {
        // Use your FastAPI endpoints
        const [tickerRes, historyRes, insightRes] = await Promise.all([
          fetch("http://localhost:8000/api/market/tickers"),
          fetch(`http://localhost:8000/api/market/history/${selectedSymbol}`),
          fetch(`http://localhost:8000/api/agent/insight/${selectedSymbol}`)
        ]);

        const allTickers = await tickerRes.json();
        const history = await historyRes.json();
        const LucyInsight = await insightRes.json();

        // Update state in one batch to ensure all components stay in sync
        setTickerData(allTickers);
        setMarketData(history);
        setInsight(LucyInsight);
      } catch (err) {
        console.error("Dashboard Sync Error:", err);
      }
    };

    const interval = setInterval(syncMarket, 5000);
    syncMarket(); // Initial call
    return () => clearInterval(interval);
  }, [selectedSymbol]); // Re-sync immediately if the user selects a new Web3 token

  return (
    <div className="min-h-screen bg-slate-950 text-white px-4 py-2">
      {/* Header with Web3 Wallet Status */}
      <div className="flex justify-between items-center mb-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-2">
          <Image src="/logo.png" width="100" height="50" alt="QuotePlot Agent" />
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
            QuotePlot Agent Dashboard
          </h1>
        </div>
      </div>

      {/* Main Chart Section */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 bg-slate-900 rounded-2xl p-6 shadow-2xl border border-slate-800">
          <MarketChart 
            data={marketData} 
            tickerData={tickerData}
            insight={insight} 
            selectedSymbol={selectedSymbol}
            setSelectedSymbol={setSelectedSymbol} 
          />
        </div>

        {/* Sidebar for Intelligent Agent Chat (Replicating lucyagent.html logic) */}
        <ChatBox
          messages={messages} 
          setMessages={setMessages} 
          onInsightUpdate={setInsight}
        />
      </div>
    </div>
  );
}