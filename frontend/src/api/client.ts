import { ApiResponse, CustomApiError, ApiErrorResponse } from '../types/api';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/+$/, '');

let authToken: string | null = null;
let onUnauthenticatedCallback: (() => void) | null = null;

export function setClientToken(token: string | null) {
  authToken = token;
}

export function getClientToken(): string | null {
  return authToken;
}

export function setOnUnauthenticated(callback: () => void) {
  onUnauthenticatedCallback = callback;
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined | null>;
  idempotencyKey?: string;
}

export async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
  const { params, idempotencyKey, headers: customHeaders, ...restOptions } = options;

  let url = `${API_BASE}${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  const headers: Record<string, string> = {
    'Accept': 'application/json',
    ...(customHeaders as Record<string, string>),
  };

  if (!(restOptions.body instanceof FormData) && restOptions.method && restOptions.method !== 'GET') {
    headers['Content-Type'] = 'application/json';
  }

  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey;
  }

  const response = await fetch(url, {
    ...restOptions,
    headers,
  });

  if (response.status === 204) {
    const requestId = response.headers.get('x-request-id') || '';
    return {
      data: {} as T,
      meta: { requestId },
    };
  }

  let jsonResult: any = null;
  try {
    jsonResult = await response.json();
  } catch (err) {
    throw new CustomApiError(
      response.status,
      {
        code: 'NETWORK_OR_PARSING_ERROR',
        message: 'Không thể giải mã dữ liệu từ server.',
      },
      response.headers.get('x-request-id') || undefined
    );
  }

  if (!response.ok) {
    const errorResponse = jsonResult as ApiErrorResponse;
    const errorBody = errorResponse?.error || {
      code: `HTTP_${response.status}`,
      message: response.statusText || 'Lỗi không xác định',
    };

    if (response.status === 401 && onUnauthenticatedCallback) {
      onUnauthenticatedCallback();
    }

    throw new CustomApiError(
      response.status,
      errorBody,
      errorResponse?.meta?.requestId || response.headers.get('x-request-id') || undefined
    );
  }

  return jsonResult as ApiResponse<T>;
}
