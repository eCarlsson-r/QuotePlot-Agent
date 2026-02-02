"use client";
import { useState } from 'react';
import { Insight } from '@/types/market';
import Typewriter from './Typewriter';

interface ChatPanelProps {
  onInsightUpdate: (insight: Insight) => void;
  messages: { role: string, content: string }[];
  setMessages: React.Dispatch<React.SetStateAction<{ role: string, content: string }[]>>;
}

export default function ChatBox({ onInsightUpdate, messages, setMessages }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

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
        body: JSON.stringify({ content: userContent }),
      });

      if (!response.ok) throw new Error("Lucy is offline.");

      const data = await response.json();

      // 3. Add Lucy's real AI response
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: data.reply
      }]);

      // 💡 Bonus: Update the Gauge with Lucy's classification confidence
      onInsightUpdate({
        probability: data.probability, // 0.84 etc.
        prediction: data.prediction_type.includes("Open") ? "Bullish" : "Bearish" 
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
      </div>

      {/* Message Area */}
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
      </div>

      {/* Input Area */}
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