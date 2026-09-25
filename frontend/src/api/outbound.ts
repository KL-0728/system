import { apiRequest } from './client';

export interface OutboundInput { lot_id: number; location_id: number; qty: number; note: string }
export interface OutboundResult { lot_id: number; location_id: number; qty: number; movement_id: number }
export interface OutboundRecord extends OutboundInput {
  movement_id: number; lot_code: string; product_name: string; unit: string;
  location_code: string; actor_name: string; created_at: string;
}

export function submitOutbound(payload: OutboundInput): Promise<OutboundResult> {
  return apiRequest('/api/outbound', {
    method: 'POST', body: JSON.stringify(payload), signal: AbortSignal.timeout(15000),
  });
}

export function getOutboundRecords(): Promise<OutboundRecord[]> {
  return apiRequest('/api/outbound', { signal: AbortSignal.timeout(10000) });
}
