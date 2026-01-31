"use client";
import { useState } from 'react';
import { Insight } from '@/types/market';

interface ChatPanelProps {
  selectedSymbol: string;
  insight: Insight;
}

export default function ChatBox({ selectedSymbol, insight }: ChatPanelProps) {
  const [messages, setMessages] = useState([
    { 
      role: 'assistant', 
      content: `System initialized. Current analysis for ${selectedSymbol}: ${insight.trend_summary}` 
    }
  ]);
  const [input, setInput] = useState("");

  const sendMessage = async () => {
    if (!input.trim()) return;
    
    // Add user message
    const newMessages = [...messages, { role: 'user', content: input }];
    setMessages(newMessages);
    setInput("");

    // Next step: Call your backend /api/agent/chat endpoint
    // For now, we'll simulate a response
  };

  return (
    <section className="w-full bg-slate-900/30 border-l border-slate-800 flex flex-col h-full">
      <div className="p-4 border-b border-slate-800 bg-slate-900/50">
        <h2 className="text-sm font-bold text-blue-400 uppercase tracking-widest">Lucy Terminal</h2>
      </div>

      {/* Message Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-xs">
        {messages.map((m, i) => (
          <div key={i} className={`${m.role === 'user' ? 'text-slate-400' : 'text-blue-300'}`}>
            <span className="font-bold">{m.role === 'user' ? '> YOU: ' : '> LUCY: '}</span>
            {m.content}
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