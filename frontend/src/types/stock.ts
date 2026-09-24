export interface LotOption {
  lot_id: number;
  lot_code: string;
  product_id: number;
  product_name: string;
  unit: string;
  received_date: string;
  total_qty: number;
}

export interface BalanceOption {
  lot_id: number;
  lot_code: string;
  product_id: number;
  product_name: string;
  unit: string;
  received_date: string;
  location_id: number;
  location_code: string;
  warehouse_code: string;
  qty: number;
  has_pending: boolean;
}

export interface StockLocationOption {
  location_id: number;
  location_code: string;
  warehouse_code: string;
  warehouse_name: string;
}
