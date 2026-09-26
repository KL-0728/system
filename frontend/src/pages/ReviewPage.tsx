import { useEffect, useRef, useState } from 'react';
import BackToTop from '../components/BackToTop';
import QuickJump from '../components/QuickJump';
import {
  getAdjustmentDetail, getPendingAdjustments, getReviewedAdjustments, reviewAdjustment,
  type AdjustmentDetail,
} from '../api/adjustments';
import { ApiError } from '../api/client';

const timeText = (value: string) => new Date(value).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false });

export default function ReviewPage() {
  const [pending, setPending] = useState<AdjustmentDetail[]>([]);
  const [reviewed, setReviewed] = useState<AdjustmentDetail[]>([]);
  const [selected, setSelected] = useState<AdjustmentDetail | null>(null);
  const [reviewNote, setReviewNote] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const inFlight = useRef(false);

  async function refresh() {
    setLoading(true);
    try {
      const [pendingRows, reviewedRows] = await Promise.all([getPendingAdjustments(), getReviewedAdjustments()]);
      setPending(pendingRows); setReviewed(reviewedRows);
      if (selected) setSelected(await getAdjustmentDetail(selected.id));
      setError('');
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : '無法更新申請，請確認連線。');
    } finally { setLoading(false); }
  }

  useEffect(() => { void refresh(); }, []);

  async function choose(id: number) {
    if (busy || loading) return;
    setLoading(true); setError(''); setSuccess(''); setReviewNote('');
    try {
      setSelected(await getAdjustmentDetail(id));
      requestAnimationFrame(() => document.getElementById('review-detail-title')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    }
    catch (failure) { setError(failure instanceof ApiError ? failure.message : '無法讀取申請詳情。'); }
    finally { setLoading(false); }
  }

  async function submit(action: 'APPROVE' | 'REJECT') {
    if (!selected || selected.status !== 'PENDING' || inFlight.current || busy || loading || uncertain) return;
    if (action === 'REJECT' && !reviewNote.trim()) { setError('駁回必須填寫原因。'); return; }
    inFlight.current = true; setBusy(true); setError(''); setSuccess('');
    try {
      const result = await reviewAdjustment(selected.id, action, reviewNote.trim());
      setSuccess(result.status === 'APPROVED'
        ? `申請 #${result.request_id} 已核准，餘量 ${result.new_qty} ${selected.unit}${result.movement_id ? `；異動編號 #${result.movement_id}` : '；差額為 0，沒有新增異動'}。`
        : `申請 #${result.request_id} 已駁回，餘量仍為 ${result.new_qty} ${selected.unit}。`);
      setReviewNote('');
      try {
        const [detail, pendingRows, reviewedRows] = await Promise.all([
          getAdjustmentDetail(selected.id), getPendingAdjustments(), getReviewedAdjustments(),
        ]);
        setSelected(detail); setPending(pendingRows); setReviewed(reviewedRows);
      } catch { setError('審核已完成，但清單更新失敗；請按「更新申請與詳情」再查詢。'); }
    } catch (failure) {
      if (failure instanceof ApiError && [401, 403, 404, 409, 422].includes(failure.status)) {
        setError(failure.message);
      } else {
        setUncertain(true);
        setError('審核結果未確認。請查詢詳情與庫存異動，確認後再決定是否操作；不要直接重送。');
      }
    } finally { inFlight.current = false; setBusy(false); }
  }

  return <main className="app-shell review-page">
    <p className="eyebrow">管理者審核</p><h1>盤點與損耗審核</h1>
    <QuickJump items={[{ id: 'review-pending', label: '待審申請' }, { id: 'review-reviewed', label: '已審核紀錄' }]} />
    <p className="hint">核對申請原數、現場實數或報廢量，以及送件原因後再決定。核准才會更新餘量。</p>
    {error && <p role="alert" className="error">{error}</p>}
    {success && <p role="status" className="notice">{success}</p>}
    {loading && <p role="status">正在讀取申請…</p>}
    <button className="secondary" type="button" disabled={busy || loading} onClick={() => void refresh()}>更新申請與詳情</button>
    {uncertain && <div className="card"><p role="alert">上次審核結果未確認。請核對此筆狀態、異動紀錄和庫存餘量；查詢暫時沒有結果也不能代表操作失敗。</p>
      <button type="button" disabled={busy || loading || !selected} onClick={() => { setUncertain(false); setError(''); }}>我已核對結果，開始新的審核</button></div>}
    <section id="review-pending" className="card jump-target" aria-labelledby="pending-title">
      <h2 id="pending-title">待審申請</h2>
      {!loading && pending.length === 0 && <p>目前沒有待審申請。</p>}
      <div className="review-list">{pending.map((record) => <article key={record.id}>
        <strong>#{record.id} {record.kind === 'COUNT' ? '盤點' : '報廢'}：{record.product_name}</strong>
        <span>{record.lot_code}／{record.location_code}；送件人 {record.requester_name}</span>
        <span>原數 {record.original_qty} {record.unit}；{record.kind === 'COUNT' ? `實數 ${record.observed_qty}` : `報廢 ${record.damaged_qty}`} {record.unit}；差額 {record.difference > 0 ? '+' : ''}{record.difference} {record.unit}</span>
        <button type="button" className="secondary" disabled={busy || loading} onClick={() => void choose(record.id)}>查看詳情與審核</button>
      </article>)}</div>
    </section>
    {selected && <section className="card" aria-labelledby="review-detail-title">
      <h2 id="review-detail-title">申請 #{selected.id} 詳情</h2>
      <div className="review-detail">
        <p><strong>狀態：</strong>{selected.status === 'PENDING' ? '待審' : selected.status === 'APPROVED' ? '已核准' : '已駁回'}</p>
        <p><strong>品項／批次／儲位：</strong>{selected.product_name}／{selected.lot_code}／{selected.location_code}</p>
        <p><strong>原數：</strong>{selected.original_qty} {selected.unit}　<strong>目前餘量：</strong>{selected.current_qty} {selected.unit}</p>
        <p><strong>{selected.kind === 'COUNT' ? '現場實數' : '報廢量'}：</strong>{selected.kind === 'COUNT' ? selected.observed_qty : selected.damaged_qty} {selected.unit}　<strong>預計差額：</strong>{selected.difference > 0 ? '+' : ''}{selected.difference} {selected.unit}</p>
        <p><strong>送件人／時間：</strong>{selected.requester_name}／{timeText(selected.created_at)}（臺灣時間）</p>
        <p><strong>送件原因：</strong>{selected.reason}</p>
        {selected.reviewed_at && <p><strong>審核人／時間：</strong>{selected.reviewer_name}／{timeText(selected.reviewed_at)}（臺灣時間）</p>}
        {selected.review_note && <p><strong>審核備註：</strong>{selected.review_note}</p>}
        {selected.movement_id && <p><strong>異動編號：</strong>#{selected.movement_id}</p>}
      </div>
      {selected.status === 'PENDING' && <div className="review-actions">
        <label>審核備註（駁回必填，最多 500 字）<textarea rows={3} maxLength={500} disabled={busy || loading || uncertain} value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} /></label>
        <div className="button-row">
          <button type="button" disabled={busy || loading || uncertain} onClick={() => void submit('APPROVE')}>{busy ? '處理中…' : '核准申請'}</button>
          <button type="button" className="secondary" disabled={busy || loading || uncertain} onClick={() => void submit('REJECT')}>{busy ? '處理中…' : '駁回申請'}</button>
        </div>
      </div>}
    </section>}
    <section id="review-reviewed" className="card jump-target" aria-labelledby="reviewed-title">
      <h2 id="reviewed-title">最近已審核申請（最多 100 筆）</h2>
      {!loading && reviewed.length === 0 && <p>目前沒有已審核申請。</p>}
      <div className="review-list">{reviewed.map((record) => <article key={record.id}>
        <strong>#{record.id} {record.kind === 'COUNT' ? '盤點' : '報廢'}／{record.status === 'APPROVED' ? '已核准' : '已駁回'}：{record.product_name}</strong>
        <span>{record.lot_code}／{record.location_code}；送件人 {record.requester_name}</span>
        <span>原數 {record.original_qty} {record.unit}；{record.kind === 'COUNT' ? `實數 ${record.observed_qty}` : `報廢 ${record.damaged_qty}`} {record.unit}</span>
        {record.reviewed_at && <span>審核人 {record.reviewer_name}／{timeText(record.reviewed_at)}（臺灣時間）</span>}
        {record.review_note && <span>{record.status === 'REJECTED' ? '駁回原因' : '審核備註'}：{record.review_note}</span>}
        <button type="button" className="secondary" disabled={busy || loading} onClick={() => void choose(record.id)}>查看詳情</button>
      </article>)}</div>
    </section>
    <BackToTop />
  </main>;
}
