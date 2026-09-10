"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ApiError, apiRequest, type CurrentUser } from "@/lib/api";

type AuthFormProps = {
  mode: "login" | "register";
  successMessage?: string;
};

type CurrentUserEnvelope = {
  data: CurrentUser;
};

type RegisteredUserEnvelope = {
  data: Pick<CurrentUser, "id" | "email">;
};

const content = {
  login: {
    title: "欢迎回来",
    description: "登录后继续管理你的简历、岗位匹配和投递进度。",
    submit: "登录",
    pending: "正在登录…",
    alternate: "还没有账号？",
    alternateAction: "立即注册",
    alternateHref: "/register",
  },
  register: {
    title: "创建账号",
    description: "从一份结构化简历开始，让每次投递都有清晰依据。",
    submit: "创建账号",
    pending: "正在创建…",
    alternate: "已经有账号？",
    alternateAction: "返回登录",
    alternateHref: "/login",
  },
} as const;

export function AuthForm({ mode, successMessage }: AuthFormProps) {
  const router = useRouter();
  const copy = content[mode];
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const body = JSON.stringify({ email, password });

      if (mode === "register") {
        await apiRequest<RegisteredUserEnvelope>("/auth/register", {
          method: "POST",
          body,
        });
        router.replace("/login?registered=1");
        return;
      }

      await apiRequest<CurrentUserEnvelope>("/auth/login", {
        method: "POST",
        body,
      });
      router.replace("/dashboard");
      router.refresh();
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "操作失败，请稍后重试。",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-7 shadow-xl shadow-slate-200/50 sm:p-9">
      <div className="mb-8">
        <p className="text-sm font-semibold text-blue-600">CareerPilot</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
          {copy.title}
        </h1>
        <p className="mt-3 leading-7 text-slate-600">{copy.description}</p>
      </div>

      {successMessage ? (
        <div
          className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"
          role="status"
        >
          {successMessage}
        </div>
      ) : null}

      <form className="space-y-5" onSubmit={handleSubmit}>
        <div>
          <label className="text-sm font-medium text-slate-800" htmlFor="email">
            邮箱
          </label>
          <input
            autoComplete="email"
            className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            id="email"
            maxLength={254}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            required
            type="email"
            value={email}
          />
        </div>

        <div>
          <div className="flex items-center justify-between gap-4">
            <label
              className="text-sm font-medium text-slate-800"
              htmlFor="password"
            >
              密码
            </label>
            <span className="text-xs text-slate-500">至少 15 个字符</span>
          </div>
          <input
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-950 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            id="password"
            maxLength={128}
            minLength={15}
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </div>

        {error ? (
          <div
            className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            role="alert"
          >
            {error}
          </div>
        ) : null}

        <button
          className="w-full rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white shadow-sm transition hover:bg-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:bg-blue-300"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? copy.pending : copy.submit}
        </button>
      </form>

      <p className="mt-7 text-center text-sm text-slate-600">
        {copy.alternate}{" "}
        <Link
          className="font-semibold text-blue-600 hover:text-blue-700"
          href={copy.alternateHref}
        >
          {copy.alternateAction}
        </Link>
      </p>
    </div>
  );
}
