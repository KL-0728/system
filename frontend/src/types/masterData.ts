export interface Product { id: number; name: string; unit: string; min_qty: number; target_qty: number; is_active: boolean; }
export interface Location { id: number; code: string; is_active: boolean; warehouse_id: number; warehouse_code: string; warehouse_name: string; }
export interface Warehouse { id: number; code: string; name: string; }
export type ProductWrite = Omit<Product, 'id'>;
export interface LocationWrite { warehouse_id: number; code: string; is_active: boolean; }
