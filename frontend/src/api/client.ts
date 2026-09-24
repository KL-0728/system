export class ApiError extends Error {
  constructor(message: string, public readonly status: number) { super(message); }
}
export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, { ...options, credentials: 'same-origin', headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new ApiError(body?.detail ?? '伺服器處理失敗', response.status);
  }
  return response.json() as Promise<T>;
}
