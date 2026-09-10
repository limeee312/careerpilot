export type CurrentUser = {
  id: string;
  email: string;
  name: string | null;
};

type ErrorEnvelope = {
  error?: {
    code?: string;
    message?: string;
  };
};

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const browserApiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${browserApiBaseUrl}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError(
      "NETWORK_ERROR",
      "暂时无法连接服务，请稍后重试。",
      0,
    );
  }

  if (!response.ok) {
    const payload = (await response
      .json()
      .catch(() => null)) as ErrorEnvelope | null;
    throw new ApiError(
      payload?.error?.code ?? "UNKNOWN_ERROR",
      payload?.error?.message ?? "请求失败，请稍后重试。",
      response.status,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
