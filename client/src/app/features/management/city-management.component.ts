import { CommonModule } from '@angular/common';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CityService } from '../../core/services/city.service';
import {
  CityCreateRequest,
  CityListItem,
  CityUpdateRequest,
} from '../../models/city.models';

@Component({
  selector: 'app-city-management',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './city-management.component.html',
  styleUrl: './city-management.component.css',
})
export class CityManagementComponent implements OnInit {
  private readonly cityApi = inject(CityService);

  readonly cities = signal<CityListItem[]>([]);
  readonly searchTerm = signal('');
  readonly cityId = signal('');
  readonly name = signal('');
  readonly state = signal('');
  readonly country = signal('India');
  readonly editingCityId = signal<string | null>(null);
  readonly deletingCityId = signal<string | null>(null);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly statusMessage = signal<string | null>(null);

  readonly filteredCities = computed(() => {
    const query = this.searchTerm().trim().toLowerCase();
    if (!query) return this.cities();
    return this.cities().filter((city) =>
      [city.name, city.state, city.country, city.id]
        .some((value) => value.toLowerCase().includes(query))
    );
  });

  ngOnInit(): void {
    this.loadCities();
  }

  loadCities(): void {
    this.loading.set(true);
    this.errorMessage.set(null);

    this.cityApi.getAllCities().subscribe({
      next: (cities) => {
        this.cities.set(cities);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.errorMessage.set(err?.error?.detail ?? 'Failed to load cities.');
      },
    });
  }

  submitCity(): void {
    const id = this.cityId().trim();
    const name = this.name().trim();
    const state = this.state().trim();
    const country = this.country().trim();

    if ((!this.editingCityId() && !id) || !name || !state || !country) {
      this.errorMessage.set('City ID, name, state, and country are required.');
      return;
    }

    this.saving.set(true);
    this.errorMessage.set(null);
    this.statusMessage.set(null);

    if (this.editingCityId()) {
      const payload: CityUpdateRequest = { name, state, country };
      this.cityApi.updateCity(payload, this.editingCityId()!).subscribe({
        next: (updated) => {
          this.cities.update((cities) =>
            cities
              .map((city) => (city.id === updated.id ? updated : city))
              .sort((a, b) => a.name.localeCompare(b.name))
          );
          this.saving.set(false);
          this.statusMessage.set(`${updated.name} updated successfully.`);
          this.resetForm();
        },
        error: (err) => {
          this.saving.set(false);
          this.errorMessage.set(err?.error?.detail ?? 'Failed to update city.');
        },
      });
      return;
    }

    const payload: CityCreateRequest = { id, name, state, country };
    this.cityApi.createCity(payload).subscribe({
      next: (created) => {
        this.cities.update((cities) =>
          [...cities, created].sort((a, b) => a.name.localeCompare(b.name))
        );
        this.saving.set(false);
        this.statusMessage.set(`${created.name} created successfully.`);
        this.resetForm();
      },
      error: (err) => {
        this.saving.set(false);
        this.errorMessage.set(err?.error?.detail ?? 'Failed to create city.');
      },
    });
  }

  editCity(city: CityListItem): void {
    this.editingCityId.set(city.id);
    this.cityId.set(city.id);
    this.name.set(city.name);
    this.state.set(city.state);
    this.country.set(city.country);
    this.statusMessage.set(null);
    this.errorMessage.set(null);
    this.deletingCityId.set(null);
  }

  deleteCity(city: CityListItem): void {
    this.deletingCityId.set(city.id);
    this.errorMessage.set(null);
    this.statusMessage.set(null);
  }

  confirmDelete(city: CityListItem): void {
    this.deletingCityId.set(city.id);
    this.cityApi.deleteCity(city.id).subscribe({
      next: () => {
        this.cities.update((cities) => cities.filter((item) => item.id !== city.id));
        this.deletingCityId.set(null);
        this.statusMessage.set(`${city.name} deleted successfully.`);
        if (this.editingCityId() === city.id) this.resetForm();
      },
      error: (err) => {
        this.deletingCityId.set(null);
        this.errorMessage.set(err?.error?.detail ?? 'Failed to delete city.');
      },
    });
  }

  resetForm(): void {
    this.editingCityId.set(null);
    this.cityId.set('');
    this.name.set('');
    this.state.set('');
    this.country.set('India');
  }
}
