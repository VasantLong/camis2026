export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  contact_phone?: string | null;
  permissions: string[];
  roles: string[];
  role_permissions: Record<string, string[]>;
  pending_role_request?: {
    id: string;
    role_id: string;
    role_name: string;
    status: string;
    created_at: string;
  } | null;
}
