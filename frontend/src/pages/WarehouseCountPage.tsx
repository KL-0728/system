import { useEffect, useRef, useState, type FormEvent } from 'react';
import { getWarehouses } from '../api/masterData';
import { ApiError } from '../api/client';
import {
  cancelWarehouseCount, checkWarehouseCountItem, completeWarehouseCount,
  listWarehouseCounts, reopenWarehouseCountItem, startWarehouseCount, type CountItem, type CountSession,
} from '../api/warehouseCounts';
import type { Warehouse } from '../types/masterData';

function loadErrorMessage(failure: unknown): string {
  if (failure instanceof ApiError) {
    if (failure.status === 404) return '目前後端尚未提供整庫盤點 API。請停止舊後端、啟動最新版後端，並重新整理網頁。';
    if (failure.status === 500) return '後端讀取盤點資料失敗。請檢查資料庫是否已執行維護遷移，再查看後端視窗的錯誤。';
    return `盤點資料讀取失敗（HTTP ${failure.status}）：${failure.message}`;
  }
  return '無法連線或讀取盤點資料，請檢查後端是否正在執行，再按「重新讀取盤點進度」。';
}

function CountRow({ item, countId, busy, isOpen, onSaved }: {
  item: CountItem; countId: number; busy: boolean; isOpen: boolean; onSaved: (result: CountSession) => void;
}) {
  const [observed, setObserved] = useState(String(item.original_qty));
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const inFlight = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current || busy) return;
    const qty = Number(observed);
    if (!Number.isSafeInteger(qty) || qty < 0 || (item.lot_id === null && qty !== 0)) {
      setError('請輸入非負整數；空儲位如發現未登錄貨物，請通知管理者確認批次。'); return;
    }
    if (qty !== item.original_qty && !note.trim()) { setError('有盤差時請填原因。'); return; }
    inFlight.current = true; setSaving(true); setError('');
    try { onSaved(await checkWarehouseCountItem(countId, item.id, qty, note.trim())); }
    catch (failure) { setError(failure instanceof ApiError ? failure.message : '結果不明，請更新盤點後核對，勿直接重送。'); }
    finally { inFlight.current = false; setSaving(false); }
  }
  async function reopen() {
    if (inFlight.current || busy || !isOpen) return;
    inFlight.current = true; setSaving(true); setError('');
    try { onSaved(await reopenWarehouseCountItem(countId, item.id)); }
    catch (failure) { setError(failure instanceof ApiError ? failure.message : '結果不明，請重新讀取盤點進度後核對。'); }
    finally { inFlight.current = false; setSaving(false); }
  }
  return <article className="count-item">
    <strong>{item.location_code}｜{item.product_name ?? '空儲位'}</strong>
    <span>{item.lot_code ?? '無批次'}｜帳面 {item.original_qty} {item.unit ?? ''}</span>
    {item.checked_at ? <><p className="notice">已確認：實數 {item.observed_qty} {item.unit ?? ''}{item.adjustment_request_id && `；盤差申請 #${item.adjustment_request_id} ${item.adjustment_status === 'APPROVED' ? '已核准' : item.adjustment_status === 'REJECTED' ? '已駁回' : '待管理者審核'}`}</p>
      {isOpen && !item.adjustment_request_id && <button type="button" className="secondary" disabled={busy || saving} onClick={() => void reopen()}>{saving ? '處理中…' : '重新核對這一格'}</button>}</> : <form onSubmit={submit}>
      <label>現場實數<input type="number" inputMode="numeric" min="0" step="1" required disabled={busy || saving} value={observed} onChange={(event) => setObserved(event.target.value)} /></label>
      <label>差異原因（數量相同可不填）<input maxLength={500} disabled={busy || saving} value={note} onChange={(event) => setNote(event.target.value)} /></label>
      <button type="submit" disabled={busy || saving}>{saving ? '登錄中…' : '確認這一格'}</button>
    </form>}
    {error && <p role="alert" className="error">{error}</p>}
  </article>;
}

export default function WarehouseCountPage() {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [sessions, setSessions] = useState<CountSession[]>([]);
  const [warehouseId, setWarehouseId] = useState('');
  const [session, setSession] = useState<CountSession | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const inFlight = useRef(false);

  function acceptSession(result: CountSession) {
    setSession(result);
    setSessions((current) => [result, ...current.filter((row) => row.id !== result.id)].slice(0, 20));
  }

  async function refresh() {
    setLoading(true);
    try {
      const [nextWarehouses, nextSessions] = await Promise.all([getWarehouses(), listWarehouseCounts()]);
      setWarehouses(nextWarehouses); setSessions(nextSessions);
      setSession((current) => nextSessions.find((row) => row.id === current?.id) ?? nextSessions.find((row) => row.status === 'OPEN') ?? null);
      setError('');
    } catch (failure) { setError(loadErrorMessage(failure)); }
    finally { setLoading(false); }
  }
  useEffect(() => { void refresh(); }, []);
  async function action(work: () => Promise<CountSession>, success: string) {
    if (inFlight.current) return;
    inFlight.current = true; setBusy(true); setError(''); setNotice('');
    try {
      const result = await work(); acceptSession(result); setNotice(success);
    } catch (failure) {
      setError(failure instanceof ApiError && failure.status !== 0
        ? `盤點操作未完成（HTTP ${failure.status}）：${failure.message}`
        : '操作結果不明，請先按「重新讀取盤點進度」核對，勿直接重送。');
    } finally { inFlight.current = false; setBusy(false); }
  }
  const checked = session?.items.filter((item) => item.checked_at).length ?? 0;
  const total = session?.items.length ?? 0;
  const pending = session?.items.filter((item) => item.adjustment_status === 'PENDING').length ?? 0;
  return <section className="card count-panel" aria-labelledby="count-title">
    <h2 id="count-title">整庫盤點</h2>
    <p className="hint">先選倉庫，再逐格核對實物。數量相符只記錄確認，不需審核；現場實數與帳面不同時，填原因後才會建立待審盤差申請，由管理者在「審核申請」處理。腐爛品請在盤點完成後另用「盤點／損耗」申請報廢。</p>
    {error && <p role="alert" className="error">{error}</p>}
    {notice && <p role="status" className="notice">{notice}</p>}
    <button type="button" className="secondary" disabled={loading || busy} onClick={() => void refresh()}>重新讀取盤點進度</button>
    <p className="hint">只重新讀取各格完成狀態，不會再送出一次盤點。</p>
    <div className="count-start">
      <label>選擇倉庫<select value={warehouseId} disabled={busy || loading} onChange={(event) => setWarehouseId(event.target.value)}>
        <option value="">請選擇倉庫</option>{warehouses.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
      </select></label>
      <button type="button" disabled={!warehouseId || busy || loading} onClick={() => void action(() => startWarehouseCount(Number(warehouseId)), '已建立或接續這座倉庫的盤點。')}>開始／接續盤點</button>
    </div>
    {sessions.length > 0 && <label>查看最近盤點<select value={session?.id ?? ''} onChange={(event) => setSession(sessions.find((row) => row.id === Number(event.target.value)) ?? null)}>
      <option value="">請選擇</option>{sessions.map((row) => <option key={row.id} value={row.id}>#{row.id} {row.warehouse_name}／{row.status === 'OPEN' ? '進行中' : row.status === 'COMPLETE' ? '已完成' : '已取消'}</option>)}
    </select></label>}
    {session && <div className="count-session">
      <h3>{session.warehouse_name}｜{session.status === 'OPEN' ? '進行中' : session.status === 'COMPLETE' ? '已完成' : '已取消'}</h3>
      <p className="notice">進度 {checked}/{total} 格；盤差待審申請 {pending} 筆。{pending > 0 ? '這些申請須由管理者另外審核，完成整庫盤點不會自動核准。' : '目前沒有需要審核的盤差。'}</p>
      {session.status === 'OPEN' && <div className="button-row">
        <button type="button" disabled={busy || checked !== total} onClick={() => void action(() => completeWarehouseCount(session.id), pending > 0 ? `整庫盤點已完成；另有 ${pending} 筆待審盤差，請管理者至「審核申請」處理。` : '整庫盤點已完成；目前沒有待審盤差，無須審核。')}>完成整庫盤點</button>
        <button type="button" className="secondary" disabled={busy} onClick={() => void action(() => cancelWarehouseCount(session.id), '盤點已取消；已送出的盤差申請仍保留，請至審核頁處理。')}>取消本次盤點</button>
      </div>}
      <div className="count-items">{session.items.map((item) => <CountRow key={item.id} item={item} countId={session.id} isOpen={session.status === 'OPEN'} busy={busy || session.status !== 'OPEN'} onSaved={(result) => { acceptSession(result); setNotice('盤點進度已更新，請核對剩餘項目。'); }} />)}</div>
    </div>}
  </section>;
}
