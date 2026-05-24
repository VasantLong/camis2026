export interface AnomalyEntry {
  activity_id: string;
  name: string;
  change_status: string;
  change_reason: string | null;
  changed_at: string;
}

export interface PanelData {
  total: number;
  by_status: Record<string, number>;
  compliance_rate: number;
  recent_anomalies: AnomalyEntry[];
}

export interface ActivityDetail {
  activity: {
    id: string;
    name: string;
    type: string;
    estimated_time: string;
    location: string;
    sponsor: string;
    deadline: string;
    status: string;
    owner_id: string;
    created_at: string;
    updated_at: string;
  };
  status_history: Array<{
    id: string;
    from_status: string | null;
    to_status: string;
    operator_id: string;
    comment: string | null;
    created_at: string;
  }>;
}

export interface MonthlyReportRequest {
  month: string;
}
