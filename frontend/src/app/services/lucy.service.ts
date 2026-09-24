import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface LucyReply {
  reply: string;
  symbol?: string;
  prediction_type?: string;
  probability?: number;
  insight_text?: string;
}

export interface LucyThought {
  type: string;
  content?: string;
  symbol?: string;
  [key: string]: unknown;
}

export interface LucyTokenStats {
  win_rate: number;
  total_trades: number;
  streak: number;
}

export interface BrightDataStatus {
  connected: boolean;
  label: string;
}

@Injectable({
  providedIn: 'root'
})
export class LucyService {
  private readonly sessionStorageKey = 'quoteplot-session-id';

  constructor(private http: HttpClient) {}

  get sessionId(): string {
    let sessionId = localStorage.getItem(this.sessionStorageKey);
    if (!sessionId) {
      sessionId = crypto.randomUUID();
      localStorage.setItem(this.sessionStorageKey, sessionId);
    }
    return sessionId;
  }

  reply(content: string): Observable<LucyReply> {
    return this.http.post<LucyReply>('/api/agent/reply', {
      content,
      session_id: this.sessionId
    });
  }

  getTokenStats(symbol: string): Observable<LucyTokenStats> {
    return this.http.get<LucyTokenStats>(`/api/agent/token-stats/${encodeURIComponent(symbol)}`);
  }

  getBrightDataStatus(): Observable<BrightDataStatus> {
    return this.http.get<BrightDataStatus>('/api/agent/brightdata-status');
  }

  connectThoughtStream(
    onThought: (thought: LucyThought) => void,
    onClose?: () => void
  ): WebSocket {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws/thoughts`);

    socket.onmessage = (event) => {
      try {
        const envelope = JSON.parse(event.data) as LucyThought;
        if (envelope.type === 'thought' && typeof envelope.content === 'string') {
          try {
            onThought(JSON.parse(envelope.content) as LucyThought);
          } catch {
            onThought(envelope);
          }
          return;
        }
        onThought(envelope);
      } catch {
        return;
      }
    };
    socket.onclose = () => onClose?.();

    return socket;
  }
}
