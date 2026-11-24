import {
  Component,
  OnDestroy,
  computed,
  effect,
  input,
  output,
  signal,
} from '@angular/core';

@Component({
  selector: 'app-hold-countdown',
  standalone: true,
  templateUrl: './hold-countdown.component.html',
  styleUrl: './hold-countdown.component.css',
})
export class HoldCountdownComponent implements OnDestroy {
  readonly holdExpiresAt = input<string | null>(null);
  readonly expired = output<void>();

  readonly remainingSeconds = signal<number>(0);
  readonly isUrgent = computed(() => {
    const secs = this.remainingSeconds();
    return secs > 0 && secs <= 60;
  });

  readonly formattedTime = computed(() => {
    const total = Math.max(0, this.remainingSeconds());
    const mins = Math.floor(total / 60)
      .toString()
      .padStart(2, '0');
    const secs = (total % 60).toString().padStart(2, '0');
    return `${mins}:${secs}`;
  });

  private timerId: ReturnType<typeof setInterval> | null = null;
  private hasEmittedExpired = false;

  constructor() {
    effect(() => {
      const targetIso = this.holdExpiresAt();
      this.stopTimer();
      this.hasEmittedExpired = false;

      if (!targetIso) {
        this.remainingSeconds.set(0);
        return;
      }

      const targetMs = Date.parse(targetIso);
      if (Number.isNaN(targetMs)) {
        this.remainingSeconds.set(0);
        return;
      }

      this.updateRemaining(targetMs);
      this.timerId = setInterval(() => {
        this.updateRemaining(targetMs);
      }, 1000);
    });
  }

  ngOnDestroy(): void {
    this.stopTimer();
  }

  private updateRemaining(targetMs: number): void {
    const diffSecs = Math.max(0, Math.floor((targetMs - Date.now()) / 1000));
    this.remainingSeconds.set(diffSecs);

    if (diffSecs === 0 && !this.hasEmittedExpired) {
      this.hasEmittedExpired = true;
      this.stopTimer();
      this.expired.emit();
    }
  }

  private stopTimer(): void {
    if (this.timerId !== null) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
  }
}