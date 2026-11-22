import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { BookingService } from '../../core/services/booking.service';
import { BookingRecord } from '../../models/bms.models';

@Component({
  selector: 'app-bookings',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './bookings.component.html',
  styleUrl: './bookings.component.css',
})
export class BookingsComponent implements OnInit {
  private readonly bookingService = inject(BookingService);
  readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  readonly bookings = signal<BookingRecord[]>([]);
  readonly loading = signal<boolean>(false);
  readonly busyId = signal<string | null>(null);
  readonly errorMessage = signal<string | null>(null);
  readonly infoMessage = signal<string | null>(null);

  ngOnInit(): void {
    this.loadBookings();
  }

  loadBookings(): void {
    this.loading.set(true);
    this.errorMessage.set(null);

    this.bookingService.getUserBookings(this.authService.userId()).subscribe({
      next: (items) => {
        this.bookings.set(items ?? []);
        this.loading.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.loading.set(false);
        this.errorMessage.set(err.error?.detail ?? 'Failed to load bookings.');
      },
    });
  }

  goToCheckout(bk: BookingRecord): void {
    this.router.navigate(['/checkout'], {
      state: {
        hold: {
          booking_id: bk.booking_id,
          show_id: bk.show_id,
          user_id: bk.user_id,
          seats: bk.seats,
          tier: bk.tier ?? 'STANDARD',
          total_amount: bk.total_amount,
          currency: bk.currency || 'INR',
          hold_expires_at: bk.hold_expires_at ?? '',
        },
      },
    });
  }

  releaseHold(bk: BookingRecord): void {
    if (this.busyId()) return;
    this.busyId.set(bk.booking_id);
    this.errorMessage.set(null);
    this.infoMessage.set(null);

    this.bookingService
      .releaseBooking({
        booking_id: bk.booking_id,
        user_id: this.authService.userId(),
      })
      .subscribe({
        next: () => {
          this.busyId.set(null);
          this.infoMessage.set(`Hold ${bk.booking_id} released.`);
          this.loadBookings();
        },
        error: (err: HttpErrorResponse) => {
          this.busyId.set(null);
          this.errorMessage.set(err.error?.detail ?? 'Failed to release hold.');
        },
      });
  }
}