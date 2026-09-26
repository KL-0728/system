import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ApiError } from '../api/client';
import { getOutboundRecords, submitOutbound, type OutboundRecord } from '../api/outbound';
import { getBalanceOptions } from '../api/stockOptions';
import type { BalanceOption } from '../types/stock';
import { releaseFormFocus } from '../utils/formFocus';
import { stockOptionLabel } from '../utils/stockOptionLabel';
import { smoothScrollTo } from '../utils/smoothScroll';

const keyOf = (balance: BalanceOption) => `${balance.lot_id}:${balance.location_id}`;

export default function OutboundPage({ refreshKey = 0, onStockChanged }: {
  refreshKey?: number; onStockChanged?: () => void;
}) {
  const [balances, setBalances] = useState<BalanceOption[]>([]);
  const [records, setRecords] = useState<OutboundRecord[]>([]);
  const [selectedKey, setSelectedKey] = useState('');
  const [qty, setQty] = useState('');
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [uncertain, setUncertain] = useState(false);
  const [checked, setChecked] = useState(false);
  const inFlight = useRef(false);
  const resultRef = useRef<HTMLParagraphElement>(null);
  const selected = balances.find((row) => keyOf(row) === selectedKey);

  async function refresh() {
    setLoading(true);
    try {
      const [newBalances, newRecords] = await Promise.all([
        getBalanceOptions({ positiveOnly: false }), getOutboundRecords(),
      ]);
      setBalances(newBalances);
      setRecords(newRecords);
      setChecked(true);
      setError('');
    } catch {
      setChecked(false);
      setError('無法更新庫存與紀錄，請確認連線後再查詢。');
    } finally { setLoading(false); }
  }

  useEffect(() => { void refresh(); }, [refreshKey]);
  useEffect(() => { if (success) smoothScrollTo(resultRef.current); }, [success]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    releaseFormFocus(event);
    if (inFlight.current || loading || uncertain) return;
    setError(''); setSuccess('');
    const amount = Number(qty);
    if (!selected || !Number.isSafeInteger(amount) || amount <= 0) {
      setError('請選擇批次與儲位，並輸入正整數數量。'); return;
    }
    if (selected.has_pending) { setError('此批次與儲位有待審申請，暫停出庫。'); return; }
    if (amount > selected.qty) { setError('出庫數量不可超過目前餘量。'); return; }
    inFlight.current = true; setBusy(true);
    try {
      const result = await submitOutbound({ lot_id: selected.lot_id, location_id: selected.location_id, qty: amount, note });
      setBalances((rows) => rows.map((row) => keyOf(row) === selectedKey ? { ...row, qty: result.qty } : row));
      setSuccess(`${selected.product_name}／${selected.lot_code}／${selected.location_code} 出庫 ${amount} ${selected.unit}成功，餘量 ${result.qty} ${selected.unit}；異動編號 #${result.movement_id}。`);
      setQty(''); setNote('');
      onStockChanged?.();
      await refresh();
    } catch (failure) {
      if (failure instanceof ApiError && [401, 403, 409, 422].includes(failure.status)) {
        setError(failure.status === 422 ? '欄位格式不正確，請確認數量為正整數、備註最多 500 字。' : failure.message);
      } else {
        setUncertain(true); setChecked(false);
        setError('結果未確認，請查詢紀錄；請勿直接重送。核對批次、位置、時間、操作者與數量後再決定。');
      }
    } finally { inFlight.current = false; setBusy(false); }
  }

  return <section className="card outbound-panel" aria-labelledby="outbound-title">
    <h2 id="outbound-title">出庫</h2>
    <p className="hint">選擇現有批次與儲位，確認數量後出庫。下方可查詢最近 100 筆出庫紀錄。</p>
    {error && <p role="alert" className="error">{error}</p>}
    {success && <p ref={resultRef} role="status" className="notice">{success}</p>}
    {loading && <p role="status">正在更新庫存與紀錄…</p>}
    <form onSubmit={handleSubmit}>
      <fieldset disabled={busy || loading || uncertain}>
        <label>批次與儲位<select required value={selectedKey} onChange={(event) => { setSelectedKey(event.target.value); setQty(''); setSuccess(''); }}>
          <option value="">請選擇批次與儲位</option>
          {balances.map((row) => <option key={keyOf(row)} value={keyOf(row)} disabled={row.has_pending || row.qty === 0}>
            {stockOptionLabel(row)}
          </option>)}
        </select></label>
        {!loading && balances.length === 0 && <p>目前沒有庫存資料。</p>}
        {selected && <p className="notice">{selected.product_name}｜{selected.lot_code}｜{selected.location_code}｜入庫日 {selected.received_date}<br />目前餘量：{selected.qty} {selected.unit}{selected.has_pending && '（待審凍結，不能出庫）'}</p>}
        <label>出庫數量<input type="number" inputMode="numeric" min="1" step="1" max={selected?.qty} required value={qty} onChange={(event) => setQty(event.target.value)} /></label>
        <label>備註（選填，最多 500 字）<input maxLength={500} value={note} onChange={(event) => setNote(event.target.value)} /></label>
        <button type="submit" disabled={!selected || selected.has_pending || selected.qty === 0}>{busy ? '出庫處理中…' : '確認出庫'}</button>
      </fieldset>
    </form>
    <div className="outbound-controls">
      <button type="button" className="secondary" disabled={busy || loading} onClick={() => void refresh()}>查詢紀錄／更新餘量</button>
      {uncertain && <><p role="alert">上次出庫結果未確認。即使查不到紀錄，也請先確認伺服器已處理完畢再決定是否重新操作。</p>
        <button type="button" disabled={!checked || loading || busy} onClick={() => { setUncertain(false); setQty(''); setNote(''); setError(''); }}>我已核對紀錄，開始新的操作</button></>}
    </div>
    <h3>最近出庫紀錄（最多 100 筆）</h3>
    {!loading && records.length === 0 && <p>目前沒有出庫紀錄。</p>}
    <div className="outbound-records">{records.map((record) => <article key={record.movement_id}>
      <strong>#{record.movement_id} {record.product_name}：出庫 {record.qty} {record.unit}</strong>
      <span>{record.lot_code}／{record.location_code}</span>
      <span>{new Date(record.created_at).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false })}（臺灣時間）／{record.actor_name}</span>
      {record.note && <span>備註：{record.note}</span>}
    </article>)}</div>
  </section>;
}
