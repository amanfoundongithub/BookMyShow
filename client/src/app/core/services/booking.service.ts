import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  HoldSeatsRequest,
  HoldSeatsResponse,
  ReleaseBookingRequest,
  ReleaseBookingResponse,
  SeatMapResponse,
  BookingRecord
} from '../../models/bms.models';

@Injectable({ providedIn: 'root' })
export class BookingService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/api/v1/bookings`;

  getSeatMap(showId: string, hallId: string): Observable<SeatMapResponse> {
    const params = new HttpParams().set('hall_id', hallId);
    return this.http.get<SeatMapResponse>(`${this.baseUrl}/shows/${showId}/seat-map`, {
      params,
    });
  }

  holdSeats(payload: HoldSeatsRequest, tierPrice?: number): Observable<HoldSeatsResponse> {
    let params = new HttpParams();
    if (tierPrice !== undefined) {
      params = params.set('tier_price', tierPrice.toString());
    }
    return this.http.post<HoldSeatsResponse>(`${this.baseUrl}/hold`, payload, { params });
  }

  releaseBooking(payload: ReleaseBookingRequest): Observable<ReleaseBookingResponse> {
    return this.http.post<ReleaseBookingResponse>(`${this.baseUrl}/release`, payload);
  }

  getUserBookings(userId: string): Observable<BookingRecord[]> {
  return this.http.get<BookingRecord[]>(`${this.baseUrl}`, {
    params: { user_id: userId },
  });
}
}