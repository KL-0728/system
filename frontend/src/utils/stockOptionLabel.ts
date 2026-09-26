import type { BalanceOption } from '../types/stock';

// Keep native iOS select labels short: WebKit counts long option text in page scrollWidth.
export function stockOptionLabel(row: BalanceOption): string {
  const name = Array.from(row.product_name);
  const shortName = name.length > 4 ? `${name.slice(0, 4).join('')}…` : row.product_name;
  const state = row.has_pending ? '／待審' : row.qty === 0 ? '／無餘量' : '';
  return `${shortName}／${row.location_code}／#${row.lot_id}／${row.qty}${state}`;
}
