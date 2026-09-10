"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";

export function LogoutButton() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogout() {
    setError(null);
    setIsSubmitting(true);

    try {
      await apiRequest<void>("/auth/logout", { method: "POST" });
      router.replace("/login");
      router.refresh();
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "登出失败，请重试。",
      );
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <button
        className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400"
        disabled={isSubmitting}
        onClick={handleLogout}
        type="button"
      >
        {isSubmitting ? "正在退出…" : "退出登录"}
      </button>
      {error ? (
        <span className="text-right text-xs text-red-600" role="alert">
          {error}
        </span>
      ) : null}
    </div>
  );
}
