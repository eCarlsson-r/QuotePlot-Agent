"use client";
import { useState } from 'react';

interface Message {
  role: 'user' | 'agent';
  content: string;
}

export default function ChatBox({ walletAddress }: { walletAddress: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/agent/reply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          content: input, 
          wallet_address: walletAddress 
        }),
      });
      
      const data = await response.json();
      const agentMsg: Message = { 
        role: 'agent', 
        content: `${data.reply} (Confidence: ${Math.round(data.probability * 100)}%)` 
      };
      setMessages(prev => [...prev, agentMsg]);
    } catch (error) {
      console.error("Chat Error:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col w-full max-w-md bg-slate-800 rounded-xl border border-slate-700 p-4 shadow-xl">
      <div className="flex-1 overflow-y-auto mb-4 space-y-2 p-2 scrollbar-hide">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-lg p-3 text-sm ${
              m.role === 'user' ? 'bg-cyan-600 text-white' : 'bg-slate-700 text-gray-200'
            }`}>
              {m.content}
            </div>
          </div>
        ))}
        {loading && <div className="text-xs text-cyan-400 animate-pulse">Lucy is thinking...</div>}
      </div>

      <form onSubmit={sendMessage} className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask Lucy about the market..."
          className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
        />
        <button type="submit" className="bg-cyan-500 hover:bg-cyan-400 text-white px-4 py-2 rounded-lg transition-colors">
          Send
        </button>
      </form>
    </div>
  );
}