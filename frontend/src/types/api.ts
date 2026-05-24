export interface ApiErrorResponse {
  detail: string;
  code: string;
  fields?: Record<string, string>;
}
