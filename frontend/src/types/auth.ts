export type UserRole = 'ADMIN' | 'WORKER';
export interface CurrentUser { id: number; username: string; display_name: string; role: UserRole; }
