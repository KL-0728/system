import { apiRequest } from './client';

export interface AdjustmentInput {
  lot_id: number;
  location_id: number;
  kind: 'COUNT' | 'SCRAP';
  observed_qty?: number;
  damaged_qty?: number;
  reason: string;
}

export interface AdjustmentRecord {
  id: number;
  kind: 'COUNT' | 'SCRAP';
  lot_id: number;
  lot_code: string;
  product_name: string;
  unit: string;
  location_id: number;
  location_code: string;
  original_qty: number;
  observed_qty: number | null;
  damaged_qty: number | null;
  reason: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  created_at: string;
}

export function submitAdjustment(payload: AdjustmentInput): Promise<AdjustmentRecord> {
  return apiRequest('/api/adjustments', {
    method: 'POST', body: JSON.stringify(payload), signal: AbortSignal.timeout(15000),
  });
}

export function getMyAdjustments(): Promise<AdjustmentRecord[]> {
  return apiRequest('/api/adjustments/mine', { signal: AbortSignal.timeout(10000) });
}
