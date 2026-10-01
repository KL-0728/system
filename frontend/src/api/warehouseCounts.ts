import { apiRequest } from './client';

export interface CountItem {
  id: number; location_id: number; location_code: string;
  lot_id: number | null; lot_code: string | null; product_name: string | null; unit: string | null;
  original_qty: number; observed_qty: number | null; adjustment_request_id: number | null;
  adjustment_status: 'PENDING' | 'APPROVED' | 'REJECTED' | null;
  checked_at: string | null; note: string;
}

export interface CountSession {
  id: number; warehouse_id: number; warehouse_code: string; warehouse_name: string;
  created_by: number; status: 'OPEN' | 'COMPLETE' | 'CANCELLED';
  started_at: string; completed_at: string | null; items: CountItem[];
}

export const listWarehouseCounts = (): Promise<CountSession[]> => apiRequest('/api/warehouse-counts', {
  signal: AbortSignal.timeout(10000),
});
export const startWarehouseCount = (warehouseId: number): Promise<CountSession> => apiRequest('/api/warehouse-counts', {
  method: 'POST', body: JSON.stringify({ warehouse_id: warehouseId }), signal: AbortSignal.timeout(15000),
});
export const checkWarehouseCountItem = (countId: number, itemId: number, observedQty: number, note: string): Promise<CountSession> =>
  apiRequest(`/api/warehouse-counts/${countId}/items/${itemId}`, {
    method: 'POST', body: JSON.stringify({ observed_qty: observedQty, note }), signal: AbortSignal.timeout(15000),
  });
export const checkAllWarehouseCountItems = (countId: number, items: { item_id: number; observed_qty: number; note: string }[]): Promise<CountSession> =>
  apiRequest(`/api/warehouse-counts/${countId}/check-all`, {
    method: 'POST', body: JSON.stringify({ items }), signal: AbortSignal.timeout(30000),
  });
export const reopenWarehouseCountItem = (countId: number, itemId: number): Promise<CountSession> =>
  apiRequest(`/api/warehouse-counts/${countId}/items/${itemId}/reopen`, {
    method: 'POST', signal: AbortSignal.timeout(15000),
  });
export const completeWarehouseCount = (countId: number): Promise<CountSession> => apiRequest(`/api/warehouse-counts/${countId}/complete`, {
  method: 'POST', signal: AbortSignal.timeout(15000),
});
export const cancelWarehouseCount = (countId: number): Promise<CountSession> => apiRequest(`/api/warehouse-counts/${countId}/cancel`, {
  method: 'POST', signal: AbortSignal.timeout(15000),
});
