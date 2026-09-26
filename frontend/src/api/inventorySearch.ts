import { apiRequest, UNAUTHORIZED_EVENT, REQUEST_TIMEOUT_MS } from './client';
import type { InventoryBalance, InventoryMovement } from '../types/inventory';

export interface InventoryFilters {
  productId?: number;
  lotCode?: string;
  locationId?: number;
}

function filterQuery(filters: InventoryFilters): string {
  const params = new URLSearchParams();
  if (filters.productId !== undefined) params.set('product_id', String(filters.productId));
  if (filters.lotCode) params.set('lot_code', filters.lotCode);
  if (filters.locationId !== undefined) params.set('location_id', String(filters.locationId));
  const query = params.toString();
  return query ? '?' + query : '';
}

export function searchInventory(filters: InventoryFilters): Promise<InventoryBalance[]> {
  return apiRequest('/api/inventory/stock' + filterQuery(filters));
}

export async function downloadInventoryCsv(filters: InventoryFilters): Promise<void> {
  const response = await fetch('/api/inventory/stock.csv' + filterQuery(filters), {
    credentials: 'same-origin', signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
  if (response.status === 401) window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  if (!response.ok) throw new Error('CSV 匯出失敗，請確認登入狀態與網路連線。');
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a');
  link.href = url;
  link.download = `inventory-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function setLotExpiry(lotId: number, expiresOn: string | null): Promise<{ lot_id: number; lot_code: string; expires_on: string | null }> {
  return apiRequest(`/api/inventory/lots/${lotId}/expiry`, {
    method: 'PUT', body: JSON.stringify({ expires_on: expiresOn }), signal: AbortSignal.timeout(10000),
  });
}

export function getInventoryMovements(lotId: number): Promise<InventoryMovement[]> {
  return apiRequest('/api/inventory/movements?lot_id=' + encodeURIComponent(lotId));
}
