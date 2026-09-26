import { useEffect, useRef, useState, type FormEvent } from 'react';
import { releaseFormFocus } from '../utils/formFocus';
import { ApiError } from '../api/client';
import { getInboundRecords, submitInbound, type InboundRecord } from '../api/inventory';
import { getProducts } from '../api/masterData';
import { getStockLocationOptions } from '../api/stockOptions';
import type { Product } from '../types/masterData';
import type { StockLocationOption } from '../types/stock';

// en-CA formats as YYYY-MM-DD; the backend rejects dates after today in Taiwan time.
const taiwanToday = () => new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Taipei' });

export default function InboundPage({ onStockChanged }: { onStockChanged?: () => void }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [locations, setLocations] = useState<StockLocationOption[]>([]);
  const [records, setRecords] = useState<InboundRecord[]>([]);
  const [productId, setProductId] = useState('');
  const [locationId, setLocationId] = useState('');
  const [qty, setQty] = useState('');
  const [receivedDate, setReceivedDate] = useState(taiwanToday);
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [uncertain, setUncertain] = useState(false);
  const inFlight = useRef(false);
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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    releaseFormFocus(event);
    if (inFlight.current || loading || !ready || uncertain) return;
    setError(''); setSuccess('');
    const amount = Number(qty);
    if (!product || !location || !Number.isSafeInteger(amount) || amount <= 0) {
      setError('請選擇品項與儲位，並輸入正整數數量。'); return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(receivedDate) || receivedDate > taiwanToday()) {
      setError('請輸入今天或以前的入庫日期。'); return;
    }
    inFlight.current = true; setBusy(true);
    try {
      const result = await submitInbound({
        product_id: product.id, location_id: location.location_id, qty: amount, received_date: receivedDate, note,
      });
      setSuccess(`入庫成功：批次 ${result.lot_code}，${product.name} ${amount} ${product.unit}放在 ${location.location_code}，該儲位此批餘量 ${result.qty} ${product.unit}；異動編號 #${result.movement_id}。`);
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
    <p className="hint">選擇品項與一個儲位，輸入數量與入庫日期；批次編號由系統產生。同一批要放多處，請入庫後再用移位分拆。</p>
    {error && <p role="alert" className="error">{error}</p>}
    {success && <p role="status" className="notice">{success}</p>}
    {loading && <p role="status">正在更新品項、儲位與紀錄…</p>}
    <form onSubmit={handleSubmit}>
      <fieldset disabled={busy || loading || uncertain}>
        <label>品項<select required value={productId} onChange={(event) => { setProductId(event.target.value); setSuccess(''); }}>
          <option value="">請選擇品項</option>
          {products.map((row) => <option key={row.id} value={row.id}>{row.name}（{row.unit}）</option>)}
        </select></label>
        <label>儲位<select required value={locationId} onChange={(event) => { setLocationId(event.target.value); setSuccess(''); }}>
          <option value="">請選擇儲位</option>
          {locations.map((row) => <option key={row.location_id} value={row.location_id}>{row.location_code}（{row.warehouse_name}）</option>)}
        </select></label>
        {!loading && ready && (products.length === 0 || locations.length === 0) && <p>目前沒有可用的啟用品項或儲位，請管理者先到基本資料建立。</p>}
        <div className="form-row">
          <label>入庫數量{product ? `（${product.unit}）` : ''}<input type="number" inputMode="numeric" min="1" step="1" required value={qty} onChange={(event) => setQty(event.target.value)} /></label>
          <label>入庫日期<span className="date-input-frame"><input type="date" required max={taiwanToday()} value={receivedDate} onChange={(event) => setReceivedDate(event.target.value)} /></span></label>
        </div>
        <label>備註（選填，最多 500 字，例如供應商）<input maxLength={500} value={note} onChange={(event) => setNote(event.target.value)} /></label>
        <button type="submit" disabled={!product || !location}>{busy ? '入庫處理中…' : '確認入庫'}</button>
      </fieldset>
    </form>
    <div className="inbound-controls">
      <button type="button" className="secondary" disabled={busy || loading} onClick={() => void refresh()}>查詢入庫紀錄</button>
      {uncertain && <><p role="alert">上次入庫結果未確認。即使查不到紀錄，也請先確認伺服器已處理完畢再決定是否重新操作，避免重複建立批次。</p>
        <button type="button" disabled={!ready || loading || busy} onClick={() => { setUncertain(false); setQty(''); setNote(''); setError(''); }}>我已核對紀錄，開始新的操作</button></>}
    </div>
    <h3>最近入庫紀錄（最多 100 筆）</h3>
    {!loading && records.length === 0 && <p>目前沒有入庫紀錄。</p>}
    <div className="inbound-records">{records.map((record) => <article key={record.movement_id}>
      <strong>#{record.movement_id} {record.lot_code}：{record.product_name} {record.qty} {record.unit}</strong>
      <span>儲位 {record.location_code}／入庫日 {record.received_date}</span>
      <span>{new Date(record.created_at).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false })}（臺灣時間）／{record.actor_name}</span>
      {record.note && <span>備註：{record.note}</span>}
    </article>)}</div>
  </section>;
}
