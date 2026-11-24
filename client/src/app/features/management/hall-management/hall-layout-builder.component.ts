import { CommonModule } from '@angular/common';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { HallService } from '../../../core/services/hall.service';
import {
  CinemaSummary,
  HallLayoutResponse,
  HallRow,
  SeatSlot,
  SeatType,
} from '../../../models/bms.models';

interface HallLayoutState {
  rows: HallRow[];
}

const DEFAULT_TIER_BY_TYPE: Record<SeatType, string> = {
  STANDARD: 'CLASSIC',
  PREMIUM: 'PRIME',
  RECLINER: 'RECLINER',
  WHEELCHAIR: 'ACCESSIBLE',
  AISLE: 'AISLE',
};

@Component({
  selector: 'app-hall-layout-builder',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './hall-layout-builder.component.html',
  styleUrl: './hall-layout-builder.component.css',
})
export class HallLayoutBuilderComponent implements OnInit {
  private readonly hallApi = inject(HallService);
  private readonly auth = inject(AuthService);

  readonly cinemas = signal<CinemaSummary[]>([]);
  readonly halls = signal<HallLayoutResponse[]>([]);
  readonly selectedCinemaId = signal<string>('');
  readonly selectedHallId = signal<string>('NEW');

  readonly hallName = signal<string>('Audi 1');
  readonly screenFormat = signal<string>('IMAX 2D');
  readonly activeBrush = signal<SeatType>('STANDARD');
  readonly layout = signal<HallLayoutState>({ rows: this.createInitialRows(4, 8) });

  readonly saving = signal<boolean>(false);
  readonly statusMessage = signal<string | null>(null);
  readonly errorMessage = signal<string | null>(null);

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

  readonly sellableSeatCount = computed(() => {
    let total = 0;
    for (const row of this.layout().rows) {
      for (const seat of row.seats) {
        if (seat.type !== 'AISLE' && seat.seat_number != null) {
          total++;
        }
      }
    }
    return total;
  });

  readonly brushes: { type: SeatType; label: string; badgeClass: string }[] = [
    { type: 'STANDARD', label: 'Standard', badgeClass: 'bg-slate-700 text-white' },
    { type: 'PREMIUM', label: 'Premium', badgeClass: 'bg-amber-600 text-white' },
    { type: 'RECLINER', label: 'Recliner', badgeClass: 'bg-purple-700 text-white' },
    { type: 'WHEELCHAIR', label: 'Wheelchair', badgeClass: 'bg-sky-700 text-white' },
    { type: 'AISLE', label: 'Aisle', badgeClass: 'bg-zinc-200 text-zinc-700' },
  ];

  ngOnInit(): void {
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
    this.selectedHallId.set('NEW');
    this.statusMessage.set(null);
    this.errorMessage.set(null);

    this.hallApi.listHalls(cinemaId).subscribe({
      next: (list) => this.halls.set(list),
      error: () => this.halls.set([]),
    });
  }

  onSelectHall(hallId: string): void {
    this.selectedHallId.set(hallId);
    this.statusMessage.set(null);
    this.errorMessage.set(null);

    if (hallId === 'NEW') {
      this.hallName.set('New Screen');
      this.screenFormat.set('2D');
      this.layout.set({ rows: this.createInitialRows(4, 8) });
      return;
    }

    this.hallApi.getHallLayout(hallId).subscribe({
      next: (hall) => {
        this.hallName.set(hall.name);
        this.screenFormat.set(hall.screen_format ?? '2D');
        this.layout.set(this.normalizeLayout(hall.layout));
      },
      error: () => this.errorMessage.set('Failed to load hall layout'),
    });
  }

  addRow(): void {
    const current = this.layout().rows;
    const nextCharCode = 65 + current.length;
    const label =
      nextCharCode <= 90 ? String.fromCharCode(nextCharCode) : `R${current.length + 1}`;
    const cols = current[0]?.seats.length ?? 8;
    const updatedRows = [...current, this.buildRow(label, cols, this.activeBrush())];
    this.layout.set({ rows: updatedRows });
  }

  removeLastRow(): void {
    const current = this.layout().rows;
    if (current.length <= 1) return;
    this.layout.set({ rows: current.slice(0, -1) });
  }

  addColumn(): void {
    const brush = this.activeBrush();
    const updatedRows = this.layout().rows.map((row) => {
      const nextSeats: SeatSlot[] = [
        ...row.seats,
        { seat_number: null, type: brush, tier: DEFAULT_TIER_BY_TYPE[brush] },
      ];
      return this.renumberRow(row.row_label, nextSeats);
    });
    this.layout.set({ rows: updatedRows });
  }

  removeLastColumn(): void {
    const updatedRows = this.layout().rows.map((row) => {
      if (row.seats.length <= 1) return row;
      return this.renumberRow(row.row_label, row.seats.slice(0, -1));
    });
    this.layout.set({ rows: updatedRows });
  }

  paintSeat(rowIndex: number, seatIndex: number): void {
    const brush = this.activeBrush();
    const updatedRows = this.layout().rows.map((row, rIdx) => {
      if (rIdx !== rowIndex) return row;
      const nextSeats: SeatSlot[] = row.seats.map((cell, sIdx) => {
        if (sIdx !== seatIndex) return cell;
        return {
          seat_number: null,
          type: brush,
          tier: DEFAULT_TIER_BY_TYPE[brush],
        };
      });
      return this.renumberRow(row.row_label, nextSeats);
    });
    this.layout.set({ rows: updatedRows });
  }

  saveHall(): void {
    const cinemaId = this.selectedCinemaId();
    if (!cinemaId) {
      this.errorMessage.set('Please select a cinema first');
      return;
    }

    this.saving.set(true);
    this.statusMessage.set(null);
    this.errorMessage.set(null);

    const normalized = this.normalizeLayout(this.layout());
    const hallId = this.selectedHallId();

    if (hallId === 'NEW') {
      this.hallApi
        .createHall({
          cinema_id: cinemaId,
          name: this.hallName().trim() || 'Screen 1',
          screen_format: this.screenFormat().trim() || '2D',
          layout: normalized,
        })
        .subscribe({
          next: (created) => {
            this.saving.set(false);
            this.halls.update((prev) => [...prev, created]);
            this.selectedHallId.set(created.hall_id);
            this.statusMessage.set(`Created ${created.name} (${created.total_seats} seats)`);
          },
          error: (err) => {
            this.saving.set(false);
            this.errorMessage.set(err?.error?.detail ?? 'Failed to create hall');
          },
        });
    } else {
      this.hallApi
        .updateHallLayout(hallId, {
          name: this.hallName().trim() || undefined,
          screen_format: this.screenFormat().trim() || undefined,
          layout: normalized,
        })
        .subscribe({
          next: (updated) => {
            this.saving.set(false);
            this.halls.update((prev) =>
              prev.map((h) => (h.hall_id === updated.hall_id ? updated : h))
            );
            this.statusMessage.set(`Saved layout (${updated.total_seats} sellable seats)`);
          },
          error: (err) => {
            this.saving.set(false);
            this.errorMessage.set(err?.error?.detail ?? 'Failed to update hall layout');
          },
        });
    }
  }

  seatCellClass(seat: SeatSlot): string {
    if (seat.type === 'AISLE') {
      return 'bg-zinc-100 text-zinc-400 border-dashed border-zinc-300';
    }
    if (seat.type === 'RECLINER') {
      return 'bg-purple-700 text-white border-purple-900';
    }
    if (seat.type === 'PREMIUM') {
      return 'bg-amber-600 text-white border-amber-800';
    }
    if (seat.type === 'WHEELCHAIR') {
      return 'bg-sky-700 text-white border-sky-900';
    }
    return 'bg-slate-700 text-white border-slate-900';
  }

  private createInitialRows(rowCount: number, colCount: number): HallRow[] {
    const rows: HallRow[] = [];
    for (let i = 0; i < rowCount; i++) {
      const label = String.fromCharCode(65 + i);
      rows.push(this.buildRow(label, colCount, 'STANDARD'));
    }
    return rows;
  }

  private buildRow(label: string, colCount: number, type: SeatType): HallRow {
    const seats: SeatSlot[] = Array.from({ length: colCount }, () => ({
      seat_number: null,
      type,
      tier: DEFAULT_TIER_BY_TYPE[type],
    }));
    return this.renumberRow(label, seats);
  }

  private renumberRow(label: string, seats: SeatSlot[]): HallRow {
    let seatNum = 1;
    const numbered: SeatSlot[] = seats.map((s) => {
      if (s.type === 'AISLE') {
        return { ...s, seat_number: null, tier: 'AISLE' };
      }
      return { ...s, seat_number: seatNum++ };
    });
    const primaryTier =
      numbered.find((s) => s.type !== 'AISLE')?.tier ?? DEFAULT_TIER_BY_TYPE.STANDARD;
    return { row_label: label, tier: primaryTier, seats: numbered };
  }

  private normalizeLayout(raw: HallLayoutState): HallLayoutState {
    const rows = (raw?.rows ?? []).map((r) => this.renumberRow(r.row_label, r.seats ?? []));
    return { rows };
  }
}