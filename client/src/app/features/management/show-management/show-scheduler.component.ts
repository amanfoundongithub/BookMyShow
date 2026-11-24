import { CommonModule } from '@angular/common';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { CatalogService } from '../../core/services/catalog.service';
import { HallService } from '../../core/services/hall.service';
import { CinemaSummary, HallLayoutResponse, Movie, Show } from '../../models/bms.models';

@Component({
  selector: 'app-show-scheduler',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './show-scheduler.component.html',
  styleUrl : './show-scheduler.component.css'
})
export class ShowSchedulerComponent implements OnInit {
  private readonly hallApi = inject(HallService);
  private readonly catalogApi = inject(CatalogService);
  private readonly auth = inject(AuthService);

  readonly cinemas = signal<CinemaSummary[]>([]);
  readonly halls = signal<HallLayoutResponse[]>([]);
  readonly movies = signal<Movie[]>([]);

  readonly selectedCinemaId = signal<string>('');
  readonly selectedHallId = signal<string>('');
  readonly selectedMovieId = signal<string>('');
  readonly language = signal<string>('English');
  readonly format = signal<string>('IMAX 2D');
  readonly startTimeLocal = signal<string>('');
  readonly durationMinutes = signal<number>(148);

  readonly reclinerPrice = signal<number>(450);
  readonly primePrice = signal<number>(280);
  readonly classicPrice = signal<number>(180);

  readonly submitting = signal<boolean>(false);
  readonly statusMessage = signal<string | null>(null);
  readonly errorMessage = signal<string | null>(null);
  readonly lastCreatedShow = signal<Show | null>(null);

  readonly allowedCinemas = computed(() => {
    const all = this.cinemas();
    const role = (
      (this.auth as unknown as { userRole?: () => string; role?: () => string }).userRole?.() ??
      (this.auth as unknown as { role?: () => string }).role?.() ??
      ''
    ).toUpperCase();
    if (role === 'ADMIN') {
      return all;
    }
    const rawIds =
      (this.auth as unknown as { cinemaIds?: () => string[] }).cinemaIds?.() ?? [];
    const owned = new Set<string>(rawIds);
    return owned.size > 0 ? all.filter((c) => owned.has(c.cinema_id)) : all;
  });

  ngOnInit(): void {
    const now = new Date(Date.now() + 60 * 60 * 1000);
    now.setMinutes(0, 0, 0);
    this.startTimeLocal.set(this.toDatetimeLocalInput(now));

    this.hallApi.listCinemas().subscribe({
      next: (list) => {
        this.cinemas.set(list);
        const scoped = this.allowedCinemas();
        if (scoped.length > 0) {
          this.onSelectCinema(scoped[0].cinema_id);
        }
      },
      error: () => this.errorMessage.set('Failed to load cinemas'),
    });
  }

  onSelectCinema(cinemaId: string): void {
    this.selectedCinemaId.set(cinemaId);
    this.selectedHallId.set('');
    this.statusMessage.set(null);
    this.errorMessage.set(null);

    this.hallApi.listHalls(cinemaId).subscribe({
      next: (hallList) => {
        this.halls.set(hallList);
        if (hallList.length > 0) {
          this.selectedHallId.set(hallList[0].hall_id);
        }
      },
      error: () => this.halls.set([]),
    });

    const cinema = this.cinemas().find((c) => c.cinema_id === cinemaId);
    const cityId = cinema?.city_id;
    if (cityId && typeof (this.catalogApi as unknown as { getMovies?: (c: string) => unknown }).getMovies === 'function') {
      (
        this.catalogApi as unknown as { getMovies: (c: string) => { subscribe: (cb: { next: (m: Movie[]) => void; error: () => void }) => void } }
      )
        .getMovies(cityId)
        .subscribe({
          next: (movieList) => {
            this.movies.set(movieList);
            if (movieList.length > 0) {
              this.onSelectMovie(movieList[0].id);
            }
          },
          error: () => this.movies.set([]),
        });
    }
  }

  onSelectMovie(movieId: string): void {
    this.selectedMovieId.set(movieId);
    const movie = this.movies().find((m) => m.id === movieId);
    if (movie) {
      this.durationMinutes.set(movie.duration_minutes);
      if (movie.languages?.length) this.language.set(movie.languages[0]);
      if (movie.formats?.length) this.format.set(movie.formats[0]);
    }
  }

  createShow(): void {
    const cinemaId = this.selectedCinemaId();
    const hallId = this.selectedHallId();
    const movieId = this.selectedMovieId().trim();
    const startRaw = this.startTimeLocal();

    if (!cinemaId || !hallId || !movieId || !startRaw) {
      this.errorMessage.set('Cinema, hall, movie ID, and start time are required');
      return;
    }

    const startDate = new Date(startRaw);
    if (Number.isNaN(startDate.getTime())) {
      this.errorMessage.set('Invalid start time');
      return;
    }

    const endDate = new Date(startDate.getTime() + this.durationMinutes() * 60 * 1000);
    const showId = `show_${Date.now().toString(36)}`;

    const payload = {
      id: showId,
      movie_id: movieId,
      cinema_id: cinemaId,
      hall_id: hallId,
      start_time: startDate.toISOString(),
      end_time: endDate.toISOString(),
      language: this.language().trim() || 'English',
      format: this.format().trim() || '2D',
      pricing: {
        RECLINER: Number(this.reclinerPrice()),
        PRIME: Number(this.primePrice()),
        CLASSIC: Number(this.classicPrice()),
      },
    };

    this.submitting.set(true);
    this.statusMessage.set(null);
    this.errorMessage.set(null);

    const createFn = (
      this.catalogApi as unknown as {
        createShow?: (body: typeof payload) => { subscribe: (cb: { next: (res: Show) => void; error: (err: { error?: { detail?: string } }) => void }) => void };
      }
    ).createShow;

    if (!createFn) {
      this.submitting.set(false);
      this.errorMessage.set('CatalogService.createShow is not yet defined');
      return;
    }

    createFn.call(this.catalogApi, payload).subscribe({
      next: (created) => {
        this.submitting.set(false);
        this.lastCreatedShow.set(created);
        this.statusMessage.set(`Scheduled show ${created.id} in ${created.hall_id}`);
      },
      error: (err) => {
        this.submitting.set(false);
        this.errorMessage.set(err?.error?.detail ?? 'Failed to schedule show');
      },
    });
  }

  private toDatetimeLocalInput(d: Date): string {
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
}