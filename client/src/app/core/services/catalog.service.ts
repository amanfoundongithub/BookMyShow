import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { City, HallLayoutResponse, Movie, Show } from '../../models/bms.models';
import { MovieRecord } from '../../models/movie.models';

export interface CreateShowPayload {
  id?: string;
  movie_id: string;
  cinema_id: string;
  hall_id: string;
  start_time: string;
  end_time: string;
  language: string;
  format: string;
  pricing: Record<string, number>;
}

@Injectable({ 
  providedIn: 'root' 
})
export class CatalogService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/api/v1/catalog`;

  getCities(): Observable<City[]> {
    return this.http.get<City[]>(`${environment.apiBaseUrl}/api/v1/cities`);
  }

  getAllMoviesByCity(cityId : string) : Observable<MovieRecord[]> {
    return this.http.get<MovieRecord[]>(`${environment.apiBaseUrl}/api/v1/movies?city=${cityId}&active_only=true`);
  }

  getShows(movieId: string, date: string, cityId: string): Observable<Show[]> {
    const params = new HttpParams()
      .set('movie_id', movieId)
      .set('date', date)
      .set('city', cityId);
    return this.http.get<Show[]>(`${this.baseUrl}/shows`, { params });
  }

  getHallLayout(hallId: string): Observable<HallLayoutResponse> {
    return this.http.get<HallLayoutResponse>(`${this.baseUrl}/halls/${hallId}/layout`);
  }

  createShow(payload: CreateShowPayload): Observable<Show> {
    return this.http.post<Show>(`${this.baseUrl}/shows`, payload);
  }
}