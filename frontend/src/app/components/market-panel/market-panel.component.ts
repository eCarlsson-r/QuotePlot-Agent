import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnDestroy, OnInit, Output } from '@angular/core';
import { Subject, catchError, of, switchMap, takeUntil, timer } from 'rxjs';
import {
  MarketHistoryPoint,
  MarketInsight,
  MarketService,
  MarketTicker
} from '../../services/market.service';

@Component({
  selector: 'app-market-panel',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './market-panel.component.html',
  styleUrl: './market-panel.component.css'
})
export class MarketPanelComponent implements OnInit, OnDestroy {
  @Output() readonly selectedSymbolChange = new EventEmitter<string>();
  selectedSymbol = new URLSearchParams(window.location.search).get('symbol')?.toUpperCase() || 'BTC';
  searchTerm = '';
  symbols: string[] = [];
  tickers: Record<string, MarketTicker> = {};
  history: MarketHistoryPoint[] = [];
  insight: MarketInsight | null = null;
  isLoading = true;
  isHistoryLoading = false;
  errorMessage = '';

  private readonly destroyed$ = new Subject<void>();

  constructor(private readonly marketService: MarketService) {}

  get visibleSymbols(): string[] {
    const query = this.searchTerm.trim().toUpperCase();
    return this.symbols.filter((symbol) => symbol.includes(query));
  }

  get chartPointString(): string {
    if (this.history.length < 2) return '';
    const prices = this.history.map((point) => point.price);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const span = max - min || 1;
    return prices.map((price, index) => {
      const x = 18 + (index / (prices.length - 1)) * 684;
      const y = 224 - ((price - min) / span) * 190;
      return `${x},${y}`;
    }).join(' ');
  }

  get chartFillPoints(): string {
    return this.chartPointString ? `18,250 ${this.chartPointString} 702,250` : '';
  }

  ngOnInit(): void {
    timer(0, 15000)
      .pipe(
        switchMap(() => this.marketService.getTickers().pipe(catchError(() => of(null)))),
        takeUntil(this.destroyed$)
      )
      .subscribe((tickers) => {
        if (!tickers) {
          if (this.isLoading) {
            this.errorMessage = 'Market data is unavailable. Check that the backend is running.';
            this.isLoading = false;
          }
          return;
        }
        this.errorMessage = '';
        this.tickers = tickers;
        this.symbols = Object.keys(tickers).sort();
        if (!this.tickers[this.selectedSymbol] && this.symbols.length > 0) {
          this.selectedSymbol = this.symbols[0];
        }
        const firstLoad = this.isLoading;
        this.isLoading = false;
        if (firstLoad) this.selectedSymbolChange.emit(this.selectedSymbol);
        this.loadAssetDetails(this.selectedSymbol);
      });
  }

  selectSymbol(symbol: string): void {
    this.selectedSymbol = symbol;
    this.selectedSymbolChange.emit(symbol);
    const url = new URL(window.location.href);
    url.searchParams.set('symbol', symbol);
    window.history.replaceState({}, '', url);
    this.loadAssetDetails(symbol);
  }

  setSearch(value: string): void {
    this.searchTerm = value;
  }

  trackSymbol(_index: number, symbol: string): string {
    return symbol;
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }

  private loadAssetDetails(symbol: string): void {
    if (!symbol) return;
    this.isHistoryLoading = true;

    this.marketService.getHistory(symbol)
      .pipe(catchError(() => of([] as MarketHistoryPoint[])), takeUntil(this.destroyed$))
      .subscribe((history) => {
        if (this.selectedSymbol !== symbol) return;
        this.history = history;
        this.isHistoryLoading = false;
      });

    this.marketService.getInsight(symbol)
      .pipe(catchError(() => of(null)), takeUntil(this.destroyed$))
      .subscribe((insight) => {
        if (this.selectedSymbol === symbol) this.insight = insight;
      });
  }
}
