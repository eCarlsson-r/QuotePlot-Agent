import { afterNextRender, Component, EventEmitter, OnDestroy, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { LucyService } from '../../services/lucy.service';

declare global {
  interface Window {
    html2canvas?: (element: HTMLElement, options: Record<string, unknown>) => Promise<HTMLCanvasElement>;
  }
}

interface LucyMessage {
  role: 'user' | 'assistant';
  content: string;
  suggestedSymbols?: string[];
}

@Component({
  selector: 'app-lucy-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './lucy-panel.component.html',
  styleUrl: './lucy-panel.component.css'
})
export class LucyPanelComponent implements OnInit, OnDestroy {
  @Output() readonly symbolRequested = new EventEmitter<string>();
  prompt = '';
  messages: LucyMessage[] = [];
  thoughts: string[] = [];
  selectedSymbol = 'BTC';
  winRate = 0;
  sampleCount = 0;
  streak = 0;
  brightDataLabel = 'Checking Bright Data…';
  brightDataConnected = false;
  exportError = '';
  isSending = false;
  errorMessage = '';
  isConnected = false;
  notificationsEnabled = false;
  logsVisible = true;

  private replySubscription: Subscription | null = null;
  private thoughtSocket: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private statusTimer: ReturnType<typeof setInterval> | null = null;
  private destroyed = false;

  constructor(private lucyService: LucyService) {}

  ngOnInit(): void {
    this.notificationsEnabled = 'Notification' in window && Notification.permission === 'granted';
    this.connectThoughts();
    afterNextRender(() => {
      if (this.destroyed) return;
      this.refreshServiceStatus();
      this.statusTimer = setInterval(() => this.refreshServiceStatus(), 60000);
    });
  }

  setSymbol(symbol: string): void {
    this.selectedSymbol = symbol;
    this.refreshStats();
  }

  toggleLogs(): void {
    this.logsVisible = !this.logsVisible;
  }

  async enableNotifications(): Promise<void> {
    if (!('Notification' in window)) {
      this.errorMessage = 'Browser notifications are not available.';
      return;
    }
    this.notificationsEnabled = (await Notification.requestPermission()) === 'granted';
    if (this.notificationsEnabled) {
      new Notification('Lucy alerts enabled', { body: 'High confidence market signals will appear here.' });
    }
  }

  async exportAnalysis(): Promise<void> {
    const reportArea = document.getElementById('report-area');
    if (!reportArea || !window.html2canvas) {
      this.exportError = 'Analysis export is unavailable. Check your connection and try again.';
      return;
    }
    this.exportError = '';
    try {
      const canvas = await window.html2canvas(reportArea, {
        backgroundColor: '#020617',
        scale: 2,
        logging: false,
        useCORS: true
      });
      const link = document.createElement('a');
      link.href = canvas.toDataURL('image/png');
      link.download = `Lucy_Analysis_${this.selectedSymbol}_${new Date().toISOString().slice(0, 10)}.png`;
      link.click();
    } catch {
      this.exportError = 'Could not generate the analysis image. Please try again.';
    }
  }

  selectSuggestion(symbol: string): void {
    this.symbolRequested.emit(symbol);
  }

  send(): void {
    const content = this.prompt.trim();
    if (!content || this.isSending) {
      return;
    }

    this.messages = [...this.messages, { role: 'user', content }];
    this.prompt = '';
    this.isSending = true;
    this.errorMessage = '';

    this.replySubscription?.unsubscribe();
    this.replySubscription = this.lucyService.reply(content).subscribe({
      next: (response) => {
        this.messages = [
          ...this.messages,
          this.formatReply(response.reply)
        ];
        this.isSending = false;
      },
      error: () => {
        this.errorMessage = 'Lucy is unavailable. Check that the backend is running.';
        this.isSending = false;
      }
    });
  }

  ngOnDestroy(): void {
    this.destroyed = true;
    this.replySubscription?.unsubscribe();
    this.thoughtSocket?.close();
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.statusTimer) clearInterval(this.statusTimer);
  }

  private connectThoughts(): void {
    if (this.destroyed) return;
    this.thoughtSocket = this.lucyService.connectThoughtStream(
      (thought) => this.handleThought(thought),
      () => {
        this.isConnected = false;
        if (this.destroyed) return;
        if (!this.reconnectTimer) {
          this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.connectThoughts();
          }, 3000);
        }
      }
    );
    this.thoughtSocket.onopen = () => this.isConnected = true;
    this.thoughtSocket.onerror = () => this.isConnected = false;
  }

  private formatReply(reply: string): LucyMessage {
    const suggestions = new Set<string>();
    const buttonPattern = /<button\b[^>]*data-symbol=["']([a-z0-9]+)["'][^>]*>([\s\S]*?)<\/button>/gi;
    const content = reply.replace(buttonPattern, (_match, symbol: string, label: string) => {
      suggestions.add(symbol.toUpperCase());
      return label.replace(/<[^>]*>/g, '').trim();
    });
    return { role: 'assistant', content, suggestedSymbols: [...suggestions] };
  }

  private handleThought(thought: Record<string, unknown>): void {
    const symbol = String(thought['symbol'] || '').toUpperCase();
    if (thought['type'] === 'thought') {
      const content = String(thought['content'] || '');
      if (content) this.thoughts = [...this.thoughts.slice(-19), content];
      return;
    }
    if (symbol && symbol !== this.selectedSymbol) return;
    if (thought['type'] === 'agent_stats') {
      this.winRate = Number(thought['win_rate'] || 0);
      this.sampleCount = Number(thought['total_trades'] || 0);
      this.streak = Number(thought['streak'] || 0);
      if (thought['content']) this.thoughts = [...this.thoughts.slice(-19), String(thought['content'])];
    } else if (thought['type'] === 'insight_update' && thought['insight_text']) {
      this.thoughts = [...this.thoughts.slice(-19), String(thought['insight_text'])];
      const probability = Number(thought['probability'] || 0);
      if (this.notificationsEnabled && probability >= 0.9 && 'Notification' in window) {
        new Notification(`Lucy signal: ${symbol}`, {
          body: `${String(thought['prediction_type'] || 'Market')} · ${Math.round(probability * 100)}% confidence`
        });
      }
    }
  }

  private refreshServiceStatus(): void {
    this.lucyService.getBrightDataStatus().subscribe({
      next: (status) => {
        this.brightDataLabel = status.label;
        this.brightDataConnected = status.connected;
      },
      error: () => {
        this.brightDataLabel = 'Bright Data: Unavailable';
        this.brightDataConnected = false;
      }
    });
    this.refreshStats();
  }

  private refreshStats(): void {
    if (!this.selectedSymbol) return;
    this.lucyService.getTokenStats(this.selectedSymbol).subscribe({
      next: (stats) => {
        this.winRate = stats.win_rate;
        this.sampleCount = stats.total_trades;
        this.streak = stats.streak;
      }
    });
  }
}
