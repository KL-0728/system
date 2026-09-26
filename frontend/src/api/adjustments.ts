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
  reviewer_name: string | null;
  review_note: string | null;
  reviewed_at: string | null;
}

export interface AdjustmentDetail extends AdjustmentRecord {
  requested_by: number;
  requester_name: string;
  current_qty: number;
  difference: number;
  reviewed_by: number | null;
  movement_id: number | null;
}

export interface AdjustmentReviewResult {
  request_id: number;
  status: 'APPROVED' | 'REJECTED';
  original_qty: number;
  new_qty: number;
  delta: number;
  movement_id: number | null;
  reviewed_by: number;
  review_note: string;
  reviewed_at: string;
}

export function submitAdjustment(payload: AdjustmentInput): Promise<AdjustmentRecord> {
  return apiRequest('/api/adjustments', {
    method: 'POST', body: JSON.stringify(payload), signal: AbortSignal.timeout(15000),
  });
}

export function getMyAdjustments(): Promise<AdjustmentRecord[]> {
  return apiRequest('/api/adjustments/mine', { signal: AbortSignal.timeout(10000) });
}

export function getPendingAdjustments(): Promise<AdjustmentDetail[]> {
  return apiRequest('/api/adjustments/pending', { signal: AbortSignal.timeout(10000) });
}

export function getReviewedAdjustments(): Promise<AdjustmentDetail[]> {
  return apiRequest('/api/adjustments/reviewed', { signal: AbortSignal.timeout(10000) });
}

export function getAdjustmentDetail(id: number): Promise<AdjustmentDetail> {
  return apiRequest(`/api/adjustments/${id}`, { signal: AbortSignal.timeout(10000) });
}

export function reviewAdjustment(id: number, action: 'APPROVE' | 'REJECT', reviewNote: string): Promise<AdjustmentReviewResult> {
  return apiRequest(`/api/adjustments/${id}/review`, {
    method: 'POST', body: JSON.stringify({ action, review_note: reviewNote }), signal: AbortSignal.timeout(15000),
  });
}
