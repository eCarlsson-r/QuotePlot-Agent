"use client";
import { useState } from 'react';
import { ChatPanelProps } from '@/types/market';
import ThoughtStream from './ThoughtStream';
import Typewriter from './Typewriter';
import { ChevronDown, ChevronUp, Terminal } from 'lucide-react';

export default function ChatBox({ userSessionId, setInsight, messages, setMessages, selectedSymbol, setSelectedSymbol, stats, logs, setLogs, setStats, setThemeMode }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showLogs, setShowLogs] = useState(true); // Toggle state

  const triggerAlert = (symbol: string, sentiment: string, confidence: number) => {
    if (Notification.permission === "granted" && confidence >= 0.90) {
      new Notification(`🚀 High Confidence Alert: ${symbol}`, {
        body: `Lucy is ${Math.round(confidence * 100)}% sure of a ${sentiment} move!`,
        icon: "/logo.png", // Path to your agent icon
      });
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;
    
    const userContent = input;
    // 1. Add User Message to UI
    setMessages(prev => [...prev, { role: 'user', content: userContent }]);
    setInput("");
    setIsLoading(true);

    try {
      // 2. Call your FastAPI /reply endpoint
      const response = await fetch("http://localhost:8000/api/agent/reply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: userContent, session_id: userSessionId })
      });

      if (!response.ok) throw new Error("Lucy is offline.");

      const data = await response.json();
      triggerAlert(data.symbol || selectedSymbol, data.prediction_type, data.probability);

      // 3. Add Lucy's real AI response
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: data.reply
      }]);

      // 2. DYNAMIC DASHBOARD SWITCH (The New Part!)
      // If Lucy found a symbol (e.g., "SOL"), update the global active token
      if (data.symbol) {
        console.log(`🎯 Lucy detected a focus on: ${data.symbol}`);
        // setActiveToken is a state passed down from your main App.js
        setSelectedSymbol(data.symbol.toUpperCase());
      }

      // 💡 Bonus: Update the Gauge with Lucy's classification confidence
      setInsight({
        probability: data.probability, 
        prediction: data.prediction_type,
        trend_summary: data.insight_text
      });

    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: "Error: Could not reach the brain." + error }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="w-full bg-slate-900/30 border-l border-slate-800 flex flex-col h-screen">
      <div className="p-4 border-b border-slate-800 bg-slate-900/50">
        <h2 className="text-sm font-bold text-blue-400 uppercase tracking-widest">Lucy Terminal</h2>

        <button 
          onClick={() => setShowLogs(!showLogs)}
          className="text-slate-400 hover:text-emerald-400 transition-colors flex items-center gap-1 text-[10px] uppercase font-mono"
        >
          <Terminal size={12} />
          {showLogs ? "Hide Internal" : "Show Internal"}
          {showLogs ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
        </button>
      </div>

      <div className="bg-slate-800/50 p-3 rounded-xl border border-slate-700 mt-4">
        <div className="flex justify-between text-[10px] uppercase text-slate-400 mb-2">
          <span>Agent Reliability</span>
          <span className="text-emerald-400">Live</span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="text-center">
            <div className="text-xl font-bold text-white">{stats.winRate}%</div>
            <div className="text-[9px] text-slate-500">ACCURACY</div>
          </div>
          <div className="text-center border-l border-slate-700">
            <div className="text-xl font-bold text-white">{stats.totalTrades}</div>
            <div className="text-[9px] text-slate-500">SAMPLES</div>
          </div>
          <div className="text-center">
            {/* Render the Streak Badge */}
            {stats.streak >= 2 && (
              <span className="badge-fire">
                🔥 {stats.streak} WIN STREAK
              </span>
            )}
            {stats.streak <= -2 && (
              <span className="badge-cold">
                ❄️ {Math.abs(stats.streak)} LOSS STREAK
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-xs">
        {messages.map((m, i) => (
          <div key={i} className={`${m.role === 'user' ? 'text-slate-400' : 'text-blue-300'}`}>
            <span className="font-bold">{m.role === 'user' ? '> YOU: ' : '> LUCY: '}</span>
            {m.role === 'assistant' ? (
              <Typewriter text={m.content} />
            ) : (
              <span>{m.content}</span>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start mb-4">
            <div className="bg-slate-800 text-blue-400 px-4 py-2 rounded-2xl rounded-bl-none border border-blue-900/50 flex items-center gap-2">
              <span className="flex gap-1">
                <span className="animate-bounce">.</span>
                <span className="animate-bounce [animation-delay:0.2s]">.</span>
                <span className="animate-bounce [animation-delay:0.4s]">.</span>
              </span>
              <span className="text-xs font-mono uppercase tracking-widest opacity-70">Lucy is thinking</span>
            </div>
          </div>
        )}
      </div>

      <div className={`transition-all duration-300 ease-in-out border-t border-slate-800/50 ${
        showLogs ? 'h-40 opacity-100' : 'h-0 opacity-0 pointer-events-none'
      }`}>
        <ThoughtStream 
            logs={logs} 
            setLogs={setLogs}
            setInsight={setInsight}
            setStats={setStats}
            setThemeMode={setThemeMode}
        />
      </div>

      <div className="p-4 border-t border-slate-800 bg-slate-900/50">
        <div className="flex gap-2">
          <input 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Ask Lucy..."
            className="flex-1 bg-slate-950 border border-slate-700 rounded p-2 text-xs focus:outline-none focus:border-blue-500 text-slate-200"
          />
        </div>
      </div>
    </section>
  );
};