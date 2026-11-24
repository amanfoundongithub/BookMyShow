import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { 
  CityCreateRequest, 
  CityCreateResponse, 
  CityListItem 
} from '../../models/city.models';

@Injectable({ 
    providedIn: 'root' 
})
export class CityService {

  private readonly http = inject(HttpClient);
  private readonly baseUrl = (environment as { apiGatewayUrl?: string }).apiGatewayUrl ?? '';

  getAllCities() : Observable<CityListItem[]> {
    return this.http.get<CityListItem[]>(`${this.baseUrl}/api/v1/cities`)
  }

  createCity(payload : CityCreateRequest) : Observable<CityCreateResponse> {
    return this.http.post<CityCreateResponse>(`${this.baseUrl}/api/v1/cities`, payload);
  }

  

}