import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { City, HallLayoutResponse, Movie, Show } from '../../models/bms.models';

@Injectable({ providedIn: 'root' })
export class CatalogService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}/api/v1/catalog`;

  getCities(): Observable<City[]> {
    return this.http.get<City[]>(`${this.baseUrl}/cities`);
  }

  getMoviesByCity(cityId: string): Observable<Movie[]> {
    const params = new HttpParams().set('city', cityId);
    return this.http.get<Movie[]>(`${this.baseUrl}/movies`, { params });
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
}