import type { Metadata } from "next";

import { AuthForm } from "@/components/auth/auth-form";

export const metadata: Metadata = {
  title: "登录 | 职航 CareerPilot",
};

type LoginPageProps = {
  searchParams: Promise<{ registered?: string }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const { registered } = await searchParams;

  return (
    <AuthForm
      mode="login"
      successMessage={registered === "1" ? "账号创建成功，请登录。" : undefined}
    />
  );
}
