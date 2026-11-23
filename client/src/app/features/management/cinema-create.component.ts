import { CommonModule } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { City, CinemaSummary } from '../../models/bms.models';
import { CatalogService } from '../../core/services/catalog.service';
import { HallService } from '../../core/services/hall.service';

@Component({
  selector: 'app-cinema-create',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './cinema-create.component.html',
  styleUrl : './cinema-create.component.css'
})
export class CinemaCreateComponent implements OnInit {
  private readonly hallApi = inject(HallService);
  private readonly catalogApi = inject(CatalogService);

  readonly cities = signal<City[]>([]);
  readonly name = signal<string>('');
  readonly cityId = signal<string>('');
  readonly stateName = signal<string>('');
  readonly address = signal<string>('');
  readonly amenitiesInput = signal<string>('IMAX, Dolby Atmos, Recliner');
  readonly isActive = signal<boolean>(true);

  readonly submitting = signal<boolean>(false);
  readonly errorMessage = signal<string | null>(null);
  readonly createdCinema = signal<CinemaSummary | null>(null);

  ngOnInit(): void {
    const getCitiesFn = (
      this.catalogApi as unknown as {
        getCities?: () => {
          subscribe: (cb: { next: (cities: City[]) => void; error: () => void }) => void;
        };
      }
    ).getCities;

    if (getCitiesFn) {
      getCitiesFn.call(this.catalogApi).subscribe({
        next: (list) => {
          this.cities.set(list);
          if (list.length > 0 && !this.cityId()) {
            this.cityId.set(list[0].id);
            this.stateName.set(list[0].state ?? '');
          }
        },
        error: () => this.cities.set([]),
      });
    }
  }

  onCitySelect(id: string): void {
    this.cityId.set(id);
    const match = this.cities().find((c) => c.id === id);
    if (match?.state) {
      this.stateName.set(match.state);
    }
  }

  submitCinema(): void {
    const trimmedName = this.name().trim();
    const trimmedCity = this.cityId().trim();
    const trimmedAddress = this.address().trim();

    if (!trimmedName || !trimmedCity || !trimmedAddress) {
      this.errorMessage.set('Cinema name, city, and address are required.');
      return;
    }

    const amenities = this.amenitiesInput()
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);

    this.submitting.set(true);
    this.errorMessage.set(null);
    this.createdCinema.set(null);

    this.hallApi
      .createCinema({
        name: trimmedName,
        city_id: trimmedCity,
        state: this.stateName().trim() || null,
        address: trimmedAddress,
        amenities,
        is_active: this.isActive(),
      })
      .subscribe({
        next: (created) => {
          this.submitting.set(false);
          this.createdCinema.set(created);
          this.name.set('');
          this.address.set('');
        },
        error: (err) => {
          this.submitting.set(false);
          this.errorMessage.set(err?.error?.detail ?? 'Failed to create cinema.');
        },
      });
  }
}