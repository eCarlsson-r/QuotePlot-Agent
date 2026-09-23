import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface MarketTicker {
  price: number;
  change: number;
}

export interface MarketInsight {
  symbol: string;
  insight: string;
}

export interface MarketHistoryPoint {
  datetime: number;
  price: number;
}

@Injectable({
  providedIn: 'root'
})
export class MarketService {
  constructor(private http: HttpClient) {}

  getTickers(): Observable<Record<string, MarketTicker>> {
    return this.http.get<Record<string, MarketTicker>>(
      '/api/market/tickers'
    );
  }

  getInsight(symbol: string): Observable<MarketInsight> {
    return this.http.get<MarketInsight>(
      `/api/market/insight/${encodeURIComponent(symbol)}`
    );
  }

  getHistory(symbol: string): Observable<MarketHistoryPoint[]> {
    return this.http.get<MarketHistoryPoint[]>(
      `/api/market/history/${encodeURIComponent(symbol)}`
    );
  }
}