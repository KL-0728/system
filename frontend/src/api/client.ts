export class ApiError extends Error {
  constructor(message: string, public readonly status: number) { super(message); }
}
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
  const response = await fetch(path, { ...options, credentials: 'same-origin', headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: ErrorDetail } | null;
    throw new ApiError(errorMessage(body?.detail), response.status);
  }
  return response.json() as Promise<T>;
}
