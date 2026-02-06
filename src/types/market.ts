export interface StockTick {
  datetime: string;
  price: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface StockHistoryItem {
  symbol: string;
  price: number;
  volume: number;
  datetime: string | number | Date;
}

export interface Insight {
  last_price?: number;
  prediction: string;
  probability: number;
  symbol?: string;
  trend_summary?: string;
}

export interface TickerInfo {
  price: number;
  oldPrice: number;
  change: number;
}

export interface AgentResponse {
  reply: string;
  prediction_type: string;
  probability: number;
}

export interface Stats {
  win_rate: number;
  total_trades: number;
  streak: number;
}

export interface MarketData {
  userSessionId: string;
  data: TickerInfo[];
  tickerData: TickerInfo[];
  insight: Insight;
  selectedSymbol: string;
  setSelectedSymbol: (symbol: string) => void;
  themeMode: string;
  setInsight: (insight: Insight) => void;
  fetchLucyAnalysis: () => void;
};

export interface ChatPanelProps {
  userSessionId: string;
  setInsight: (insight: Insight) => void;
  messages: ChatMessage[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  selectedSymbol: string;
  setSelectedSymbol: React.Dispatch<React.SetStateAction<string>>;
  stats: Stats;
  logs: string[];
  setLogs: React.Dispatch<React.SetStateAction<string[]>>;
  setStats: (stats: Stats) => void;
  setThemeMode: React.Dispatch<React.SetStateAction<'normal' | 'volatile'>>;
}

export interface ChatMessage {
  role: string;
  type?: string;
  content?: string;
  data?: {
    sentiment: string;
    summary: string;
    top_gainers: string[];
  }
}