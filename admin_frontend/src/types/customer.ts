export type CustomerStatus = 1 | 2 | 3;

export interface CustomerAddress {
  street?: string;
  city?: string;
  state?: string;
  country?: string;
  zipCode?: string;
}

export interface CustomerDto {
  id: string;
  name?: string;
  full_name?: string;
  email: string;
  phone?: string | null;
  role?: string;
  is_active?: boolean;
  created_at?: string;
  last_login?: string | null;
  company?: string;
  avatar?: string;
  status?: CustomerStatus;
  totalOrders?: number;
  totalSpent?: number;
  address?: CustomerAddress;
}
