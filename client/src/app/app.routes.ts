import { Routes } from '@angular/router';
import { ShowSelectionComponent } from './features/discovery/show-selection.component';
import { SeatMatrixComponent } from './features/seat-map/seat-matrix.component';
import { CheckoutComponent } from './features/checkout/checkout.component';
import { LoginComponent } from './features/auth/login.component';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: '', component: ShowSelectionComponent },
  { path: 'login', component: LoginComponent },
  { path: 'shows/:showId/seats', component: SeatMatrixComponent },
  { path: 'checkout', component: CheckoutComponent, canActivate: [authGuard] },
  { path: '**', redirectTo: '' },
];