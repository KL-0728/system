export class ApiError extends Error {
  constructor(message: string, public readonly status: number) { super(message); }
}
export const UNAUTHORIZED_EVENT = 'inventory:unauthorized';
export const REQUEST_TIMEOUT_MS = 15000;
type ErrorDetail = string | Array<{ loc?: Array<string | number>; msg?: string }>;

function errorMessage(detail: ErrorDetail | undefined): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      const field = item.loc?.at(-1);
      const labels: Record<string, string> = {
        name: '名稱', unit: '單位', min_qty: '最低量', target_qty: '目標量',
        warehouse_id: '冷凍庫', code: '儲位編號',
      };
      const label = field === undefined || field === 'body' ? '' : labels[String(field)] ?? String(field);
      const message = item.msg?.replace(/^Value error, /, '') ?? '欄位內容不正確';
      return label ? `${label}：${message}` : message;
    }).join('；');
  }
  return '伺服器處理失敗';
}
export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const abort = () => controller.abort();
  if (options.signal?.aborted) controller.abort();
  options.signal?.addEventListener('abort', abort, { once: true });
  let response: Response;
  try {
    response = await fetch(path, { ...options, signal: controller.signal, credentials: 'same-origin', headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers } });
  } catch (error) {
    if (controller.signal.aborted && !options.signal?.aborted) throw new ApiError('連線逾時，請確認結果後重試。', 0);
    throw error;
  } finally {
    window.clearTimeout(timeout);
    options.signal?.removeEventListener('abort', abort);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: ErrorDetail } | null;
    if (response.status === 401 && path !== '/api/auth/login') window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    throw new ApiError(errorMessage(body?.detail), response.status);
  }
  return response.json() as Promise<T>;
}
