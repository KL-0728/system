import { useEffect, useRef, useState } from 'react';
import { getLocations, getWarehouses } from '../api/masterData';
import { searchInventory } from '../api/inventorySearch';
import type { Location, Warehouse } from '../types/masterData';
import type { InventoryBalance } from '../types/inventory';

export default function LocationMapPage({ refreshKey = 0 }: { refreshKey?: number }) {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [rows, setRows] = useState<InventoryBalance[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const detailRef = useRef<HTMLDivElement>(null);

  async function refresh() {
    setLoading(true);
    try {
      const [nextWarehouses, nextLocations, nextRows] = await Promise.all([
        getWarehouses(), getLocations(), searchInventory({}),
      ]);
      setWarehouses(nextWarehouses); setLocations(nextLocations); setRows(nextRows); setError('');
    } catch { setError('無法更新儲位與庫存，請確認連線後重試。'); }
    finally { setLoading(false); }
  }

  useEffect(() => { void refresh(); }, [refreshKey]);
  useEffect(() => {
    if (selectedId !== null) detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [selectedId]);
  function selectLocation(id: number) {
    if (selectedId === id) detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    else setSelectedId(id);
  }
  const selected = locations.find((item) => item.id === selectedId);
  const currentRows = rows.filter((row) => row.location_id === selectedId && row.qty > 0);

  return <section className="card location-map-panel" aria-labelledby="location-map-title">
    <h2 id="location-map-title">儲位簡圖</h2>
    <p className="hint">依代碼排列的示意方格，不代表實際建築平面圖；點儲位查看目前有餘量的批次。</p>
    <button type="button" className="secondary" disabled={loading} onClick={() => void refresh()}>更新簡圖</button>
    {loading && <p role="status">正在更新儲位簡圖…</p>}
    {error && <p className="error" role="alert">{error}</p>}
    <div className="warehouse-map-list">{warehouses.map((warehouse) => <section key={warehouse.id} aria-label={warehouse.name}>
      <h3>{warehouse.name}</h3>
      <div className="location-map-grid">{locations.filter((item) => item.warehouse_id === warehouse.id)
        .sort((a, b) => a.code.localeCompare(b.code))
        .map((location) => {
          const lotCount = rows.filter((row) => row.location_id === location.id && row.qty > 0).length;
          return <button key={location.id} type="button" className={`secondary location-tile${selectedId === location.id ? ' selected' : ''}`}
            aria-pressed={selectedId === location.id} onClick={() => selectLocation(location.id)}>
            <strong>{location.code}</strong><span>{location.is_active ? `${lotCount} 批有庫存` : '已停用'}</span>
          </button>;
        })}</div>
    </section>)}</div>
    {selected && <div className="location-map-detail" ref={detailRef} aria-live="polite">
      <h3>{selected.code} 目前庫存</h3>
      {currentRows.length === 0 ? <p>此儲位目前沒有正餘量庫存。</p> : <div className="item-grid">{currentRows.map((row) => <article key={row.lot_id}>
        <strong>{row.product_name}／{row.lot_code}</strong>
        <span>{row.qty} {row.unit} · 入庫日 {row.received_date}</span>
      </article>)}</div>}
    </div>}
  </section>;
}
