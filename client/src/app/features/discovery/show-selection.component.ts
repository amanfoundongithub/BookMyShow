import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { CatalogService } from '../../core/services/catalog.service';
import { City, Movie, Show } from '../../models/bms.models';
import { CityService } from '../../core/services/city.service';
import { ShowSearchResponseItem } from '../../models/show.models';

@Component({
  selector: 'app-show-selection',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './show-selection.component.html',
  styleUrl: './show-selection.component.css',
})
export class ShowSelectionComponent implements OnInit {

  private readonly catalogService = inject(CatalogService);
  private readonly cityService    = inject(CityService);

  readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  readonly cities = signal<City[]>([]);
  readonly selectedState = signal<string>('');
  readonly selectedCityId = signal<string>('');
  readonly movies = signal<Movie[]>([]);
  readonly selectedMovie = signal<Movie | null>(null);
  readonly selectedDate = signal<string>(new Date().toISOString().slice(0, 10));
  readonly shows = signal<ShowSearchResponseItem[]>([]);

  readonly loadingMovies = signal<boolean>(false);
  readonly loadingShows = signal<boolean>(false);
  readonly errorMessage = signal<string | null>(null);

  readonly states = computed(() => {
    const unique = new Set(
      this.cities()
        .map((c) => c.state?.trim())
        .filter((s): s is string => Boolean(s))
    );
    return Array.from(unique).sort((a, b) => a.localeCompare(b));
  });

  readonly citiesInSelectedState = computed(() => {
    const state = this.selectedState();
    if (!state) return [];
    return this.cities().filter((c) => c.state === state);
  });

  readonly selectedCity = computed(() => {
    const cityId = this.selectedCityId();
    if (!cityId) return null;
    return this.cities().find((c) => c.id === cityId) ?? null;
  });

  ngOnInit(): void {
    this.loadCities();
  }

  onStateChange(state: string): void {
    this.selectedState.set(state);
    this.selectedCityId.set('');
    this.selectedMovie.set(null);
    this.movies.set([]);
    this.shows.set([]);
  };

  onCityChange(cityId: string): void {
    this.selectedCityId.set(cityId);
    this.selectedMovie.set(null);
    this.shows.set([]);
    if (cityId) {
      this.loadMovies(cityId);
    } else {
      this.movies.set([]);
    }
  }

  selectMovie(movie: Movie): void {
    this.selectedMovie.set(movie);
    this.loadShows();
  }

  onDateChange(dateStr: string): void {
    this.selectedDate.set(dateStr);
    if (this.selectedMovie()) {
      this.loadShows();
    }
  }

  getTierEntries(pricing: Record<string, number>): [string, number][] {
    return Object.entries(pricing || {});
  }

  openSeatMap(show: ShowSearchResponseItem): void {
    this.router.navigate(['/shows', show.id, 'seats'], {
      queryParams: {
        hallId: show.hall_id,
        pricing: JSON.stringify(show.pricing ?? {}),
      },
    });
  }

  private loadMovies(cityId: string): void {
    this.loadingMovies.set(true);
    this.errorMessage.set(null);
    this.catalogService.getAllMoviesByCity(cityId).subscribe({
      next: (movies) => {
        this.movies.set(movies);
        this.loadingMovies.set(false);
      },
      error: () => {
        this.loadingMovies.set(false);
        this.errorMessage.set('Failed to load movies for the selected city.');
      },
    });
  }

  private loadShows(): void {
    const movie = this.selectedMovie();
    if (!movie) return;
    this.loadingShows.set(true);
    this.errorMessage.set(null);
    this.catalogService
      .getAllShowsForMovieInACityForADate(movie.id, this.selectedDate(), this.selectedCityId())
      .subscribe({
        next: (shows) => {
          this.shows.set(shows);
          this.loadingShows.set(false);
        },
        error: () => {
          this.loadingShows.set(false);
          this.errorMessage.set('Failed to load showtimes.');
        },
      });
  }

  // Load cities
  private loadCities() : void {
    this.errorMessage.set(null);
    this.cityService.getAllCities().subscribe({
      next : (cities) => {
        this.cities.set(cities);
      },
      error : (err) => {
        console.log("Error in fetching cities data:", err);
        this.errorMessage.set("Error occured while fetching cities data. Please try again.");
      }
    })
  };

}