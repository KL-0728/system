import { FormEvent, useEffect, useRef, useState } from 'react';
import BackToTop from '../components/BackToTop';
import QuickJump from '../components/QuickJump';
import { createLocation, createProduct, getLocations, getProducts, getWarehouses, updateLocation, updateProduct } from '../api/masterData';
import type { Location, Product, Warehouse } from '../types/masterData';
import { smoothScrollTo } from '../utils/smoothScroll';

const emptyProduct = { name: '', unit: '籠', min_qty: 0, target_qty: 0, is_active: true };

export default function SettingsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [product, setProduct] = useState(emptyProduct);
  const [productId, setProductId] = useState<number | null>(null);
  const [location, setLocation] = useState({ warehouse_id: 0, number: '', is_active: true });
  const [locationId, setLocationId] = useState<number | null>(null);
  const [pageMessage, setPageMessage] = useState('');
  const [productMessage, setProductMessage] = useState('');
  const [locationMessage, setLocationMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const productEditor = useRef<HTMLElement>(null);
  const locationEditor = useRef<HTMLElement>(null);

  async function load() {
    const [productRows, locationRows, warehouseRows] = await Promise.all([getProducts(), getLocations(), getWarehouses()]);
    setProducts(productRows); setLocations(locationRows); setWarehouses(warehouseRows);
    setLocation((current) => ({ ...current, warehouse_id: current.warehouse_id || warehouseRows[0]?.id || 0 }));
  }
  useEffect(() => { load().catch((error) => setPageMessage(error instanceof Error ? error.message : '讀取失敗')); }, []);

  async function saveProduct(event: FormEvent) {
    event.preventDefault(); setBusy(true); setProductMessage('');
    try {
      if (productId === null) await createProduct(product); else await updateProduct(productId, product);
      setProductMessage(productId === null ? '品項新增成功' : '品項更新成功'); setProduct(emptyProduct); setProductId(null); await load();
    } catch (error) { setProductMessage(error instanceof Error ? error.message : '儲存失敗'); }
    finally { setBusy(false); }
  }
  async function saveLocation(event: FormEvent) {
    event.preventDefault(); setBusy(true); setLocationMessage('');
    try {
      const warehouse = warehouses.find((item) => item.id === location.warehouse_id);
      if (!warehouse) throw new Error('請選擇冷凍庫');
      if (!/^\d{1,2}$/.test(location.number) || Number(location.number) < 1 || Number(location.number) > 99) throw new Error('儲位編號請輸入 1 至 99');
      const code = `${warehouse.code}-${String(Number(location.number)).padStart(2, '0')}`;
      const payload = { warehouse_id: location.warehouse_id, code, is_active: location.is_active };
      if (locationId === null) await createLocation(payload); else await updateLocation(locationId, payload);
      setLocationMessage(locationId === null ? `儲位 ${code} 新增成功` : `儲位 ${code} 更新成功`); setLocation({ warehouse_id: warehouses[0]?.id || 0, number: '', is_active: true }); setLocationId(null); await load();
    } catch (error) { setLocationMessage(error instanceof Error ? error.message : '儲存失敗'); }
    finally { setBusy(false); }
  }
  function editProduct(item: Product) {
    setProductMessage(''); setProductId(item.id);
    setProduct({ name: item.name, unit: item.unit, min_qty: item.min_qty, target_qty: item.target_qty, is_active: item.is_active });
    smoothScrollTo(productEditor.current);
  }
  function editLocation(item: Location) {
    const match = item.code.match(/-([0-9]{2})$/);
    if (!match || Number(match[1]) === 0) {
      setLocationMessage(`儲位 ${item.code} 是舊格式，無法用編號表單編輯；請先確認資料。`);
      smoothScrollTo(locationEditor.current);
      return;
    }
    setLocationMessage(''); setLocationId(item.id);
    setLocation({ warehouse_id: item.warehouse_id, number: String(Number(match[1])), is_active: item.is_active });
    smoothScrollTo(locationEditor.current);
  }
  const selectedWarehouse = warehouses.find((item) => item.id === location.warehouse_id);
  const locationPreview = selectedWarehouse && /^\d{1,2}$/.test(location.number) && Number(location.number) > 0
    ? `${selectedWarehouse.code}-${String(Number(location.number)).padStart(2, '0')}`
    : '尚未輸入';
  const productQuantityInvalid = product.target_qty < product.min_qty;

  return <main className="app-shell"><p className="eyebrow">管理者設定</p><h1>品項與儲位</h1>
    <QuickJump items={[{ id: 'settings-products', label: '品項管理' }, { id: 'settings-locations', label: '儲位管理' }]} />
    {pageMessage && <p className="notice error" role="alert">{pageMessage}</p>}
    <section ref={productEditor} id="settings-products" className="card jump-target"><h2>{productId === null ? '新增品項' : '編輯品項'}</h2>{productMessage && <p className="notice" role="status">{productMessage}</p>}<form onSubmit={saveProduct}>
      <label>名稱<input value={product.name} onChange={(event) => setProduct({ ...product, name: event.target.value })} required /></label>
      <label>單位<input value={product.unit} onChange={(event) => setProduct({ ...product, unit: event.target.value })} required /></label>
      <div className="form-row"><label>最低量<input type="number" min="0" step="1" value={product.min_qty} onChange={(event) => setProduct({ ...product, min_qty: Number(event.target.value) })} required /></label><label>目標量<input type="number" min={product.min_qty} step="1" value={product.target_qty} onChange={(event) => setProduct({ ...product, target_qty: Number(event.target.value) })} aria-describedby="quantity-rule" required /></label></div>
      {productQuantityInvalid && <p id="quantity-rule" className="field-error" role="alert">目標量不得低於最低量</p>}
      <label className="check"><input type="checkbox" checked={product.is_active} onChange={(event) => setProduct({ ...product, is_active: event.target.checked })} />啟用</label>
      <div className="button-row"><button disabled={busy || productQuantityInvalid}>儲存品項</button>{productId !== null && <button type="button" className="secondary" onClick={() => { setProductId(null); setProduct(emptyProduct); }}>取消編輯</button>}</div>
    </form><div className="manage-list">{products.map((item) => <article key={item.id}><div><strong>{item.name}</strong><span>{item.unit} · 最低 {item.min_qty} · 目標 {item.target_qty} · {item.is_active ? '啟用' : '停用'}</span></div><button className="secondary" onClick={() => editProduct(item)}>編輯</button></article>)}</div></section>
    <section ref={locationEditor} id="settings-locations" className="card jump-target"><h2>{locationId === null ? '新增儲位' : '編輯儲位'}</h2>{locationMessage && <p className="notice" role="status">{locationMessage}</p>}<form onSubmit={saveLocation}>
      <label>冷凍庫<select value={location.warehouse_id} onChange={(event) => setLocation({ ...location, warehouse_id: Number(event.target.value) })}>{warehouses.map((item) => <option key={item.id} value={item.id}>{item.code}／{Array.from(item.name).slice(0, 8).join('')}</option>)}</select></label>
      {selectedWarehouse && <p className="hint">已選冷凍庫：{selectedWarehouse.name}</p>}
      <label>儲位編號<input type="number" min="1" max="99" step="1" value={location.number} onChange={(event) => setLocation({ ...location, number: event.target.value })} placeholder="例如：3，系統會建立 B-03" required /></label>
      <p className="hint">完整儲位代碼：{locationPreview}</p>
      <label className="check"><input type="checkbox" checked={location.is_active} onChange={(event) => setLocation({ ...location, is_active: event.target.checked })} />啟用</label>
      <div className="button-row"><button disabled={busy || !location.warehouse_id}>儲存儲位</button>{locationId !== null && <button type="button" className="secondary" onClick={() => { setLocationMessage(''); setLocationId(null); setLocation({ warehouse_id: warehouses[0]?.id || 0, number: '', is_active: true }); }}>取消編輯</button>}</div>
    </form><div className="manage-list">{locations.map((item) => <article key={item.id}><div><strong>{item.code}</strong><span>{item.warehouse_name} · {item.is_active ? '啟用' : '停用'}</span></div><button className="secondary" onClick={() => editLocation(item)}>編輯</button></article>)}</div></section>
    <BackToTop />
  </main>;
}
