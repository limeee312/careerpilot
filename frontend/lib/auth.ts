import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import type { CurrentUser } from "@/lib/api";

type CurrentUserEnvelope = {
  data: CurrentUser;
};

const serverApiBaseUrl =
  process.env.API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000/api/v1";

export async function requireCurrentUser(): Promise<CurrentUser> {
  const cookieHeader = (await cookies()).toString();

  if (!cookieHeader) {
    redirect("/login");
  }

  let response: Response;

  try {
    response = await fetch(`${serverApiBaseUrl}/auth/me`, {
      cache: "no-store",
      headers: { cookie: cookieHeader },
    });
  } catch {
    throw new Error("认证服务暂时不可用");
  }

  if (response.status === 401) {
    redirect("/login");
  }

  if (!response.ok) {
    throw new Error(`认证服务返回异常状态：${response.status}`);
  }

  const payload = (await response.json()) as CurrentUserEnvelope;
  return payload.data;
}
