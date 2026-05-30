export interface ActivityCreate {
  name: string;
  type: string;
  estimated_time: string;
  location: string;
  sponsor: string;
  sponsor_contact: string;
  sponsor_phone: string;
  deadline: string;
  designer_id?: string;
}

export interface ActivityResponse {
  id: string;
  name: string;
  type: string;
  estimated_time: string;
  location: string;
  sponsor: string;
  sponsor_contact?: string | null;
  sponsor_phone?: string | null;
  deadline: string;
  status: string;
  owner_id: string;
  designer_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ActivityPaginatedResponse {
  items: ActivityResponse[];
  total: number;
}

export interface ActivityListParams {
  status?: string;
  keyword?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  size?: number;
  tab?: string;
}

export interface StatusLogEntry {
  id: string;
  from_status: string | null;
  to_status: string;
  operator_id: string;
  comment: string | null;
  created_at: string;
}
