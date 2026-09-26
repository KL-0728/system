import { useEffect, useRef, useState, type FormEvent } from 'react';
import { getMyAdjustments, submitAdjustment, type AdjustmentRecord } from '../api/adjustments';
import { ApiError } from '../api/client';
import { getBalanceOptions } from '../api/stockOptions';
import type { BalanceOption } from '../types/stock';

const keyOf = (row: BalanceOption) => `${row.lot_id}:${row.location_id}`;
const statusLabel = { PENDING: '待審', APPROVED: '已核准', REJECTED: '已駁回' };

export default function AdjustmentPage({ refreshKey = 0, onRequestCreated }: {
  refreshKey?: number; onRequestCreated?: () => void;
}) {
  const [balances, setBalances] = useState<BalanceOption[]>([]);
  const [records, setRecords] = useState<AdjustmentRecord[]>([]);
  const [selectedKey, setSelectedKey] = useState('');
  const [kind, setKind] = useState<'COUNT' | 'SCRAP'>('COUNT');
  const [amount, setAmount] = useState('');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(true);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const inFlight = useRef(false);
  const selected = balances.find((row) => keyOf(row) === selectedKey);

  async function refresh() {
    setLoading(true); setReady(false);
    try {
      const [nextBalances, nextRecords] = await Promise.all([
        getBalanceOptions({ positiveOnly: false }), getMyAdjustments(),
      ]);
      setBalances(nextBalances); setRecords(nextRecords); setReady(true); setError('');
    } catch { setError('無法更新庫存與申請紀錄，請確認連線後再查詢。'); }
    finally { setLoading(false); }
  }

  useEffect(() => { void refresh(); }, [refreshKey]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current || loading || !ready || uncertain) return;
    setError(''); setSuccess('');
    const value = Number(amount);
    if (!selected || amount.trim() === '' || !Number.isSafeInteger(value) || (kind === 'COUNT' ? value < 0 : value <= 0)) {
      setError(kind === 'COUNT' ? '請選擇批次與儲位，並輸入非負整數實數。' : '請選擇批次與儲位，並輸入正整數報廢量。');
      return;
    }
    if (!reason.trim()) { setError('請填寫原因。'); return; }
    if (selected.has_pending) { setError('此批次與儲位已有待審申請。'); return; }
    if (kind === 'SCRAP' && value > selected.qty) { setError('報廢量不可超過目前餘量。'); return; }
    inFlight.current = true; setBusy(true);
    try {
      const record = await submitAdjustment({
        lot_id: selected.lot_id, location_id: selected.location_id,
        kind, ...(kind === 'COUNT' ? { observed_qty: value } : { damaged_qty: value }),
        reason: reason.trim(),
      });
      setSuccess(`申請 #${record.id} 已送出，狀態為待審；帳面仍為 ${record.original_qty} ${record.unit}。`);
      setAmount(''); setReason('');
      onRequestCreated?.();
      await refresh();
    } catch (failure) {
      if (failure instanceof ApiError && [401, 403, 409, 422].includes(failure.status)) {
        setError(failure.message);
      } else {
        setUncertain(true); setReady(false);
        setError('送件結果未確認，請先查詢自己的申請紀錄，不要直接重送。');
      }
    } finally { inFlight.current = false; setBusy(false); }
  }

  return <section className="card adjustment-panel" aria-labelledby="adjustment-title">
    <h2 id="adjustment-title">盤點／損耗申請</h2>
    <p className="hint">倉管填寫現場實數或報廢量及原因。送件後由管理者審核；待審期間帳面餘量不變，同批次與儲位暫停異動。</p>
    {error && <p role="alert" className="error">{error}</p>}
    {success && <p role="status" className="notice">{success}</p>}
    {loading && <p role="status">正在更新庫存與申請紀錄…</p>}
    <form onSubmit={handleSubmit}>
      <fieldset disabled={busy || loading || !ready || uncertain}>
        <label>批次與儲位<select required value={selectedKey} onChange={(event) => { setSelectedKey(event.target.value); setAmount(''); setError(''); setSuccess(''); }}>
          <option value="">請選擇批次與儲位</option>
          {balances.map((row) => <option key={keyOf(row)} value={keyOf(row)}>
            {row.product_name}／{row.lot_code}／{row.location_code}：{row.qty} {row.unit}{row.has_pending ? '（待審凍結）' : ''}
          </option>)}
        </select></label>
        {ready && balances.length === 0 && <p>目前沒有可申請的批次與儲位庫存。</p>}
        {selected && <p className="notice">帳面餘量：{selected.qty} {selected.unit}{selected.has_pending && '（已有待審申請）'}</p>}
        <label>申請種類<select value={kind} onChange={(event) => { setKind(event.target.value as 'COUNT' | 'SCRAP'); setAmount(''); setError(''); }}>
          <option value="COUNT">盤點：填現場實數</option>
          <option value="SCRAP">損耗：填報廢量</option>
        </select></label>
        <label>{kind === 'COUNT' ? '現場實數' : '報廢量'}
          <input type="number" inputMode="numeric" required min={kind === 'COUNT' ? '0' : '1'} step="1"
            max={kind === 'SCRAP' ? selected?.qty : undefined} value={amount} onChange={(event) => setAmount(event.target.value)} />
        </label>
        <label>原因（必填，最多 500 字）<textarea required maxLength={500} rows={3} value={reason} onChange={(event) => setReason(event.target.value)} /></label>
        <button type="submit" disabled={!selected || selected.has_pending || (kind === 'SCRAP' && selected.qty === 0)}>{busy ? '送件處理中…' : '送出待審申請'}</button>
      </fieldset>
    </form>
    <div className="adjustment-controls">
      <button type="button" className="secondary" disabled={busy || loading} onClick={() => void refresh()}>查詢我的申請／更新餘量</button>
      {uncertain && <><p role="alert">請核對最近的批次、儲位、種類、數量與時間；查不到紀錄也不能代表送件失敗。</p>
        <button type="button" disabled={!ready || loading || busy} onClick={() => { setUncertain(false); setAmount(''); setReason(''); setError(''); }}>我已核對紀錄，開始新的申請</button></>}
    </div>
    <h3>我的最近申請（最多 100 筆）</h3>
    {ready && records.length === 0 && <p>目前沒有申請紀錄。</p>}
    <div className="adjustment-records">{records.map((record) => <article key={record.id}>
      <strong>#{record.id} {record.kind === 'COUNT' ? '盤點' : '報廢'}／{statusLabel[record.status]}</strong>
      <span>{record.product_name}／{record.lot_code}／{record.location_code}</span>
      <span>原數 {record.original_qty} {record.unit}；{record.kind === 'COUNT' ? `實數 ${record.observed_qty}` : `報廢 ${record.damaged_qty}`} {record.unit}</span>
      <span>原因：{record.reason}</span>
      <span>{new Date(record.created_at).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false })}（臺灣時間）</span>
    </article>)}</div>
  </section>;
}
