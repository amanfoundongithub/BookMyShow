import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  CreatePaymentIntentRequest,
  PaymentIntentResponse,
  PaymentWebhookRequest,
  PaymentWebhookResponse,
} from '../../models/bms.models';

@Injectable({ providedIn: 'root' })
export class PaymentService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/api/v1/payments`;

  createIntent(
    payload: CreatePaymentIntentRequest,
    idempotencyKey: string
  ): Observable<PaymentIntentResponse> {
    const headers = new HttpHeaders({
      'Idempotency-Key': idempotencyKey,
    });
    return this.http.post<PaymentIntentResponse>(`${this.baseUrl}/create-intent`, payload, {
      headers,
    });
  }

  sendWebhook(
    payload: PaymentWebhookRequest,
    webhookSignature: string
  ): Observable<PaymentWebhookResponse> {
    const headers = new HttpHeaders({
      'X-Webhook-Signature': webhookSignature,
    });
    return this.http.post<PaymentWebhookResponse>(`${this.baseUrl}/webhook`, payload, {
      headers,
    });
  }
}