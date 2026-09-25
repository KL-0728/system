import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ApiError } from '../api/client';
import { getBalanceOptions, getStockLocationOptions } from '../api/stockOptions';
import { getTransferRecords, submitTransfer, type TransferRecord } from '../api/transfer';
import type { BalanceOption, StockLocationOption } from '../types/stock';

const keyOf = (row: BalanceOption) => `${row.lot_id}:${row.location_id}`;

export default function TransferPage({ refreshKey = 0, onStockChanged }: {
  refreshKey?: number; onStockChanged?: () => void;
}) {
  const [balances, setBalances] = useState<BalanceOption[]>([]);
  const [locations, setLocations] = useState<StockLocationOption[]>([]);
  const [records, setRecords] = useState<TransferRecord[]>([]);
  const [sourceKey, setSourceKey] = useState('');
  const [targetId, setTargetId] = useState('');
  const [qty, setQty] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [uncertain, setUncertain] = useState(false);
  const inFlight = useRef(false);
  const source = balances.find((row) => keyOf(row) === sourceKey);
  const target = locations.find((row) => row.location_id === Number(targetId));
  const targetBalance = balances.find((row) => row.lot_id === source?.lot_id && row.location_id === Number(targetId));
  const lotBalances = balances.filter((row) => row.lot_id === source?.lot_id);
  const sameLocation = source?.location_id === target?.location_id && !!source;

  async function refresh() {
    setLoading(true); setReady(false);
    try {
      const [nextBalances, nextLocations, nextRecords] = await Promise.all([
        getBalanceOptions({ positiveOnly: false }), getStockLocationOptions(), getTransferRecords(),
      ]);
      setBalances(nextBalances); setLocations(nextLocations); setRecords(nextRecords);
      setReady(true); setError('');
    } catch { setError('無法更新移位資料，請確認連線後再查詢。'); }
    finally { setLoading(false); }
  }

  useEffect(() => { void refresh(); }, [refreshKey]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current || loading || !ready || uncertain) return;
    setError(''); setSuccess('');
    const amount = Number(qty);
    if (!source || !target || !Number.isSafeInteger(amount) || amount <= 0) {
      setError('請選擇來源、目標，並輸入正整數數量。'); return;
    }
    if (sameLocation) { setError('來源與目標儲位不可相同。'); return; }
    if (source.has_pending || targetBalance?.has_pending) {
      setError('來源或目標的同批次庫存有待審申請，暫停移位。'); return;
    }
    if (amount > source.qty) { setError('移位數量不可超過來源餘量。'); return; }
    inFlight.current = true; setBusy(true);
    try {
      const result = await submitTransfer({
        lot_id: source.lot_id, from_location_id: source.location_id,
        to_location_id: target.location_id, qty: amount,
      });
      setSuccess(`${source.product_name}／${source.lot_code} 移位 ${amount} ${source.unit}成功：${source.location_code} 剩 ${result.from_qty} ${source.unit}，${target.location_code} 有 ${result.to_qty} ${source.unit}；異動編號 #${result.movement_id}。`);
      setQty('');
      onStockChanged?.();
      await refresh();
    } catch (failure) {
      if (failure instanceof ApiError && [401, 403, 409, 422].includes(failure.status)) {
        setError(failure.status === 422 ? '欄位格式不正確，數量必須是正整數。' : failure.message);
      } else {
        setUncertain(true); setReady(false);
        setError('結果未確認，請查詢移位紀錄；請勿直接重送。');
      }
    } finally { inFlight.current = false; setBusy(false); }
  }

  return <section className="card transfer-panel" aria-labelledby="transfer-title">
    <h2 id="transfer-title">移位</h2>
    <p className="hint">選擇同批貨物的來源與目標。移位只改變位置，總量不變。</p>
    {error && <p role="alert" className="error">{error}</p>}
    {success && <p role="status" className="notice">{success}</p>}
    {loading && <p role="status">正在更新移位資料…</p>}
    <form onSubmit={handleSubmit}>
      <fieldset disabled={busy || loading || !ready || uncertain}>
        <label>移位來源（批次與儲位）<select required value={sourceKey} onChange={(event) => {
          setSourceKey(event.target.value); setTargetId(''); setQty(''); setSuccess(''); setError('');
        }}>
          <option value="">請選擇來源</option>
          {balances.map((row) => <option key={keyOf(row)} value={keyOf(row)}>
            {row.product_name}／{row.lot_code}／{row.location_code}：{row.qty} {row.unit}{row.has_pending ? '（待審凍結）' : ''}
          </option>)}
        </select></label>
        {ready && !balances.some((row) => row.qty > 0) && <p>目前沒有可移位的正餘量庫存。</p>}
        <label>目標儲位<select required value={targetId} onChange={(event) => { setTargetId(event.target.value); setSuccess(''); }}>
          <option value="">請選擇啟用儲位</option>
          {locations.map((location) => {
            const pending = balances.some((row) => row.lot_id === source?.lot_id && row.location_id === location.location_id && row.has_pending);
            return <option key={location.location_id} value={location.location_id}>{location.location_code}{pending ? '（同批待審凍結）' : ''}</option>;
          })}
        </select></label>
        {source && <p>來源：{source.qty} {source.unit}{source.has_pending && '（待審凍結）'}；目標同批：{targetBalance?.qty ?? 0} {source.unit}{targetBalance?.has_pending && '（待審凍結）'}</p>}
        {sameLocation && <p className="field-error">來源與目標儲位不可相同。</p>}
        {(source?.has_pending || targetBalance?.has_pending) && <p className="field-error">來源或目標的同批次庫存待審，不能移位。</p>}
        <label>移位數量<input type="number" inputMode="numeric" required min="1" step="1" max={source?.qty} value={qty} onChange={(event) => setQty(event.target.value)} /></label>
        <button type="submit" disabled={!source || !target || sameLocation || source.qty === 0 || source.has_pending || targetBalance?.has_pending}>{busy ? '移位處理中…' : '確認移位'}</button>
      </fieldset>
    </form>
    <div className="transfer-controls">
      <button className="secondary" type="button" disabled={busy || loading} onClick={() => void refresh()}>查詢移位紀錄／更新餘量</button>
      {uncertain && <><p role="alert">上次移位結果未確認。核對批次、來源、目標、數量、時間及操作者，確認伺服器已處理完畢後再決定是否重新操作；查不到紀錄不代表未成功。</p>
        <button type="button" disabled={!ready || loading || busy} onClick={() => { setUncertain(false); setQty(''); setError(''); }}>我已核對移位紀錄，開始新的操作</button></>}
    </div>
    {source && <div className="transfer-balances">
      <h3>同批次各處餘量</h3>
      <p className="transfer-total">合計：{lotBalances.reduce((sum, row) => sum + row.qty, 0)} {source.unit}</p>
      {lotBalances.map((row) => <article key={keyOf(row)}>{row.location_code}：{row.qty} {row.unit}{row.has_pending && '（待審凍結）'}</article>)}
    </div>}
    <h3>最近移位紀錄（最多 100 筆）</h3>
    {ready && records.length === 0 && <p>目前沒有移位紀錄。</p>}
    <div className="transfer-records">{records.map((record) => <article key={record.movement_id}>
      <strong>#{record.movement_id} {record.product_name}：移位 {record.qty} {record.unit}</strong>
      <span>{record.lot_code}／{record.from_location_code} → {record.to_location_code}</span>
      <span>{new Date(record.created_at).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false })}（臺灣時間）／{record.actor_name}</span>
    </article>)}</div>
  </section>;
}
