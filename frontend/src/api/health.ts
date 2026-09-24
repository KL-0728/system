import type { HealthResponse } from '../types/health';

export async function getHealth(signal: AbortSignal): Promise<HealthResponse> {
  const response = await fetch('/api/health', { signal });
  if (!response.ok) throw new Error('健康檢查失敗');
  const data: unknown = await response.json();
  if (typeof data !== 'object' || data === null ||
      !('status' in data) || data.status !== 'ok') {
    throw new Error('健康檢查回應不符預期');
  }
  return { status: 'ok' };
}
