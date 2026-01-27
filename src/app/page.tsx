"use client";
import ChatBox from '@/components/ChatBox';
import MarketChart from '@/components/MarketChart';

export default function Dashboard() {
  const mockWallet = "0x71C...3d2"; // Replace with real wallet connection later
  return (
    <div className="min-h-screen bg-slate-950 text-white p-8">
      {/* Header with Web3 Wallet Status */}
      <div className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
          QuotePlot Agent Dashboard
        </h1>
        <button className="bg-blue-600 hover:bg-blue-500 px-6 py-2 rounded-full text-sm font-medium transition-all">
          Connect Wallet
        </button>
      </div>

      {/* Main Chart Section */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 bg-slate-900 rounded-2xl p-6 shadow-2xl border border-slate-800">
          <MarketChart />
        </div>

        {/* Sidebar for Intelligent Agent Chat (Replicating lucyagent.html logic) */}
        <ChatBox walletAddress={mockWallet} />
      </div>
    </div>
  );
}