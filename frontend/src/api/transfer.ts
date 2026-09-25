import { apiRequest } from './client';

export interface TransferInput {
  lot_id: number; from_location_id: number; to_location_id: number; qty: number;
}
export interface TransferResult {
  lot_id: number; from_location_id: number; to_location_id: number;
  from_qty: number; to_qty: number; movement_id: number;
}
export interface TransferRecord extends TransferInput {
  movement_id: number; lot_code: string; product_name: string; unit: string;
  from_location_code: string; to_location_code: string; actor_name: string; created_at: string;
}

export function submitTransfer(payload: TransferInput): Promise<TransferResult> {
  return apiRequest('/api/outbound/transfers', {
    method: 'POST', body: JSON.stringify(payload), signal: AbortSignal.timeout(15000),
  });
}

export function getTransferRecords(): Promise<TransferRecord[]> {
  return apiRequest('/api/outbound/transfers', { signal: AbortSignal.timeout(10000) });
}
