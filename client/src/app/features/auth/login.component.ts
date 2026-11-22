import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

type AuthMode = 'login' | 'register';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
})
export class LoginComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  readonly mode = signal<AuthMode>('login');
  readonly name = signal<string>('');
  readonly email = signal<string>('');
  readonly password = signal<string>('');

  readonly submitting = signal<boolean>(false);
  readonly errorMessage = signal<string | null>(null);
  readonly infoMessage = signal<string | null>(null);

  readonly showDevOverride = signal<boolean>(false);
  readonly manualUserId = signal<string>(this.authService.userId());
  readonly manualToken = signal<string>(this.authService.token() ?? '');

  switchMode(nextMode: AuthMode): void {
    this.mode.set(nextMode);
    this.errorMessage.set(null);
    this.infoMessage.set(null);
  }

  submit(): void {
    if (this.submitting()) return;

    const cleanEmail = this.email().trim();
    const cleanPassword = this.password();
    const cleanName = this.name().trim();

    if (!cleanEmail || !cleanPassword) {
      this.errorMessage.set('Please enter both email and password.');
      return;
    }

    if (this.mode() === 'register' && cleanName.length < 2) {
      this.errorMessage.set('Please enter your name (at least 2 characters).');
      return;
    }

    this.submitting.set(true);
    this.errorMessage.set(null);
    this.infoMessage.set(null);

    const request$ =
      this.mode() === 'login'
        ? this.authService.login({ email: cleanEmail, password: cleanPassword })
        : this.authService.register({
            name: cleanName,
            email: cleanEmail,
            password: cleanPassword,
          });

    request$.subscribe({
      next: () => {
        this.submitting.set(false);
        this.navigateAfterAuth();
      },
      error: (err: HttpErrorResponse) => {
        this.submitting.set(false);
        if (typeof err.error?.detail === 'string') {
          this.errorMessage.set(err.error.detail);
        } else if (Array.isArray(err.error?.detail)) {
          this.errorMessage.set(
            err.error.detail.map((d: { msg?: string }) => d.msg ?? 'Validation error').join(', ')
          );
        } else {
          this.errorMessage.set(
            this.mode() === 'login'
              ? 'Login failed. Check your credentials and try again.'
              : 'Registration failed. Check your inputs and try again.'
          );
        }
      },
    });
  }

  applyManualSession(): void {
    this.authService.setSession(this.manualToken(), this.manualUserId());
    this.infoMessage.set('Manual session applied.');
    this.navigateAfterAuth();
  }

  private navigateAfterAuth(): void {
    const returnUrl = this.route.snapshot.queryParamMap.get('returnUrl') || '/';
    this.router.navigateByUrl(returnUrl);
  }
}