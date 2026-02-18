export interface UserResponse {
  id: string;
  email: string;
  name?: string;
  full_name: string;
  avatar?: string;
  phone: string | null;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login: string | null;
}

export interface UserCreateAdmin {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
  role?: string;
}

export interface UserUpdate {
  full_name?: string;
  phone?: string;
}
