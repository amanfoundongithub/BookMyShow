export interface MovieRecord {
  id: string;
  title: string;
  duration_minutes: number;
  rating: string;
  languages: string[];
  formats: string[];
  synopsis: string | null;
  city_ids: string[];
  release_date: string | null;
  poster_url: string | null;
  is_active: boolean;
}

export interface MovieCreateRequest {
  id?: string;
  title: string;
  duration_minutes: number;
  rating?: string;
  languages?: string[];
  formats?: string[];
  synopsis?: string | null;
  city_ids?: string[];
  release_date?: string | null;
  poster_url?: string | null;
  is_active?: boolean;
}

export type MovieUpdateRequest = Partial<Omit<MovieCreateRequest, 'id'>>;

export interface MovieOptions {
  languages: string[];
  formats: string[];
  ratings: string[];
}