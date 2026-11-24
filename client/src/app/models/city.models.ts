export interface CityListItem {
    id : string,
    name : string,
    state : string,
    country : string
};

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
};

export interface CityUpdateRequest {
    name? : string, 
    state? : string,
    country? : string
};

export interface CityUpdateResponse {
    id : string,
    name : string,
    state : string,
    country : string
}