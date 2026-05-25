export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  display_name?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  username: string;
  email: string;
  display_name: string | null;
  is_active: boolean;
  permissions: string[];
  roles: string[];
  pending_role_request?: {
    id: string;
    role_id: string;
    role_name: string;
    status: string;
    created_at: string;
  } | null;
}
