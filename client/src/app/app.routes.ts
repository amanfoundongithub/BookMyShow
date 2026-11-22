import { Routes } from '@angular/router';
import { ShowSelectionComponent } from './features/discovery/show-selection.component';
import { SeatMatrixComponent } from './features/seat-map/seat-matrix.component';
import { CheckoutComponent } from './features/checkout/checkout.component';

export const routes: Routes = [
  { path: '', component: ShowSelectionComponent },
  { path: 'shows/:showId/seats', component: SeatMatrixComponent },
  { path: 'checkout', component: CheckoutComponent },
  { path: '**', redirectTo: '' },
];