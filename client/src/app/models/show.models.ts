export interface ShowSearchResponseItem {
    id: string;
    movie_id: string;
    cinema: CinemaResponseItem;
    hall_id: string;
    start_time: string;
    end_time: string;
    language: string;
    format: string;
    pricing: Record<string, number>;
};

interface CinemaResponseItem {
    cinema_id: string,
    name: string,
    city_id: string,
    state: string,
    address: string,
    amenities: string[],
    is_active: boolean,
    created_at: string
}