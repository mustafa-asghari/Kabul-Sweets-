export interface IApiError {
  code?: string;
  message: string;
  details?: unknown;
}

export interface IApiResponse<T> {
  succeeded: boolean;
  message: string;
  timestamp: string;
  statusCode?: number;
  data?: T;
  errors?: IApiError[];
}

// Alias for compatibility
export type ApiResponse<T> = IApiResponse<T>;
