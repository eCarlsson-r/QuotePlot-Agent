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
  last_price: number;
  prediction: string;
  probability: number;
  symbol: string;
  trend_summary: string;
}

export interface AgentResponse {
  reply: string;
  prediction_type: string;
  probability: number;
}