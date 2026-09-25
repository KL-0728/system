import { apiRequest } from './client';

export interface InboundInput { product_id: number; location_id: number; qty: number; received_date: string; note: string }
export interface InboundResult {
  lot_id: number; lot_code: string; product_id: number; location_id: number;
  received_date: string; qty: number; movement_id: number;
}
export interface InboundRecord {
  movement_id: number; lot_id: number; lot_code: string; product_name: string; unit: string;
  received_date: string; location_id: number; location_code: string; qty: number;
  actor_name: string; note: string; created_at: string;
}

export function submitInbound(payload: InboundInput): Promise<InboundResult> {
  return apiRequest('/api/inventory/inbound', {
    method: 'POST', body: JSON.stringify(payload), signal: AbortSignal.timeout(15000),
  });
}

export function getInboundRecords(): Promise<InboundRecord[]> {
  return apiRequest('/api/inventory/inbound', { signal: AbortSignal.timeout(10000) });
}
