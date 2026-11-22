import { Injectable, signal } from '@angular/core';

const TOKEN_STORAGE_KEY = 'bms_jwt_token';
const USER_STORAGE_KEY = 'bms_user_id';

@Injectable({ providedIn: 'root' })
export class AuthService {
  readonly token = signal<string | null>(this.readInitialToken());
  readonly userId = signal<string>(this.readInitialUserId());

  setSession(token: string, userId: string): void {
    const trimmed = token.trim();
    this.token.set(trimmed || null);
    this.userId.set(userId.trim() || 'usr_991');

    if (typeof localStorage !== 'undefined') {
      if (trimmed) {
        localStorage.setItem(TOKEN_STORAGE_KEY, trimmed);
      } else {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
      }
      localStorage.setItem(USER_STORAGE_KEY, this.userId());
    }
  }

  clearSession(): void {
    this.token.set(null);
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  }

  createCorrelationId(): string {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }
    return `corr_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
  }

  private readInitialToken(): string | null {
    if (typeof localStorage === 'undefined') {
      return null;
    }
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  }

  private readInitialUserId(): string {
    if (typeof localStorage === 'undefined') {
      return 'usr_991';
    }
    return localStorage.getItem(USER_STORAGE_KEY) || 'usr_991';
  }
}