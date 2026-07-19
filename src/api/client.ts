// src/api/client.ts

const BASE_URL = import.meta.env.PROD
  ? ""
  : import.meta.env.VITE_API_URL || "http://localhost:5000";

/* =========================
   Types
========================= */

export interface VideoFormat {
  [key: string]: any;
}

export interface VideoInfo {
  [key: string]: any;
}

/* =========================
   API Error
========================= */

export class ApiClientError extends Error {
  statusCode: number;
  status: number;
  data?: unknown;

  constructor(message: string, statusCode = 0, data?: unknown) {
    super(message);

    this.name = "ApiClientError";
    this.statusCode = statusCode;
    this.status = statusCode;
    this.data = data;

    Object.setPrototypeOf(this, ApiClientError.prototype);
  }
}

/* =========================
   Request
========================= */

interface RequestOptions extends RequestInit {
  data?: unknown;
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { data, ...fetchOptions } = options;

  const url = `${BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      headers: {
        "Content-Type": "application/json",
        ...fetchOptions.headers,
      },
      body:
        data !== undefined
          ? JSON.stringify(data)
          : fetchOptions.body,
    });

    if (response.status === 204) {
      return {} as T;
    }

    const responseData = await response.json().catch(() => null);

    if (!response.ok) {
      const message =
        responseData?.message ||
        responseData?.error ||
        `HTTP Error: ${response.status}`;

      throw new ApiClientError(
        message,
        response.status,
        responseData
      );
    }

    return responseData as T;
  } catch (error) {
    if (error instanceof ApiClientError) {
      throw error;
    }

    throw new ApiClientError(
      error instanceof Error
        ? error.message
        : "لا يمكن الاتصال بالسيرفر",
      0,
      error
    );
  }
}

/* =========================
   Generic API
========================= */

export const api = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: "GET",
    }),

  post: <T>(
    endpoint: string,
    data: unknown,
    options?: RequestOptions
  ) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: "POST",
      data,
    }),

  put: <T>(
    endpoint: string,
    data: unknown,
    options?: RequestOptions
  ) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: "PUT",
      data,
    }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: "DELETE",
    }),
};

/* =========================
   Video functions
========================= */

export const analyzeVideo = (
  url: string
): Promise<VideoInfo> => {
  return api.post<VideoInfo>("/api/analyze", { url });
};

export const downloadVideo = (
  ...args: any[]
): Promise<any> => {
  const [url, format] = args;

  return api.post<any>("/api/download", {
    url,
    format,
    format_id: format,
  });
};

export default api;