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
  content: string;
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

  connectThoughtStream(
    onThought: (thought: LucyThought) => void,
    onClose?: () => void
  ): WebSocket {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws/thoughts`);

    socket.onmessage = (event) => {
      try {
        onThought(JSON.parse(event.data) as LucyThought);
      } catch {
        return;
      }
    };
    socket.onclose = () => onClose?.();

    return socket;
  }
}