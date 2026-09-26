import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ApiError } from '../api/client';
import { getProducts } from '../api/masterData';
import { createShortageDemand, getShortageDemands, type ShortageDemand } from '../api/shortages';
import type { Product } from '../types/masterData';
import { smoothScrollTo } from '../utils/smoothScroll';
import { releaseFormFocus } from '../utils/formFocus';
import { productOptionLabel } from '../utils/productOptionLabel';

export default function ShortagePage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [records, setRecords] = useState<ShortageDemand[]>([]);
  const [productId, setProductId] = useState('');
  const [qty, setQty] = useState('');
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const inFlight = useRef(false);
  const resultRef = useRef<HTMLParagraphElement>(null);
  const product = products.find((item) => item.id === Number(productId));

  async function refresh() {
    setLoading(true);
    try {
      const [nextProducts, nextRecords] = await Promise.all([getProducts(), getShortageDemands()]);
      setProducts(nextProducts.filter((item) => item.is_active));
      setRecords(nextRecords);
      setError('');
    } catch { setError('無法更新品項與缺貨需求紀錄，請確認連線。'); }
    finally { setLoading(false); }
  }

  useEffect(() => { void refresh(); }, []);
  useEffect(() => { if (success) smoothScrollTo(resultRef.current); }, [success]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    releaseFormFocus(event);
    if (inFlight.current || busy || loading || uncertain) return;
    const amount = Number(qty);
    if (!product || !Number.isSafeInteger(amount) || amount <= 0) {
      setError('請選擇品項並輸入正整數詢問數量。'); return;
    }
    inFlight.current = true; setBusy(true); setError(''); setSuccess('');
    try {
      const saved = await createShortageDemand({ product_id: product.id, qty: amount, note });
      setSuccess(`已記錄缺貨需求 #${saved.id}：${saved.product_name} ${saved.qty} ${saved.unit}。這不是出庫，不會扣除庫存。`);
      setQty(''); setNote('');
      await refresh();
    } catch (failure) {
      if (failure instanceof ApiError && [401, 403, 404, 409, 422].includes(failure.status)) {
        setError(failure.message);
      } else {
        setUncertain(true);
        setError('結果未確認，請先更新缺貨紀錄核對，不要直接重送。');
      }
    } finally { inFlight.current = false; setBusy(false); }
  }

  return <section className="card shortage-panel" aria-labelledby="shortage-title">
    <h2 id="shortage-title">缺貨需求紀錄</h2>
    <p className="hint">客人想買但沒有成交時，記下品項與詢問數量；即使目前庫存為 0 也可記錄。這不是訂單或出庫，不會變動庫存。</p>
    {error && <p className="error" role="alert">{error}</p>}
    {success && <p ref={resultRef} className="notice" role="status">{success}</p>}
    <form onSubmit={submit}>
      <fieldset disabled={busy || loading || uncertain}>
        <label>品項<select required value={productId} onChange={(event) => setProductId(event.target.value)}>
          <option value="">請選擇品項</option>
          {products.map((item) => <option value={item.id} key={item.id}>{productOptionLabel(item)}</option>)}
        </select></label>
        {product && <p className="hint">已選品項：{product.name}（{product.unit}）</p>}
        <label>詢問數量{product ? `（${product.unit}）` : ''}<input type="number" inputMode="numeric" min="1" step="1" required value={qty} onChange={(event) => setQty(event.target.value)} /></label>
        <label>備註（選填，最多 500 字）<input maxLength={500} value={note} onChange={(event) => setNote(event.target.value)} /></label>
        <button type="submit" disabled={!product}>{busy ? '記錄中…' : '記錄缺貨需求'}</button>
      </fieldset>
    </form>
    <div className="shortage-controls">
      <button type="button" className="secondary" disabled={busy || loading} onClick={() => void refresh()}>更新我的缺貨紀錄</button>
      {uncertain && <><p role="alert">先核對最近紀錄的品項、數量和時間；查不到不代表送件一定失敗。</p>
        <button type="button" disabled={busy || loading} onClick={() => { setUncertain(false); setError(''); setQty(''); setNote(''); }}>我已核對，開始新紀錄</button></>}
    </div>
    <h3>我的最近紀錄（最多 100 筆）</h3>
    {!loading && records.length === 0 && <p>目前沒有缺貨需求紀錄。</p>}
    <div className="shortage-records">{records.map((item) => <article key={item.id}>
      <strong>#{item.id} {item.product_name}：詢問 {item.qty} {item.unit}</strong>
      <span>{new Date(item.created_at).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false })}（臺灣時間）／{item.actor_name}</span>
      {item.note && <span>備註：{item.note}</span>}
    </article>)}</div>
  </section>;
}
