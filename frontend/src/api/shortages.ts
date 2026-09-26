import { apiRequest } from './client';

export interface ShortageDemand {
  id: number;
  product_id: number;
  product_name: string;
  unit: string;
  qty: number;
  note: string;
  actor_name: string;
  created_at: string;
}

export function createShortageDemand(payload: { product_id: number; qty: number; note: string }): Promise<ShortageDemand> {
  return apiRequest('/api/shortages', { method: 'POST', body: JSON.stringify(payload), signal: AbortSignal.timeout(15000) });
}

export function getShortageDemands(): Promise<ShortageDemand[]> {
  return apiRequest('/api/shortages', { signal: AbortSignal.timeout(10000) });
}
