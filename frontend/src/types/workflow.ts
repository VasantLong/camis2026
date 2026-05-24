export interface StatusTransition {
  to_status: string;
  comment?: string;
}

export interface RejectRequest {
  reason: string;
}

export interface ForceChangeRequest {
  reason: string;
}
