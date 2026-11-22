import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  AuthResponse,
  LoginRequest,
  RegisterRequest,
  UserProfile,
} from '../../models/bms.models';

const TOKEN_STORAGE_KEY = 'bms_jwt_token';
const USER_ID_STORAGE_KEY = 'bms_user_id';
const USER_PROFILE_STORAGE_KEY = 'bms_user_profile';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly authBaseUrl = `${environment.apiBaseUrl}/api/v1/auth`;
  private readonly usersBaseUrl = `${environment.apiBaseUrl}/api/v1/users`;

  readonly token = signal<string | null>(this.readInitialToken());
  readonly userId = signal<string>(this.readInitialUserId());
  readonly currentUser = signal<UserProfile | null>(this.readInitialUserProfile());
  readonly isAuthenticated = computed(() => Boolean(this.token()));

  register(payload: RegisterRequest): Observable<AuthResponse> {
    return this.http
      .post<AuthResponse>(`${this.authBaseUrl}/register`, payload)
      .pipe(tap((res) => this.applyAuthResponse(res)));
  }

  login(payload: LoginRequest): Observable<AuthResponse> {
    return this.http
      .post<AuthResponse>(`${this.authBaseUrl}/login`, payload)
      .pipe(tap((res) => this.applyAuthResponse(res)));
  }

  fetchCurrentUser(): Observable<UserProfile> {
    return this.http.get<UserProfile>(`${this.usersBaseUrl}/me`).pipe(
      tap((profile) => {
        this.currentUser.set(profile);
        this.userId.set(profile.user_id);
        this.persistUserProfile(profile);
        this.persistUserId(profile.user_id);
      })
    );
  }

  setSession(token: string, userId: string): void {
    const trimmedToken = token.trim();
    const trimmedUserId = userId.trim() || 'usr_991';

    this.token.set(trimmedToken || null);
    this.userId.set(trimmedUserId);
    this.currentUser.set(null);

    if (typeof localStorage !== 'undefined') {
      if (trimmedToken) {
        localStorage.setItem(TOKEN_STORAGE_KEY, trimmedToken);
      } else {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
      }
      localStorage.setItem(USER_ID_STORAGE_KEY, trimmedUserId);
      localStorage.removeItem(USER_PROFILE_STORAGE_KEY);
    }
  }

  logout(): void {
    this.token.set(null);
    this.currentUser.set(null);
    this.userId.set('');

    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      localStorage.removeItem(USER_PROFILE_STORAGE_KEY);
      localStorage.removeItem(USER_ID_STORAGE_KEY);
    }
  }

  clearSession(): void {
    this.logout();
  }

  createCorrelationId(): string {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }
    return `corr_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
  }

  private applyAuthResponse(res: AuthResponse): void {
    this.token.set(res.access_token);
    this.userId.set(res.user.user_id);
    this.currentUser.set(res.user);

    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(TOKEN_STORAGE_KEY, res.access_token);
      localStorage.setItem(USER_ID_STORAGE_KEY, res.user.user_id);
      localStorage.setItem(USER_PROFILE_STORAGE_KEY, JSON.stringify(res.user));
    }
  }

  private persistUserId(id: string): void {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(USER_ID_STORAGE_KEY, id);
    }
  }

  private persistUserProfile(profile: UserProfile): void {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(USER_PROFILE_STORAGE_KEY, JSON.stringify(profile));
    }
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
    return localStorage.getItem(USER_ID_STORAGE_KEY) || 'usr_991';
  }

  private readInitialUserProfile(): UserProfile | null {
    if (typeof localStorage === 'undefined') {
      return null;
    }
    const raw = localStorage.getItem(USER_PROFILE_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    try {
      return JSON.parse(raw) as UserProfile;
    } catch {
      return null;
    }
  }
}