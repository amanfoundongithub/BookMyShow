import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { PaymentService } from '../../core/services/payment.service';
import {
  HoldSeatsResponse,
  PaymentIntentResponse,
  PaymentWebhookResponse,
} from '../../models/bms.models';

@Component({
  selector: 'app-checkout',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './checkout.component.html',
  styleUrl: './checkout.component.css',
})
export class CheckoutComponent implements OnInit {
  private readonly router = inject(Router);
  private readonly paymentService = inject(PaymentService);
  private readonly authService = inject(AuthService);

  readonly hold = signal<HoldSeatsResponse | null>(null);
  readonly bookingId = signal<string>('');
  readonly userId = signal<string>(this.authService.userId());
  readonly amount = signal<number>(0);
  readonly currency = signal<string>('INR');
  readonly webhookSecret = signal<string>('local-webhook-secret');

  readonly idempotencyKey = computed(() => {
    const id = this.bookingId().trim() || 'booking';
    return `${id}_ATTEMPT_1`;
  });

  readonly intent = signal<PaymentIntentResponse | null>(null);
  readonly webhookResult = signal<PaymentWebhookResponse | null>(null);

  readonly creatingIntent = signal<boolean>(false);
  readonly sendingWebhook = signal<boolean>(false);
  readonly errorMessage = signal<string | null>(null);
  readonly statusMessage = signal<string | null>(null);

  ngOnInit(): void {
    const navState = history.state as { hold?: HoldSeatsResponse } | undefined;
    if (navState?.hold) {
      this.hold.set(navState.hold);
      this.bookingId.set(navState.hold.booking_id);
      this.userId.set(navState.hold.user_id);
      this.amount.set(navState.hold.total_amount);
      this.currency.set(navState.hold.currency || 'INR');
    }
  }

  createIntent(): void {
    if (!this.bookingId().trim() || this.amount() <= 0 || this.creatingIntent()) return;

    this.creatingIntent.set(true);
    this.errorMessage.set(null);
    this.statusMessage.set(null);

    this.paymentService
      .createIntent(
        {
          booking_id: this.bookingId().trim(),
          user_id: this.userId().trim(),
          amount: this.amount(),
          currency: this.currency(),
          payment_gateway: 'MOCK_GATEWAY',
        },
        this.idempotencyKey()
      )
      .subscribe({
        next: (res) => {
          this.creatingIntent.set(false);
          this.intent.set(res);
          this.statusMessage.set(
            `Payment intent ${res.payment_id} ready (status: ${res.status}).`
          );
        },
        error: (err: HttpErrorResponse) => {
          this.creatingIntent.set(false);
          this.errorMessage.set(err.error?.detail ?? 'Failed to create payment intent.');
        },
      });
  }

  triggerWebhook(eventStatus: 'SUCCESS' | 'FAILED'): void {
    const currentIntent = this.intent();
    if (!currentIntent || this.sendingWebhook()) return;

    this.sendingWebhook.set(true);
    this.errorMessage.set(null);
    this.statusMessage.set(null);

    this.paymentService
      .sendWebhook(
        {
          payment_id: currentIntent.payment_id,
          booking_id: currentIntent.booking_id,
          gateway_reference: currentIntent.gateway_reference,
          event_status: eventStatus,
          failure_reason: eventStatus === 'FAILED' ? 'PAYMENT_DECLINED_SIMULATED' : undefined,
        },
        this.webhookSecret()
      )
      .subscribe({
        next: (res) => {
          this.sendingWebhook.set(false);
          this.webhookResult.set(res);
          this.intent.set({ ...currentIntent, status: res.status });
          if (eventStatus === 'SUCCESS') {
            this.statusMessage.set(
              'Payment confirmed! Seats are transitioning to CONFIRMED and ticket notification queued.'
            );
          } else {
            this.statusMessage.set(
              'Payment marked FAILED. Booking is cancelled and held seats are being released.'
            );
          }
        },
        error: (err: HttpErrorResponse) => {
          this.sendingWebhook.set(false);
          this.errorMessage.set(err.error?.detail ?? 'Failed to dispatch payment webhook.');
        },
      });
  }

  backToDiscovery(): void {
    this.router.navigate(['/']);
  }
}