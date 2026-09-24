import { apiRequest } from './client';
import type { Location, LocationWrite, Product, ProductWrite, Warehouse } from '../types/masterData';
export function getProducts() { return apiRequest<Product[]>('/api/master-data/products'); }
export function getLocations() { return apiRequest<Location[]>('/api/master-data/locations'); }
export function getWarehouses() { return apiRequest<Warehouse[]>('/api/master-data/warehouses'); }
export function createProduct(data: ProductWrite) { return apiRequest<Product>('/api/master-data/products', { method: 'POST', body: JSON.stringify(data) }); }
export function updateProduct(id: number, data: ProductWrite) { return apiRequest<Product>(`/api/master-data/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }); }
export function createLocation(data: LocationWrite) { return apiRequest<Location>('/api/master-data/locations', { method: 'POST', body: JSON.stringify(data) }); }
export function updateLocation(id: number, data: LocationWrite) { return apiRequest<Location>(`/api/master-data/locations/${id}`, { method: 'PUT', body: JSON.stringify(data) }); }
