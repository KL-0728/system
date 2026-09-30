import { useEffect, useRef, useState, type FormEvent } from 'react';
import { releaseFormFocus } from '../utils/formFocus';
import { smoothScrollTo } from '../utils/smoothScroll';
import { ApiError } from '../api/client';
import { getInboundRecords, submitInbound, type InboundRecord } from '../api/inventory';
import { getProducts } from '../api/masterData';
import { getStockLocationOptions } from '../api/stockOptions';
import type { Product } from '../types/masterData';
import type { StockLocationOption } from '../types/stock';
import { productOptionLabel } from '../utils/productOptionLabel';

const taiwanNow = () => new Date().toLocaleString('sv-SE', { timeZone: 'Asia/Taipei', hour12: false }).replace(' ', 'T').slice(0, 16);

export default function InboundPage({ onStockChanged }: { onStockChanged?: () => void }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [locations, setLocations] = useState<StockLocationOption[]>([]);
  const [records, setRecords] = useState<InboundRecord[]>([]);
  const [productId, setProductId] = useState('');
  const [locationId, setLocationId] = useState('');
  const [qty, setQty] = useState('');
  const [receivedAt, setReceivedAt] = useState(taiwanNow);
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [uncertain, setUncertain] = useState(false);
  const inFlight = useRef(false);
  const resultRef = useRef<HTMLParagraphElement>(null);
  const product = products.find((row) => row.id === Number(productId));
  const location = locations.find((row) => row.location_id === Number(locationId));

  async function refresh() {
    setLoading(true); setReady(false);
    try {
      const [nextProducts, nextLocations, nextRecords] = await Promise.all([
        getProducts(), getStockLocationOptions(), getInboundRecords(),
      ]);
      setProducts(nextProducts.filter((row) => row.is_active));
      setLocations(nextLocations); setRecords(nextRecords);
      setReady(true); setError('');
    } catch { setError('無法更新入庫資料與紀錄，請確認連線後再查詢。'); }
    finally { setLoading(false); }
  }

  useEffect(() => { void refresh(); }, []);
  useEffect(() => { if (success) smoothScrollTo(resultRef.current); }, [success]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    releaseFormFocus(event);
    if (inFlight.current || loading || !ready || uncertain) return;
    setError(''); setSuccess('');
    const amount = Number(qty);
    if (!product || !location || !Number.isSafeInteger(amount) || amount <= 0) {
      setError('請選擇品項與儲位，並輸入正整數數量。'); return;
    }
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(receivedAt) || receivedAt > taiwanNow()) {
      setError('請輸入臺灣時間的實際進貨日期與時間，不可晚於現在。'); return;
    }
    inFlight.current = true; setBusy(true);
    try {
      const result = await submitInbound({
        product_id: product.id, location_id: location.location_id, qty: amount,
        received_date: receivedAt.slice(0, 10), received_at: `${receivedAt}:00+08:00`, note,
      });
      setSuccess(`已登錄入庫：${product.name} ${amount} ${product.unit} → ${location.location_code}。進貨時間 ${receivedAt.replace('T', ' ')}；批次 ${result.lot_code}；異動 #${result.movement_id}。`);
      setQty(''); setNote('');
      onStockChanged?.();
      await refresh();
    } catch (failure) {
      if (failure instanceof ApiError && [401, 403, 409, 422].includes(failure.status)) {
        setError(failure.status === 422 ? `欄位格式不正確：${failure.message}` : failure.message);
      } else {
        setUncertain(true);
        setError('結果未確認，請查詢紀錄；請勿直接重送。核對品項、儲位、數量、時間與操作者後再決定。');
      }
    } finally { inFlight.current = false; setBusy(false); }
  }

  return <section className="card inbound-panel" aria-labelledby="inbound-title">
    <h2 id="inbound-title">入庫</h2>
    <p className="hint">到貨後在儲位旁登錄。進貨時間預設現在；批次由系統產生。送出後請核對成功回執。</p>
    {error && <p role="alert" className="error">{error}</p>}
    {success && <p ref={resultRef} role="status" className="notice">{success}</p>}
    {loading && <p role="status">正在更新品項、儲位與紀錄…</p>}
    <form onSubmit={handleSubmit}>
      <fieldset disabled={busy || loading || uncertain}>
        <label>品項<select required value={productId} onChange={(event) => { setProductId(event.target.value); setSuccess(''); }}>
          <option value="">請選擇品項</option>
          {products.map((row) => <option key={row.id} value={row.id}>{productOptionLabel(row)}</option>)}
        </select></label>
        {product && <p className="hint">已選品項：{product.name}（{product.unit}）</p>}
        <label>儲位<select required value={locationId} onChange={(event) => { setLocationId(event.target.value); setSuccess(''); }}>
          <option value="">請選擇儲位</option>
          {locations.map((row) => <option key={row.location_id} value={row.location_id}>{row.location_code}（{row.warehouse_name}）</option>)}
        </select></label>
        {!loading && ready && (products.length === 0 || locations.length === 0) && <p>目前沒有可用的啟用品項或儲位，請管理者先到基本資料建立。</p>}
        <div className="form-row">
          <label>入庫數量{product ? `（${product.unit}）` : ''}<input type="number" inputMode="numeric" min="1" step="1" required value={qty} onChange={(event) => setQty(event.target.value)} /></label>
          <label>實際進貨時間（臺灣時間）<input type="datetime-local" required max={taiwanNow()} value={receivedAt} onChange={(event) => setReceivedAt(event.target.value)} /></label>
        </div>
        <label>備註（選填，最多 500 字，例如供應商）<input maxLength={500} value={note} onChange={(event) => setNote(event.target.value)} /></label>
        {product && location && qty && <p className="notice">即將登錄：{product.name} {qty} {product.unit} → {location.location_code}</p>}
        <button type="submit" disabled={!product || !location}>{busy ? '入庫處理中…' : '確認已放好並登錄'}</button>
      </fieldset>
    </form>
    <div className="inbound-controls">
      <button type="button" className="secondary" disabled={busy || loading} onClick={() => void refresh()}>更新品項、儲位與入庫紀錄</button>
      <p className="hint">重新讀取資料庫，適合另一台裝置剛操作後使用；不會新增一筆入庫。</p>
      {uncertain && <><p role="alert">上次入庫結果未確認。即使查不到紀錄，也請先確認伺服器已處理完畢再決定是否重新操作，避免重複建立批次。</p>
        <button type="button" disabled={!ready || loading || busy} onClick={() => { setUncertain(false); setQty(''); setNote(''); setError(''); }}>我已核對紀錄，開始新的操作</button></>}
    </div>
    <h3>最近入庫紀錄（最多 100 筆）</h3>
    {!loading && records.length === 0 && <p>目前沒有入庫紀錄。</p>}
    <div className="inbound-records">{records.map((record) => <article key={record.movement_id}>
      <strong>#{record.movement_id} {record.lot_code}：{record.product_name} {record.qty} {record.unit}</strong>
      <span>儲位 {record.location_code}／實際進貨 {record.received_at ? record.received_at.replace('T', ' ').slice(0, 16) : `${record.received_date}（舊資料未記時間）`}</span>
      <span>系統登錄時間 {new Date(record.created_at).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false })}（臺灣時間）／{record.actor_name}</span>
      {record.note && <span>備註：{record.note}</span>}
    </article>)}</div>
  </section>;
}
