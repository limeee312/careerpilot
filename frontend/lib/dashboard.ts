import type { ApplicationListItem } from "./application";

export type DashboardOverview = {
  total: number;
  active: number;
  rejected: number;
  offer: number;
  withdrawn: number;
};

export type DashboardData = {
  overview: DashboardOverview;
  recent_applications: ApplicationListItem[];
};

export type DashboardEnvelope = {
  data: DashboardData;
};

export type DashboardMetric = {
  key: "total" | "active" | "terminated" | "offer";
  label: string;
  value: number;
  description: string;
  tone: "slate" | "blue" | "amber" | "emerald";
};

export function getDashboardMetrics(
  overview: DashboardOverview,
): DashboardMetric[] {
  return [
    {
      key: "total",
      label: "累计投递",
      value: overview.total,
      description: "全部投递记录",
      tone: "slate",
    },
    {
      key: "active",
      label: "进行中",
      value: overview.active,
      description: "仍在推进的流程",
      tone: "blue",
    },
    {
      key: "terminated",
      label: "流程终止",
      value: overview.rejected + overview.withdrawn,
      description: `淘汰 ${overview.rejected} · 主动放弃 ${overview.withdrawn}`,
      tone: "amber",
    },
    {
      key: "offer",
      label: "Offer",
      value: overview.offer,
      description: "已获得录用结果",
      tone: "emerald",
    },
  ];
}

export function isDashboardEmpty(dashboard: DashboardData): boolean {
  return (
    dashboard.overview.total === 0 && dashboard.recent_applications.length === 0
  );
}
