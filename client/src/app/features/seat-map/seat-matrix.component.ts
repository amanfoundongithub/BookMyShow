import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription, forkJoin } from 'rxjs';
import { AuthService } from '../../core/services/auth.service';
import { BookingService } from '../../core/services/booking.service';
import { CatalogService } from '../../core/services/catalog.service';
import { WsSeatService } from '../../core/services/ws-seat.service';
import {
  HallRow,
  HoldSeatsResponse,
  SeatLockStatus,
  SeatStatusUpdateEvent,
} from '../../models/bms.models';
import { HoldCountdownComponent } from './hold-countdown.component';
import { HallService } from '../../core/services/hall.service';

type VisualSeatState = 'AVAILABLE' | 'SELECTED' | 'HELD' | 'CONFIRMED';

@Component({
  selector: 'app-seat-matrix',
  standalone: true,
  imports: [CommonModule, HoldCountdownComponent],
  templateUrl: './seat-matrix.component.html',
  styleUrl: './seat-matrix.component.css',
})
export class SeatMatrixComponent implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly bookingService = inject(BookingService);
  private readonly hallService = inject(HallService);
  private readonly authService = inject(AuthService);
  private readonly showService = inject(CatalogService);

  readonly wsService = inject(WsSeatService);

  readonly showId = signal<string>('');
  readonly hallId = signal<string>('hall_audi_2');
  readonly pricing = signal<Record<string, number>>({});

  readonly rows = signal<HallRow[]>([]);
  readonly seatStatuses = signal<Record<string, SeatLockStatus>>({});
  readonly selectedSeats = signal<string[]>([]);
  readonly selectedTier = signal<string | null>(null);
  readonly activeHold = signal<HoldSeatsResponse | null>(null);

  readonly loading = signal<boolean>(true);
  readonly submitting = signal<boolean>(false);
  readonly errorMessage = signal<string | null>(null);
  readonly infoMessage = signal<string | null>(null);

  readonly estimatedTotal = computed(() => {
    const tier = this.selectedTier();
    const prices = this.pricing();
    const count = this.selectedSeats().length;
    if (!tier || !count) return 0;
    const unitPrice = prices[tier] ?? 0;
    return unitPrice * count;
  });

  private wsSub: Subscription | null = null;

  ngOnInit(): void {

    const paramShowId = this.route.snapshot.paramMap.get('showId') ??'';

    const queryHallId = this.route.snapshot.queryParamMap.get('hallId') ?? 'hall_audi_2';
    const rawPricing = this.route.snapshot.queryParamMap.get('pricing');

    this.showId.set(paramShowId);
    this.hallId.set(queryHallId);

    if (rawPricing) {
      try {
        this.pricing.set(JSON.parse(rawPricing) as Record<string, number>);
      } catch {
        this.pricing.set({});
      }
    }

    this.loadInitialData();
    this.subscribeToWsUpdates(paramShowId);
  }

  ngOnDestroy(): void {
    this.wsSub?.unsubscribe();
    this.wsService.disconnect();
  }

  formatSeatCode(rowLabel: string, seatNumber?: number): string {
    return `${rowLabel}${seatNumber ?? ''}`;
  }

  getSeatVisualState(code: string): VisualSeatState {
    const heldSeats = this.activeHold()?.seats ?? [];
    if (heldSeats.includes(code) || this.selectedSeats().includes(code)) {
      return 'SELECTED';
    }
    const status = this.seatStatuses()[code];
    if (status === 'CONFIRMED') return 'CONFIRMED';
    if (status === 'HELD') return 'HELD';
    return 'AVAILABLE';
  }

  isSeatDisabled(code: string, state: VisualSeatState): boolean {
    if (this.activeHold() || this.submitting()) return true;
    if (state === 'CONFIRMED') return true;
    if (state === 'HELD' && !this.selectedSeats().includes(code)) return true;
    return false;
  }

  toggleSeat(code: string, tier: string): void {
    if (this.activeHold() || this.submitting()) return;
    this.errorMessage.set(null);
    this.infoMessage.set(null);

    const current = this.selectedSeats();
    if (current.includes(code)) {
      const next = current.filter((s) => s !== code);
      this.selectedSeats.set(next);
      if (next.length === 0) {
        this.selectedTier.set(null);
      }
      return;
    }

    if (this.selectedTier() && this.selectedTier() !== tier) {
      this.errorMessage.set(`Please select seats within the same tier (${this.selectedTier()}).`);
      return;
    }

    this.selectedTier.set(tier);
    this.selectedSeats.set([...current, code]);
  }

  holdSelectedSeats(): void {
    const seats = this.selectedSeats();
    const tier = this.selectedTier();
    if (!seats.length || !tier || this.submitting()) return;

    this.submitting.set(true);
    this.errorMessage.set(null);
    this.infoMessage.set(null);

    const tierPrice = this.pricing()[tier];

    this.bookingService
      .holdSeats(
        {
          show_id: this.showId(),
          user_id: this.authService.userId(),
          seats,
          tier,
        },
        tierPrice
      )
      .subscribe({
        next: (hold) => {
          this.submitting.set(false);
          this.activeHold.set(hold);
          this.selectedSeats.set([]);
          this.infoMessage.set('Seats locked! Complete payment before the hold expires.');
        },
        error: (err: HttpErrorResponse) => {
          this.submitting.set(false);
          if (err.status === 409) {
            this.errorMessage.set(
              'One or more selected seats were just taken. Refreshing live seat map...'
            );
            this.selectedSeats.set([]);
            this.selectedTier.set(null);
            this.refreshSeatMap();
          } else {
            this.errorMessage.set(err.error?.detail ?? 'Could not lock selected seats.');
          }
        },
      });
  }

  releaseCurrentHold(): void {
    const hold = this.activeHold();
    if (!hold || this.submitting()) return;

    this.submitting.set(true);
    this.errorMessage.set(null);

    this.bookingService
      .releaseBooking({
        booking_id: hold.booking_id,
        user_id: this.authService.userId(),
      })
      .subscribe({
        next: () => {
          this.submitting.set(false);
          this.activeHold.set(null);
          this.selectedTier.set(null);
          this.infoMessage.set('Hold released. Seats are available again.');
          this.refreshSeatMap();
        },
        error: (err: HttpErrorResponse) => {
          this.submitting.set(false);
          this.errorMessage.set(err.error?.detail ?? 'Failed to release hold.');
        },
      });
  }

  onHoldExpired(): void {
    this.activeHold.set(null);
    this.selectedSeats.set([]);
    this.selectedTier.set(null);
    this.errorMessage.set('Seat hold expired. Please select your seats again.');
    this.refreshSeatMap();
  }

  proceedToCheckout(): void {
    const hold = this.activeHold();
    if (!hold) return;

    this.router.navigate(['/checkout'], {
      state: { hold },
    });
  }

  private loadInitialData(): void {
    this.loading.set(true);
    this.errorMessage.set(null);

    forkJoin({
      showDetails : this.showService.getShowDetailsById(this.showId()),
      layout: this.hallService.getHallLayout(this.hallId()),
      seatMap: this.bookingService.getSeatMap(this.showId(), this.hallId()),
    }).subscribe({
      next: ({ layout, seatMap, showDetails }) => {
        this.rows.set(layout.layout?.rows ?? []);
        this.seatStatuses.set({ ...(seatMap.seats ?? {}) });
        this.loading.set(false);
        this.pricing.set(showDetails.pricing);
      },
      error: () => {
        this.loading.set(false);
        this.errorMessage.set('Failed to load hall layout or seat map.');
      },
    });
  }

  private refreshSeatMap(): void {
    this.bookingService.getSeatMap(this.showId(), this.hallId()).subscribe({
      next: (seatMap) => {
        this.seatStatuses.set({ ...(seatMap.seats ?? {}) });
      },
    });
  }

  private subscribeToWsUpdates(showId: string): void {
    this.wsService.connect(showId);
    this.wsSub = this.wsService.seatUpdates$.subscribe((evt: SeatStatusUpdateEvent) => {
      const updated = { ...this.seatStatuses() };
      for (const seat of evt.seats) {
        if (evt.status === 'AVAILABLE') {
          delete updated[seat];
        } else {
          updated[seat] = evt.status;
        }
      }
      this.seatStatuses.set(updated);

      // If another user locked a seat the current user was eyeing, drop it from selection
      const currentHoldId = this.activeHold()?.booking_id;
      if (evt.status !== 'AVAILABLE' && evt.booking_id && evt.booking_id !== currentHoldId) {
        const filtered = this.selectedSeats().filter((s) => !evt.seats.includes(s));
        if (filtered.length !== this.selectedSeats().length) {
          this.selectedSeats.set(filtered);
          this.infoMessage.set(`Seat(s) ${evt.seats.join(', ')} were held by another user.`);
        }
      }
    });
  }
}