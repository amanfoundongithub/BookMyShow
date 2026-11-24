import { CommonModule } from '@angular/common';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CityService } from '../../../core/services/city.service';
import { MovieService } from '../../../core/services/movie.service';
import { CityListItem } from '../../../models/city.models';
import {
  MovieCreateRequest,
  MovieOptions,
  MovieRecord,
  MovieUpdateRequest,
} from '../../../models/movie.models';

@Component({
  selector: 'app-movie-management',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './movie-management.component.html',
  styleUrl: './movie-management.component.css',
})
export class MovieManagementComponent implements OnInit {
  private readonly cityService = inject(CityService);
  private readonly movieService = inject(MovieService);

  readonly movies = signal<MovieRecord[]>([]);
  readonly cities = signal<CityListItem[]>([]);
  readonly movieOptions = signal<MovieOptions | null>(null);
  readonly searchTerm = signal('');
  readonly pageNumber = signal(1);
  readonly pageSize = signal(10);
  readonly openDropdown = signal<'cities' | 'languages' | 'formats' | null>(null);
  readonly movieId = signal('');
  readonly title = signal('');
  readonly durationMinutes = signal<number | null>(null);
  readonly rating = signal('');
  readonly languages = signal<string[]>([]);
  readonly formats = signal<string[]>([]);
  readonly synopsis = signal('');
  readonly selectedCityIds = signal<string[]>([]);
  readonly releaseDate = signal('');
  readonly posterUrl = signal('');
  readonly isActive = signal(true);
  readonly editingMovieId = signal<string | null>(null);
  readonly deletingMovieId = signal<string | null>(null);
  readonly loadingMovies = signal(true);
  readonly loadingCities = signal(true);
  readonly loadingOptions = signal(true);
  readonly saving = signal(false);
  readonly deleteInProgress = signal(false);
  readonly movieListError = signal<string | null>(null);
  readonly citiesError = signal<string | null>(null);
  readonly optionsError = signal<string | null>(null);
  readonly errorMessage = signal<string | null>(null);
  readonly statusMessage = signal<string | null>(null);

  readonly filteredMovies = computed(() => {
    const query = this.searchTerm().trim().toLowerCase();
    if (!query) return this.movies();
    const cities = this.cities();
    return this.movies().filter((movie) =>
      [
        movie.title,
        movie.id,
        movie.rating,
        ...movie.languages,
        ...movie.formats,
        ...movie.city_ids,
        ...movie.city_ids.flatMap((id) => {
          const city = cities.find((item) => item.id === id);
          return city ? [city.name, city.state] : [];
        }),
      ].some((value) => value.toLowerCase().includes(query))
    );
  });

  readonly allCitiesSelected = computed(() =>
    this.cities().length > 0 &&
    this.cities().every((city) => this.selectedCityIds().includes(city.id))
  );
  readonly allLanguagesSelected = computed(() => {
    const options = this.movieOptions()?.languages ?? [];
    return options.length > 0 && options.every((option) => this.languages().includes(option));
  });
  readonly allFormatsSelected = computed(() => {
    const options = this.movieOptions()?.formats ?? [];
    return options.length > 0 && options.every((option) => this.formats().includes(option));
  });
  readonly pageCount = computed(() =>
    Math.max(1, Math.ceil(this.filteredMovies().length / this.pageSize()))
  );
  readonly currentPage = computed(() => Math.min(this.pageNumber(), this.pageCount()));
  readonly paginatedMovies = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize();
    return this.filteredMovies().slice(start, start + this.pageSize());
  });
  readonly firstVisibleRow = computed(() =>
    this.filteredMovies().length ? (this.currentPage() - 1) * this.pageSize() + 1 : 0
  );
  readonly lastVisibleRow = computed(() =>
    Math.min(this.currentPage() * this.pageSize(), this.filteredMovies().length)
  );

  ngOnInit(): void {
    this.loadMovies();
    this.loadMovieOptions();
    this.loadCities();
  }

  loadCities(): void {
    this.loadingCities.set(true);
    this.citiesError.set(null);

    this.cityService.getAllCities().subscribe({
      next: (cities) => {
        this.cities.set(cities);
        const editingMovie = this.movies().find((movie) => movie.id === this.editingMovieId());
        this.selectedCityIds.set(
          editingMovie?.city_ids.length
            ? [...editingMovie.city_ids]
            : cities.map((city) => city.id)
        );
        this.loadingCities.set(false);
      },
      error: (err) => {
        this.loadingCities.set(false);
        this.citiesError.set(err?.error?.detail ?? 'Failed to load cities.');
      },
    });
  }

  loadMovies(): void {
    this.loadingMovies.set(true);
    this.movieListError.set(null);

    this.movieService.listMovies().subscribe({
      next: (movies) => {
        this.movies.set(movies);
        this.loadingMovies.set(false);
      },
      error: (err) => {
        this.loadingMovies.set(false);
        this.movieListError.set(err?.error?.detail ?? 'Failed to load movies.');
      },
    });
  }

  loadMovieOptions(): void {
    this.loadingOptions.set(true);
    this.optionsError.set(null);

    this.movieService.getMovieOptions().subscribe({
      next: (options) => {
        this.movieOptions.set(options);
        this.loadingOptions.set(false);
        this.rating.set(options.ratings.includes('UA') ? 'UA' : (options.ratings[0] ?? ''));
        this.languages.set([...options.languages]);
        this.formats.set([...options.formats]);
      },
      error: (err) => {
        this.loadingOptions.set(false);
        this.optionsError.set(err?.error?.detail ?? 'Failed to load movie options.');
      },
    });
  }

  setSearchTerm(value: string): void {
    this.searchTerm.set(value);
    this.pageNumber.set(1);
  }

  setPageSize(value: number): void {
    this.pageSize.set(value);
    this.pageNumber.set(1);
  }

  previousPage(): void {
    this.pageNumber.update((page) => Math.max(1, page - 1));
  }

  nextPage(): void {
    this.pageNumber.update((page) => Math.min(this.pageCount(), page + 1));
  }

  toggleDropdown(dropdown: 'cities' | 'languages' | 'formats'): void {
    this.openDropdown.update((current) => current === dropdown ? null : dropdown);
  }

  selectAllCities(): void {
    this.selectedCityIds.set(this.cities().map((city) => city.id));
  }

  selectAllLanguages(): void {
    this.languages.set([...(this.movieOptions()?.languages ?? [])]);
  }

  selectAllFormats(): void {
    this.formats.set([...(this.movieOptions()?.formats ?? [])]);
  }

  toggleCity(cityId: string, event: Event): void {
    const checkbox = event.target;
    if (!(checkbox instanceof HTMLInputElement)) return;
    if (!checkbox.checked && this.selectedCityIds().length <= 1) {
      checkbox.checked = true;
      return;
    }
    this.selectedCityIds.update((ids) =>
      checkbox.checked ? [...new Set([...ids, cityId])] : ids.filter((id) => id !== cityId)
    );
  }

  toggleLanguage(language: string, event: Event): void {
    const checkbox = event.target;
    if (!(checkbox instanceof HTMLInputElement)) return;
    this.languages.update((values) =>
      checkbox.checked
        ? [...new Set([...values, language])]
        : values.filter((value) => value !== language)
    );
  }

  toggleFormat(format: string, event: Event): void {
    const checkbox = event.target;
    if (!(checkbox instanceof HTMLInputElement)) return;
    this.formats.update((values) =>
      checkbox.checked
        ? [...new Set([...values, format])]
        : values.filter((value) => value !== format)
    );
  }

  closeDropdown(): void {
    this.openDropdown.set(null);
  }

  submitMovie(): void {
    const fields = this.buildMovieFields();
    if (!fields) return;

    this.saving.set(true);
    this.errorMessage.set(null);
    this.statusMessage.set(null);

    const editingId = this.editingMovieId();
    if (editingId) {
      const {
        synopsis,
        release_date: releaseDate,
        poster_url: posterUrl,
        ...requiredFields
      } = fields;
      const payload: MovieUpdateRequest = {
        ...requiredFields,
        ...(synopsis !== null ? { synopsis } : {}),
        ...(releaseDate !== null ? { release_date: releaseDate } : {}),
        ...(posterUrl !== null ? { poster_url: posterUrl } : {}),
      };
      this.movieService.updateMovie(editingId, payload).subscribe({
        next: (updated) => {
          this.movies.update((movies) =>
            movies
              .map((movie) => (movie.id === updated.id ? updated : movie))
              .sort((a, b) => a.title.localeCompare(b.title))
          );
          this.saving.set(false);
          this.statusMessage.set(`${updated.title} updated successfully.`);
          this.resetForm();
        },
        error: (err) => {
          this.saving.set(false);
          this.errorMessage.set(err?.error?.detail ?? 'Failed to update movie.');
        },
      });
      return;
    }

    const payload: MovieCreateRequest = {
      ...fields,
      id: this.movieId().trim() || undefined,
    };
    this.movieService.createMovie(payload).subscribe({
      next: (created) => {
        this.movies.update((movies) =>
          [...movies, created].sort((a, b) => a.title.localeCompare(b.title))
        );
        this.saving.set(false);
        this.statusMessage.set(`${created.title} added to the catalog.`);
        this.resetForm();
      },
      error: (err) => {
        this.saving.set(false);
        this.errorMessage.set(err?.error?.detail ?? 'Failed to create movie.');
      },
    });
  }

  editMovie(movie: MovieRecord): void {
    this.editingMovieId.set(movie.id);
    this.movieId.set(movie.id);
    this.title.set(movie.title);
    this.durationMinutes.set(movie.duration_minutes);
    this.rating.set(movie.rating);
    this.languages.set([...movie.languages]);
    this.formats.set([...movie.formats]);
    this.synopsis.set(movie.synopsis ?? '');
    this.selectedCityIds.set(
      movie.city_ids.length ? [...movie.city_ids] : this.cities().map((city) => city.id)
    );
    this.releaseDate.set(movie.release_date ?? '');
    this.posterUrl.set(movie.poster_url ?? '');
    this.isActive.set(movie.is_active);
    this.openDropdown.set(null);
    this.deletingMovieId.set(null);
    this.errorMessage.set(null);
    this.statusMessage.set(null);
  }

  requestDelete(movie: MovieRecord): void {
    this.deletingMovieId.set(movie.id);
    this.errorMessage.set(null);
    this.statusMessage.set(null);
  }

  cityAvailability(movie: MovieRecord): string {
    if (movie.city_ids.length === 0) return 'All cities';
    const cities = this.cities();
    return movie.city_ids
      .map((id) => cities.find((city) => city.id === id)?.name ?? id)
      .join(', ');
  }

  confirmDelete(movie: MovieRecord): void {
    if (this.deleteInProgress()) return;

    this.deletingMovieId.set(movie.id);
    this.deleteInProgress.set(true);
    this.errorMessage.set(null);
    this.statusMessage.set(null);
    this.movieService.deleteMovie(movie.id).subscribe({
      next: () => {
        this.movies.update((movies) => movies.filter((item) => item.id !== movie.id));
        this.deletingMovieId.set(null);
        this.deleteInProgress.set(false);
        this.statusMessage.set(`${movie.title} deleted.`);
        if (this.editingMovieId() === movie.id) this.resetForm();
      },
      error: (err) => {
        this.deletingMovieId.set(null);
        this.deleteInProgress.set(false);
        this.errorMessage.set(err?.error?.detail ?? 'Failed to delete movie.');
      },
    });
  }

  cancelDelete(): void {
    if (!this.deleteInProgress()) this.deletingMovieId.set(null);
  }

  resetForm(): void {
    this.editingMovieId.set(null);
    this.movieId.set('');
    this.title.set('');
    this.durationMinutes.set(null);
    const options = this.movieOptions();
    this.rating.set(options?.ratings.includes('UA') ? 'UA' : (options?.ratings[0] ?? ''));
    this.languages.set([...(options?.languages ?? [])]);
    this.formats.set([...(options?.formats ?? [])]);
    this.synopsis.set('');
    this.selectedCityIds.set(this.cities().map((city) => city.id));
    this.releaseDate.set('');
    this.posterUrl.set('');
    this.isActive.set(true);
    this.openDropdown.set(null);
  }

  private buildMovieFields(): Omit<MovieCreateRequest, 'id'> | null {
    const title = this.title().trim();
    const id = this.movieId().trim();
    const duration = this.durationMinutes();
    const options = this.movieOptions();

    if (!options) {
      this.errorMessage.set('Movie options are unavailable. Reload them before saving.');
      return null;
    }
    if (!title || duration == null || !Number.isInteger(duration) || duration < 1 || duration > 600) {
      this.errorMessage.set('Enter a title and a whole-number runtime between 1 and 600 minutes.');
      return null;
    }
    if (!this.editingMovieId() && id.length === 1) {
      this.errorMessage.set('Movie IDs must be at least 2 characters long.');
      return null;
    }
    if (!this.rating() || this.languages().length === 0 || this.formats().length === 0) {
      this.errorMessage.set('Select a rating, at least one language, and at least one format.');
      return null;
    }

    const cityIds =
      this.cities().length > 0 && this.allCitiesSelected()
        ? []
        : [...this.selectedCityIds()];

    return {
      title,
      duration_minutes: duration,
      rating: this.rating(),
      languages: [...this.languages()],
      formats: [...this.formats()],
      synopsis: this.synopsis().trim() || null,
      city_ids: cityIds,
      release_date: this.releaseDate() || null,
      poster_url: this.posterUrl().trim() || null,
      is_active: this.isActive(),
    };
  }
}
