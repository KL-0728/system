import { useEffect, useState, type FormEvent } from 'react';
import { getLocations, getProducts } from '../api/masterData';
import { getInventoryMovements, searchInventory, type InventoryFilters } from '../api/inventorySearch';
import type { Location, Product } from '../types/masterData';
import type { InventoryBalance, InventoryMovement } from '../types/inventory';

const movementNames: Record<string, string> = {
  RECEIPT: '入庫', OUTBOUND: '出庫', TRANSFER: '移位',
  COUNT_GAIN: '盤盈', COUNT_LOSS: '盤虧', SCRAP: '報廢',
};

function InventoryLot({ positions }: { positions: InventoryBalance[] }) {
  const lot = positions[0];
  const [expanded, setExpanded] = useState(false);
  const [movements, setMovements] = useState<InventoryMovement[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function toggleHistory() {
    if (expanded) { setExpanded(false); return; }
    setExpanded(true);
    if (movements !== null) return;
    setLoading(true);
    try {
      setMovements(await getInventoryMovements(lot.lot_id));
      setError('');
    } catch {
      setError('無法讀取異動歷史，請再試一次。');
    } finally {
      setLoading(false);
    }
  }

  return <article className="inventory-lot">
    <h3>{lot.product_name}／{lot.lot_code}</h3>
    <p>入庫日 {lot.received_date} · 庫齡 {lot.age_days} 天 · 入庫操作者 {lot.received_by}</p>
    <strong>全批合計 {lot.total_qty} {lot.unit}</strong>
    <div className="inventory-positions">{positions.map((position) =>
      <div key={position.location_id} className="inventory-position">
        <span>{position.warehouse_name}／{position.location_code}</span>
        <strong>{position.qty} {lot.unit}</strong>
      </div>)}</div>
    <button type="button" className="secondary" aria-expanded={expanded} onClick={() => void toggleHistory()}>
      {expanded ? '收起異動歷史' : '查看異動歷史'}
    </button>
    {expanded && <div className="inventory-history">
      {loading && <p role="status">正在讀取異動歷史…</p>}
      {error && <p role="alert" className="error">{error}</p>}
      {movements?.length === 0 && <p>這批目前沒有異動紀錄。</p>}
      {movements?.map((movement) => <div className="inventory-movement" key={movement.movement_id}>
        <strong>#{movement.movement_id} {movementNames[movement.kind] ?? movement.kind} {movement.qty} {lot.unit}</strong>
        <span>{movement.from_location_code ?? '庫外'} → {movement.to_location_code ?? '庫外'}</span>
        <span>{new Date(movement.created_at).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false })}（臺灣時間）／{movement.actor_name}</span>
        {movement.note && <span>備註：{movement.note}</span>}
      </div>)}
    </div>}
  </article>;
}

export default function InventoryPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [rows, setRows] = useState<InventoryBalance[]>([]);
  const [productId, setProductId] = useState('');
  const [lotCode, setLotCode] = useState('');
  const [locationId, setLocationId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  const [searched, setSearched] = useState(false);
  const groups = new Map<number, InventoryBalance[]>();
  for (const row of rows) groups.set(row.lot_id, [...(groups.get(row.lot_id) ?? []), row]);

  async function runSearch(filters: InventoryFilters) {
    setLoading(true);
    try {
      setRows(await searchInventory(filters));
      setVersion((value) => value + 1);
      setSearched(true);
      setError('');
    } catch {
      setError('庫存查詢失敗，請確認連線後重試。');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    Promise.all([getProducts(), getLocations(), searchInventory({})]).then(([nextProducts, nextLocations, nextRows]) => {
      if (active) { setProducts(nextProducts); setLocations(nextLocations); setRows(nextRows); setSearched(true); setError(''); }
    }).catch(() => { if (active) setError('庫存資料載入失敗，請重新進入頁面。'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  function filters(): InventoryFilters {
    return {
      productId: productId ? Number(productId) : undefined,
      lotCode: lotCode.trim() || undefined,
      locationId: locationId ? Number(locationId) : undefined,
    };
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runSearch(filters());
  }

  return <section className="card inventory-panel" aria-labelledby="inventory-title">
    <h2 id="inventory-title">庫存查詢</h2>
    <p className="hint">依品項、批次碼或儲位查詢。位置列顯示符合條件的儲位；「全批合計」包含該批在所有儲位的餘量，歸零位置仍會顯示。</p>
    {error && <p role="alert" className="error">{error}</p>}
    <form onSubmit={handleSubmit}>
      <fieldset disabled={loading}>
        <label>品項<select value={productId} onChange={(event) => setProductId(event.target.value)}>
          <option value="">全部品項</option>
          {products.map((product) => <option key={product.id} value={product.id}>{product.name}{product.is_active ? '' : '（已停用）'}</option>)}
        </select></label>
        <label>批次碼<input value={lotCode} maxLength={100} placeholder="可輸入部分批次碼" onChange={(event) => setLotCode(event.target.value)} /></label>
        <label>儲位<select value={locationId} onChange={(event) => setLocationId(event.target.value)}>
          <option value="">全部儲位</option>
          {locations.map((location) => <option key={location.id} value={location.id}>{location.code}（{location.warehouse_name}）{location.is_active ? '' : '（已停用）'}</option>)}
        </select></label>
        <div className="inventory-actions">
          <button type="submit">查詢／更新</button>
          <button type="button" className="secondary" onClick={() => {
            setProductId(''); setLotCode(''); setLocationId(''); void runSearch({});
          }}>清除條件</button>
        </div>
      </fieldset>
    </form>
    {loading && <p role="status">正在讀取資料庫庫存…</p>}
    {!loading && searched && rows.length === 0 && !error && <p role="status">沒有符合條件的庫存。</p>}
    <div className="inventory-results">{[...groups.values()].map((positions) =>
      <InventoryLot key={positions[0].lot_id + ':' + version} positions={positions} />)}</div>
  </section>;
}
