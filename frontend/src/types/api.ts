export interface ApiResponse<T> {
  data: T;
  meta: ResponseMeta;
}

export interface ResponseMeta {
  requestId: string;
  page?: number;
  pageSize?: number;
  total?: number;
  totalPages?: number;
}

export interface PaginationMeta {
  requestId?: string;
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export interface ApiErrorDetail {
  field?: string;
  reason: string;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: ApiErrorDetail[];
}

export interface ApiErrorResponse {
  error: ApiErrorBody;
  meta: {
    requestId: string;
  };
}

export class CustomApiError extends Error {
  code: string;
  details: ApiErrorDetail[];
  requestId?: string;
  status: number;

  constructor(status: number, errorBody: ApiErrorBody, requestId?: string) {
    super(errorBody.message || 'Lỗi hệ thống');
    this.name = 'CustomApiError';
    this.status = status;
    this.code = errorBody.code || 'UNKNOWN_ERROR';
    this.details = errorBody.details || [];
    this.requestId = requestId;
  }
}
