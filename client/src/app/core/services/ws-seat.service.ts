import { Injectable, OnDestroy, inject, signal } from '@angular/core';
import { Subject, Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { SeatStatusUpdateEvent } from '../../models/bms.models';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class WsSeatService implements OnDestroy {
  private readonly auth = inject(AuthService);
  private readonly updates$ = new Subject<SeatStatusUpdateEvent>();
  private socket: WebSocket | null = null;
  private activeShowId: string | null = null;

  readonly connected = signal<boolean>(false);
  readonly lastError = signal<string | null>(null);

  get seatUpdates$(): Observable<SeatStatusUpdateEvent> {
    return this.updates$.asObservable();
  }

  connect(showId: string): void {
    if (this.activeShowId === showId && this.socket && this.socket.readyState <= WebSocket.OPEN) {
      return;
    }
    this.disconnect();
    this.activeShowId = showId;
    this.lastError.set(null);

    const url = this.buildWsUrl(showId);
    const ws = new WebSocket(url);
    this.socket = ws;

    ws.onopen = () => {
      if (this.socket === ws) {
        this.connected.set(true);
      }
    };

    ws.onmessage = (event: MessageEvent<string>) => {
      try {
        const parsed = JSON.parse(event.data) as SeatStatusUpdateEvent;
        if (parsed?.type === 'SEAT_STATUS_UPDATE' && parsed.show_id === showId) {
          this.updates$.next(parsed);
        }
      } catch {
        // Ignore non-JSON or heartbeat frames
      }
    };

    ws.onerror = () => {
      if (this.socket === ws) {
        this.lastError.set('WebSocket connection error');
      }
    };

    ws.onclose = () => {
      if (this.socket === ws) {
        this.connected.set(false);
        this.socket = null;
      }
    };
  }

  disconnect(): void {
    this.activeShowId = null;
    this.connected.set(false);
    if (this.socket) {
      this.socket.onopen = null;
      this.socket.onmessage = null;
      this.socket.onerror = null;
      this.socket.onclose = null;
      this.socket.close();
      this.socket = null;
    }
  }

  ngOnDestroy(): void {
    this.disconnect();
    this.updates$.complete();
  }

  private buildWsUrl(showId: string): string {
    const token = this.auth.token();
    const query = token ? `?token=${encodeURIComponent(token)}` : '';

    if (environment.wsBaseUrl) {
      return `${environment.wsBaseUrl.replace(/\/$/, '')}/ws/shows/${showId}${query}`;
    }

    if (typeof window !== 'undefined') {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${protocol}//${window.location.host}/ws/shows/${showId}${query}`;
    }

    return `ws://localhost:8000/ws/shows/${showId}${query}`;
  }
}