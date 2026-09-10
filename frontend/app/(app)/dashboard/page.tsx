import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "首页 | 职航 CareerPilot",
};

const nextSteps = [
  {
    number: "01",
    title: "创建简历母版",
    description: "结构化保存教育、经历、项目和技能，作为后续匹配的事实来源。",
  },
  {
    number: "02",
    title: "导入目标职位",
    description: "粘贴真实 JD，拆解岗位要求并与简历证据逐项比较。",
  },
  {
    number: "03",
    title: "管理投递进度",
    description: "保存目标岗位，记录阶段变化和关键流程节点。",
  },
];

export default function DashboardPage() {
  return (
    <div>
      <div className="max-w-2xl">
        <p className="text-sm font-semibold text-blue-600">MVP 0.1</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
          欢迎来到职航
        </h1>
        <p className="mt-4 text-lg leading-8 text-slate-600">
          账号与安全会话已经就绪。接下来将从简历母版开始，逐步完成岗位匹配与投递管理闭环。
        </p>
      </div>

      <section className="mt-10 grid gap-5 lg:grid-cols-3" aria-label="后续步骤">
        {nextSteps.map((step) => (
          <article
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
            key={step.number}
          >
            <div className="flex items-center justify-between gap-4">
              <span className="text-sm font-semibold text-blue-600">
                {step.number}
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">
                即将开发
              </span>
            </div>
            <h2 className="mt-6 text-lg font-semibold text-slate-900">
              {step.title}
            </h2>
            <p className="mt-2 leading-7 text-slate-600">{step.description}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
