import type { Metadata } from "next";

import { ApplicationList } from "@/components/application/application-list";

export const metadata: Metadata = {
  title: "投递管理 | 职航 CareerPilot",
};

export default function ApplicationsPage() {
  return <ApplicationList />;
}
