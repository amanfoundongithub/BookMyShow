import { Routes } from '@angular/router';
import { ShowSelectionComponent } from './features/discovery/show-selection.component';
import { SeatMatrixComponent } from './features/seat-map/seat-matrix.component';
import { CheckoutComponent } from './features/checkout/checkout.component';
import { LoginComponent } from './features/auth/login.component';
import { BookingsComponent } from './features/bookings/bookings.component';
import { authGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';

export const routes: Routes = [
  { path: '', component: ShowSelectionComponent },
  { path: 'login', component: LoginComponent },
  { path: 'shows/:showId/seats', component: SeatMatrixComponent },
  { path: 'checkout', component: CheckoutComponent, canActivate: [authGuard] },
  { path: 'bookings', component: BookingsComponent, canActivate: [authGuard] },
  {
    path: 'management',
    canActivate: [authGuard, roleGuard],
    data: { roles: ['ADMIN', 'CINEMA'] },
    children: [
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'cinemas/new',
      },
      {
        path: 'cinemas/new',
        loadComponent: () =>
          import('./features/management/cinema-management/cinema-create.component').then(
            (m) => m.CinemaCreateComponent
          ),
      },
      {
        path: 'cities',
        canActivate: [roleGuard],
        data: { roles: ['ADMIN'] },
        loadComponent: () =>
          import('./features/management/city-management/city-management.component').then(
            (m) => m.CityManagementComponent
          ),
      },
      {
        path: 'movies',
        canActivate: [roleGuard],
        data: { roles: ['ADMIN'] },
        loadComponent: () =>
          import('./features/management/movie-management/movie-management.component').then(
            (m) => m.MovieManagementComponent
          ),
      },
      {
        path: 'halls',
        loadComponent: () =>
          import('./features/management/hall-management/hall-layout-builder.component').then(
            (m) => m.HallLayoutBuilderComponent
          ),
      },
      {
        path: 'shows',
        loadComponent: () =>
          import('./features/management/show-management/show-scheduler.component').then(
            (m) => m.ShowSchedulerComponent
          ),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];