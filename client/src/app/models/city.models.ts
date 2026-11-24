// Item for city list 
export interface CityListItem {
    id : string,
    name : string,
    state : string,
    country : string
};

// City create request & response

export interface CityCreateRequest {
    id : string,
    name : string,
    state : string,
    country : string
};

export interface CityCreateResponse {
    id : string,
    name : string,
    state : string,
    country : string
}

// City update request & response