export interface City {
  id: string;
  name: string;
  state: string;
  country: string;
}

export interface Movie {
  id: string;
  title: string;
  duration_minutes: number;
  rating: string;
  languages: string[];
  formats: string[];
}

export interface Show {
  id: string;
  movie_id: string;
  cinema_id: string;
  hall_id: string;
  start_time: string;
  end_time: string;
  language: string;
  format: string;
  pricing: Record<string, number>;
}

export type SeatType = 'STANDARD' | 'PREMIUM' | 'RECLINER' | 'AISLE' | 'WHEELCHAIR';
export type SeatLockStatus = 'AVAILABLE' | 'HELD' | 'CONFIRMED';
export type BookingStatus = 'HELD' | 'CONFIRMED' | 'EXPIRED' | 'CANCELLED';
export type TransactionStatus = 'PENDING' | 'SUCCESS' | 'FAILED';
export type UserRole = 'USER' | 'CINEMA' | 'ADMIN';

export interface SeatSlot {
  seat_number?: number | null;
  type: SeatType;
  tier?: string;
}

export interface HallRow {
  row_label: string;
  tier?: string;
  seats: SeatSlot[];
}

export interface HallLayoutResponse {
  hall_id: string;
  cinema_id: string;
  name: string;
  screen_format?: string;
  total_seats: number;
  layout: {
    rows: HallRow[];
  };
  created_at?: string;
}

export interface CinemaSummary {
  cinema_id: string;
  name: string;
  city_id: string;
  state?: string | null;
  address: string;
  amenities?: string[];
  is_active?: boolean;
  created_at?: string;
}

export interface CreateHallPayload {
  cinema_id: string;
  name: string;
  screen_format: string;
  layout: {
    rows: HallRow[];
  };
}

export interface UpdateHallLayoutPayload {
  name?: string;
  screen_format?: string;
  layout: {
    rows: HallRow[];
  };
}

export interface HallResponse {
  hall_id: string;
  cinema_id: string;
  name: string;
  screen_format: string;
  total_seats: number;
  layout: {
    rows: HallRow[];
  };
  created_at: string;
}

export interface SeatMapResponse {
  show_id: string;
  hall_id: string;
  seats: Record<string, SeatLockStatus>;
}

export interface HoldSeatsRequest {
  show_id: string;
  user_id: string;
  seats: string[];
  tier: string;
}

export interface HoldSeatsResponse {
  booking_id: string;
  show_id: string;
  user_id: string;
  seats: string[];
  tier: string;
  total_amount: number;
  currency: string;
  status: BookingStatus;
  hold_expires_at: string;
}

export interface ReleaseBookingRequest {
  booking_id: string;
  user_id: string;
}

export interface ReleaseBookingResponse {
  booking_id: string;
  status: BookingStatus;
  released_seats: string[];
}

export interface SeatStatusUpdateEvent {
  type: 'SEAT_STATUS_UPDATE';
  show_id: string;
  seats: string[];
  status: SeatLockStatus | 'AVAILABLE';
  booking_id: string | null;
}

export interface CreatePaymentIntentRequest {
  booking_id: string;
  user_id: string;
  amount: number;
  currency: string;
  payment_gateway: string;
}

export interface PaymentIntentResponse {
  payment_id: string;
  booking_id: string;
  idempotency_key: string;
  amount: number;
  currency: string;
  status: TransactionStatus;
  payment_gateway: string;
  gateway_reference: string;
  created_at: string;
}

export interface PaymentWebhookRequest {
  payment_id: string;
  booking_id: string;
  gateway_reference: string;
  event_status: 'SUCCESS' | 'FAILED';
  failure_reason?: string;
}

export interface PaymentWebhookResponse {
  payment_id: string;
  booking_id: string;
  status: TransactionStatus;
  published_routing_key: string;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface UserProfile {
  user_id: string;
  name: string;
  email: string;
  role: UserRole;
  cinema_ids?: string[];
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface BookingRecord {
  booking_id: string;
  show_id: string;
  hall_id?: string;
  user_id: string;
  seats: string[];
  tier?: string;
  total_amount: number;
  currency: string;
  status: BookingStatus;
  hold_expires_at?: string | null;
  created_at?: string;
}

export interface CreateCinemaPayload {
  name: string;
  city_id: string;
  state?: string | null;
  address: string;
  amenities?: string[];
  is_active?: boolean;
}