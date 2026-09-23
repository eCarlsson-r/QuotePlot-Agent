import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subject, takeUntil } from 'rxjs';
import {
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
  selectedSymbol = 'BTC';
  symbols: string[] = [];
  tickers: Record<string, MarketTicker> = {};
  insight: MarketInsight | null = null;
  isLoading = true;
  errorMessage = '';

  private readonly destroyed$ = new Subject<void>();

  constructor(private marketService: MarketService) {}

  ngOnInit(): void {
    this.loadTickers();
  }

  selectSymbol(symbol: string): void {
    this.selectedSymbol = symbol;
    this.loadInsight(symbol);
  }

  trackSymbol(_index: number, symbol: string): string {
    return symbol;
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }

  private loadTickers(): void {
    this.isLoading = true;
    this.errorMessage = '';

    this.marketService.getTickers()
      .pipe(takeUntil(this.destroyed$))
      .subscribe({
        next: (tickers) => {
          this.tickers = tickers;
          this.symbols = Object.keys(tickers).sort();
          if (this.symbols.length > 0 && !this.tickers[this.selectedSymbol]) {
            this.selectedSymbol = this.symbols[0];
          }
          this.isLoading = false;
          this.loadInsight(this.selectedSymbol);
        },
        error: () => {
          this.isLoading = false;
          this.errorMessage = 'Market data is unavailable. Start the FastAPI service on port 8000.';
        }
      });
  }

  private loadInsight(symbol: string): void {
    if (!symbol) {
      return;
    }

    this.marketService.getInsight(symbol)
      .pipe(takeUntil(this.destroyed$))
      .subscribe({
        next: (insight) => this.insight = insight,
        error: () => this.insight = null
      });
  }
}