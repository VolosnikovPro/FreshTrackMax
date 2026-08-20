export type UserRole = 'admin' | 'manager' | 'storekeeper' | 'nutrition_manager';

export interface User {
  id: number;
  username: string;
  display_name: string;
  role: UserRole;
  is_active: boolean;
  max_user_id: number;
}

export interface AuthState {
  user: User | null;
  token: string | null;
}

export interface Product {
  id: number;
  name: string;
  sku: string | null;
  unit: string;
  category: string | null;
  description: string | null;
  is_active: boolean;
}

export interface Batch {
  id: number;
  product_id: number;
  product_name: string;
  batch_number: string | null;
  quantity: number;
  unit: string;
  expiry_date: string;       // ISO date string
  received_date: string | null;
  days_until_expiry: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface RawMaterialCost {
  id: number;
  product_id: number;
  product_name: string;
  cost_per_unit: number;
  currency: string;
  effective_date: string;
  notes: string | null;
  created_at: string;
}

export interface DailyConsumption {
  id: number;
  product_id: number;
  product_name: string;
  date: string;
  quantity_used: number;
  unit: string;
  notes: string | null;
  created_at: string;
}

export interface DailyHeadcount {
  id: number;
  date: string;
  count: number;
  notes: string | null;
  created_at: string;
}

export interface AdminSummary {
  total_products: number;
  total_batches: number;
  expiring_soon_urgent: number;
  expiring_soon_planned: number;
  total_products_with_cost: number;
  today_headcount: number | null;
  today_consumption_entries: number;
}

export interface NotificationResult {
  sent: number;
  recipients: string[];
  products_included: number;
}
