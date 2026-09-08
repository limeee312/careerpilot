import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "职航 CareerPilot",
  description: "AI 求职决策与求职过程管理平台",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
