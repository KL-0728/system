export interface Product { id: number; name: string; unit: string; min_qty: number; target_qty: number; is_active: boolean; }
export interface Location { id: number; code: string; is_active: boolean; warehouse_id: number; warehouse_code: string; warehouse_name: string; }
