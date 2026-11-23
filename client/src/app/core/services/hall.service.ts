import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  CinemaSummary,
  CreateHallPayload,
  HallLayoutResponse,
  UpdateHallLayoutPayload,
  CreateCinemaPayload
} from '../../models/bms.models';

@Injectable({ providedIn: 'root' })
export class HallService {
  private readonly http = inject(HttpClient);
  // Uses empty string if using proxy.conf.json forwarding, or environment baseUrl
  private readonly baseUrl = (environment as { apiGatewayUrl?: string }).apiGatewayUrl ?? '';

  listCinemas(cityId?: string): Observable<CinemaSummary[]> {
    let params = new HttpParams();
    if (cityId) {
      params = params.set('city_id', cityId);
    }
    return this.http.get<CinemaSummary[]>(`${this.baseUrl}/api/v1/cinemas`, { params });
  }

  listHalls(cinemaId?: string): Observable<HallLayoutResponse[]> {
    let params = new HttpParams();
    if (cinemaId) {
      params = params.set('cinema_id', cinemaId);
    }
    return this.http.get<HallLayoutResponse[]>(`${this.baseUrl}/api/v1/halls`, { params });
  }

  getHallLayout(hallId: string): Observable<HallLayoutResponse> {
    return this.http.get<HallLayoutResponse>(`${this.baseUrl}/api/v1/halls/${hallId}/layout`);
  }

  createHall(payload: CreateHallPayload): Observable<HallLayoutResponse> {
    return this.http.post<HallLayoutResponse>(`${this.baseUrl}/api/v1/halls`, payload);
  }

  updateHallLayout(
    hallId: string,
    payload: UpdateHallLayoutPayload
  ): Observable<HallLayoutResponse> {
    return this.http.put<HallLayoutResponse>(
      `${this.baseUrl}/api/v1/halls/${hallId}/layout`,
      payload
    );
  }

  createCinema(payload: CreateCinemaPayload): Observable<CinemaSummary> {
    return this.http.post<CinemaSummary>(`${this.baseUrl}/api/v1/cinemas`, payload);
  }

}