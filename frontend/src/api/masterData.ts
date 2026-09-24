import { apiRequest } from './client';
import type { Location, Product } from '../types/masterData';
export function getProducts() { return apiRequest<Product[]>('/api/master-data/products'); }
export function getLocations() { return apiRequest<Location[]>('/api/master-data/locations'); }
