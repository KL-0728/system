import { apiRequest } from './client';
import type { InventoryBalance, InventoryMovement } from '../types/inventory';

export interface InventoryFilters {
  productId?: number;
  lotCode?: string;
  locationId?: number;
}

export function searchInventory(filters: InventoryFilters): Promise<InventoryBalance[]> {
  const params = new URLSearchParams();
  if (filters.productId !== undefined) params.set('product_id', String(filters.productId));
  if (filters.lotCode) params.set('lot_code', filters.lotCode);
  if (filters.locationId !== undefined) params.set('location_id', String(filters.locationId));
  const query = params.toString();
  return apiRequest('/api/inventory/stock' + (query ? '?' + query : ''));
}

export function getInventoryMovements(lotId: number): Promise<InventoryMovement[]> {
  return apiRequest('/api/inventory/movements?lot_id=' + encodeURIComponent(lotId));
}
