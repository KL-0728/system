import { apiRequest } from './client';

export interface ReportSummary {
  active_product_count: number;
  in_stock_product_count: number;
  low_stock_product_count: number;
  pending_adjustment_count: number;
  shortage_demand_count: number;
}

export interface ProductReport {
  product_id: number;
  product_name: string;
  unit: string;
  current_qty: number;
  min_qty: number;
  target_qty: number;
  is_low: boolean;
  replenishment_gap: number;
  outbound_30d: number;
  shortage_demand_qty: number;
  count_gain_qty: number;
  count_loss_qty: number;
  scrap_qty: number;
}

export interface AgedLotReport {
  lot_id: number;
  lot_code: string;
  product_name: string;
  unit: string;
  received_date: string;
  age_days: number;
  total_qty: number;
}

export interface AdjustmentEventReport {
  movement_id: number;
  adjustment_request_id: number;
  kind: 'COUNT_GAIN' | 'COUNT_LOSS' | 'SCRAP';
  lot_code: string;
  product_name: string;
  unit: string;
  location_code: string;
  qty: number;
  actor_name: string;
  reason: string;
  created_at: string;
}

export interface DecisionReport {
  as_of_utc: string;
  summary: ReportSummary;
  products: ProductReport[];
  aged_lots: AgedLotReport[];
  adjustments: AdjustmentEventReport[];
  shortage_demands: Array<{
    id: number; product_id: number; product_name: string; unit: string;
    qty: number; note: string; actor_name: string; created_at: string;
  }>;
}

export function getDecisionReport(): Promise<DecisionReport> {
  return apiRequest('/api/reports', { signal: AbortSignal.timeout(10000) });
}
