import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { LucyService } from '../../services/lucy.service';

interface LucyMessage {
  role: 'user' | 'assistant';
  content: string;
}

@Component({
  selector: 'app-lucy-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './lucy-panel.component.html',
  styleUrl: './lucy-panel.component.css'
})
export class LucyPanelComponent implements OnInit, OnDestroy {
  prompt = '';
  messages: LucyMessage[] = [];
  thoughts: string[] = [];
  isSending = false;
  errorMessage = '';
  isConnected = false;

  private replySubscription: Subscription | null = null;
  private thoughtSocket: WebSocket | null = null;

  constructor(private lucyService: LucyService) {}

  ngOnInit(): void {
    this.thoughtSocket = this.lucyService.connectThoughtStream(
      (thought) => {
        if (thought.type === 'thought' && thought.content) {
          this.thoughts = [...this.thoughts.slice(-7), thought.content];
        }
      },
      () => this.isConnected = false
    );
    this.thoughtSocket.onopen = () => this.isConnected = true;
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
          { role: 'assistant', content: response.reply }
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
    this.replySubscription?.unsubscribe();
    this.thoughtSocket?.close();
  }
}