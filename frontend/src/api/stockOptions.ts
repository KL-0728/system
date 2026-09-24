import { apiRequest } from './client';
import type { BalanceOption, LotOption, StockLocationOption } from '../types/stock';

export function getLotOptions(productId?: number): Promise<LotOption[]> {
  const query = productId === undefined ? '' : `?product_id=${productId}`;
  return apiRequest(`/api/stock-options/lots${query}`);
}

export function getBalanceOptions(options: { lotId?: number; positiveOnly?: boolean } = {}): Promise<BalanceOption[]> {
  const query = new URLSearchParams();
  if (options.lotId !== undefined) query.set('lot_id', String(options.lotId));
  if (options.positiveOnly !== undefined) query.set('positive_only', String(options.positiveOnly));
  const suffix = query.size === 0 ? '' : `?${query.toString()}`;
  return apiRequest(`/api/stock-options/balances${suffix}`);
}

export function getStockLocationOptions(): Promise<StockLocationOption[]> {
  return apiRequest('/api/stock-options/locations');
}
