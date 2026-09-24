import { apiRequest } from './client';
import type { CurrentUser } from '../types/auth';
export function login(username: string, password: string) { return apiRequest<CurrentUser>('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }); }
export function logout() { return apiRequest<{ message: string }>('/api/auth/logout', { method: 'POST' }); }
export function getCurrentUser() { return apiRequest<CurrentUser>('/api/auth/me'); }
