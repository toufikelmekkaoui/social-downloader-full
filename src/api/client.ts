// src/api/client.ts

const getBaseURL = (): string => {
  if (import.meta.env.PROD) {
    return ""; // في الـ Production كيقرا من نفس الدومين تلقائياً
  }
  return import.meta.env.VITE_API_URL || "http://localhost:5000"; // في الـ Dev
};

const BASE_URL = getBaseURL();

interface RequestOptions extends RequestInit {
  data?: unknown;
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { data, ...fetchOptions } = options;
  const url = `${BASE_URL}${endpoint}`;
  
  const config: RequestInit = {
    ...fetchOptions,
    headers: {
      "Content-Type": "application/json",
      ...fetchOptions.headers,
    },
    body: data ? JSON.stringify(data) : fetchOptions.body,
  };

  try {
    const response = await fetch(url, config);
    if (response.status === 204) {
      return {} as T;
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        message: `HTTP Error: ${response.status}`,
      }));
      throw new Error(errorData.message || `HTTP Error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message === "Failed to fetch") {
      throw new Error("لا يمكن الاتصال بالسيرفر. تحقق من الاتصال.");
    }
    throw error;
  }
}

export const api = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { method: "GET", ...options }),

  post: <T>(endpoint: string, data: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { method: "POST", data, ...options }),

  put: <T>(endpoint: string, data: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { method: "PUT", data, ...options }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { method: "DELETE", ...options }),
};

export default api;