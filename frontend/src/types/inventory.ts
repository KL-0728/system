export interface InventoryBalance {
  lot_id: number;
  lot_code: string;
  product_id: number;
  product_name: string;
  unit: string;
  received_date: string;
  age_days: number;
  received_by: string;
  location_id: number;
  location_code: string;
  warehouse_code: string;
  warehouse_name: string;
  qty: number;
  total_qty: number;
}

export interface InventoryMovement {
  movement_id: number;
  lot_id: number;
  kind: string;
  from_location_code: string | null;
  to_location_code: string | null;
  qty: number;
  actor_name: string;
  note: string;
  adjustment_request_id: number | null;
  created_at: string;
}
