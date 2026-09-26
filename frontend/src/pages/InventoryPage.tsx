import { useEffect, useRef, useState, type FormEvent } from 'react';
import { getLocations, getProducts } from '../api/masterData';
import { downloadInventoryCsv, getInventoryMovements, searchInventory, setLotExpiry, type InventoryFilters } from '../api/inventorySearch';
import type { Location, Product } from '../types/masterData';
import type { InventoryBalance, InventoryMovement } from '../types/inventory';
import { productOptionLabel } from '../utils/productOptionLabel';

const movementNames: Record<string, string> = {
  RECEIPT: '入庫', OUTBOUND: '出庫', TRANSFER: '移位',
  COUNT_GAIN: '盤盈', COUNT_LOSS: '盤虧', SCRAP: '報廢',
};

function InventoryLot({ positions, role, onExpirySaved }: {
  positions: InventoryBalance[];
  role: 'ADMIN' | 'WORKER';
  onExpirySaved: () => Promise<void>;
}) {
  const lot = positions[0];
  const [expanded, setExpanded] = useState(false);
  const [movements, setMovements] = useState<InventoryMovement[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expiryDate, setExpiryDate] = useState(lot.expires_on ?? '');
  const [savingExpiry, setSavingExpiry] = useState(false);
  const [expiryError, setExpiryError] = useState('');

  async function saveExpiry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSavingExpiry(true); setExpiryError('');
    try {
      await setLotExpiry(lot.lot_id, expiryDate || null);
      await onExpirySaved();
    } catch { setExpiryError('效期儲存或更新失敗，請重新查詢後核對。'); }
    finally { setSavingExpiry(false); }
  }

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
    <p className={lot.expiry_status === '已到期' || lot.expiry_status === '即將到期' ? 'expiry-alert' : 'hint'}>
      到期日：{lot.expires_on ?? '未提供'}{lot.expires_on && `（${lot.expiry_status}）`}
    </p>
    <strong>全批合計 {lot.total_qty} {lot.unit}</strong>
    <div className="inventory-positions">{positions.map((position) =>
      <div key={position.location_id} className="inventory-position">
        <span>{position.warehouse_name}／{position.location_code}</span>
        <strong>{position.qty} {lot.unit}</strong>
      </div>)}</div>
    {role === 'ADMIN' && <details className="expiry-editor"><summary>設定這批的到期日</summary>
      <p className="hint">依可信的人工資料填寫；留空後儲存可清除，不推算品質。</p>
      <form onSubmit={saveExpiry}><label>到期日<span className="date-input-frame"><input type="date" value={expiryDate} onChange={(event) => setExpiryDate(event.target.value)} /></span></label>
        <button type="submit" disabled={savingExpiry}>{savingExpiry ? '儲存中…' : '儲存效期'}</button>
      </form>
      {expiryError && <p role="alert" className="error">{expiryError}</p>}
    </details>}
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

export default function InventoryPage({ refreshKey = 0, role }: { refreshKey?: number; role: 'ADMIN' | 'WORKER' }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [rows, setRows] = useState<InventoryBalance[]>([]);
  const [productId, setProductId] = useState('');
  const [lotCode, setLotCode] = useState('');
  const [locationId, setLocationId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [appliedFilters, setAppliedFilters] = useState<InventoryFilters>({});
  const latestSearch = useRef(0);
  const [searched, setSearched] = useState(false);
  const [exporting, setExporting] = useState(false);
  const groups = new Map<number, InventoryBalance[]>();
  for (const row of rows) groups.set(row.lot_id, [...(groups.get(row.lot_id) ?? []), row]);

  async function runSearch(filters: InventoryFilters) {
    const searchId = ++latestSearch.current;
    setLoading(true);
    try {
      const result = await searchInventory(filters);
      if (searchId !== latestSearch.current) return;
      setRows(result);
      setAppliedFilters(filters);
      setSearched(true);
      setError('');
    } catch {
      if (searchId === latestSearch.current) setError('庫存查詢失敗，請確認連線後重試。');
    } finally {
      if (searchId === latestSearch.current) setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    Promise.all([getProducts(), getLocations(), searchInventory({})]).then(([nextProducts, nextLocations, nextRows]) => {
      if (active && latestSearch.current === 0) { setProducts(nextProducts); setLocations(nextLocations); setRows(nextRows); setSearched(true); setError(''); }
      else if (active) { setProducts(nextProducts); setLocations(nextLocations); }
    }).catch(() => { if (active && latestSearch.current === 0) setError('庫存資料載入失敗，請重新進入頁面。'); })
      .finally(() => { if (active && latestSearch.current === 0) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (refreshKey > 0) void runSearch(appliedFilters);
  }, [refreshKey]);

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

  async function handleExport() {
    setExporting(true); setError('');
    try { await downloadInventoryCsv(appliedFilters); }
    catch { setError('CSV 匯出失敗，請確認連線後再試。'); }
    finally { setExporting(false); }
  }

  return <section className="card inventory-panel" aria-labelledby="inventory-title">
    <h2 id="inventory-title">庫存查詢</h2>
    <p className="hint">依品項、批次碼或儲位查詢。位置列顯示符合條件的儲位；「全批合計」包含該批在所有儲位的餘量，歸零位置仍會顯示。</p>
    {error && <p role="alert" className="error">{error}</p>}
    <form onSubmit={handleSubmit}>
      <fieldset disabled={loading}>
        <label>品項<select value={productId} onChange={(event) => setProductId(event.target.value)}>
          <option value="">全部品項</option>
          {products.map((product) => <option key={product.id} value={product.id}>{productOptionLabel(product)}</option>)}
        </select></label>
        {productId && <p className="hint">已選品項：{products.find((item) => item.id === Number(productId))?.name}</p>}
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
          <button type="button" className="secondary" disabled={exporting || loading} onClick={() => void handleExport()}>{exporting ? '匯出中…' : '匯出目前查詢 CSV'}</button>
        </div>
        <p className="hint">CSV 使用上次成功查詢的條件；修改欄位後請先按「查詢／更新」。匯出數量以下載當下資料庫為準。</p>
      </fieldset>
    </form>
    {loading && <p role="status">正在讀取資料庫庫存…</p>}
    {!loading && searched && rows.length === 0 && !error && <p role="status">沒有符合條件的庫存。</p>}
    <div className="inventory-results">{[...groups.values()].map((positions) =>
      <InventoryLot key={positions[0].lot_id} positions={positions} role={role} onExpirySaved={() => runSearch(appliedFilters)} />)}</div>
  </section>;
}
