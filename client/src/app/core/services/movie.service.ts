import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from './auth.service';
import {
  MovieCreateRequest,
  MovieOptions,
  MovieRecord,
  MovieUpdateRequest,
} from '../../models/movie.models';

@Injectable({ providedIn: 'root' })
export class MovieService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly baseUrl = `${environment.apiBaseUrl}/api/v1/movies`;

  getMovieOptions(): Observable<MovieOptions> {
    return this.http.get<MovieOptions>(`${this.baseUrl}/meta`);
  }

  listMovies(activeOnly = false): Observable<MovieRecord[]> {
    const params = new HttpParams().set('active_only', activeOnly);
    return this.http.get<MovieRecord[]>(this.baseUrl, { params });
  }

  createMovie(payload: MovieCreateRequest): Observable<MovieRecord> {
    return this.http.post<MovieRecord>(this.baseUrl, payload, {
      headers: { 'X-User-Role': this.auth.role() },
    });
  }

  updateMovie(movieId: string, payload: MovieUpdateRequest): Observable<MovieRecord> {
    return this.http.patch<MovieRecord>(`${this.baseUrl}/${encodeURIComponent(movieId)}`, payload, {
      headers: { 'X-User-Role': this.auth.role() },
    });
  }

  deleteMovie(movieId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${encodeURIComponent(movieId)}`, {
      headers: { 'X-User-Role': this.auth.role() },
    });
  }
}
