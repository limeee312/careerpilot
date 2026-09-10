import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col justify-center px-6 py-16 sm:px-10">
      <div className="mb-8 inline-flex w-fit items-center rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600 shadow-sm">
        CareerPilot MVP 0.1
      </div>
      <h1 className="max-w-4xl text-5xl font-semibold tracking-tight text-slate-950 sm:text-7xl">
        让每一次投递，都有清晰依据。
      </h1>
      <p className="mt-7 max-w-2xl text-lg leading-8 text-slate-600 sm:text-xl">
        职航帮助求职者比较目标岗位、理解匹配证据、生成真实可信的岗位版简历，并持续管理投递进度。
      </p>
      <div className="mt-9 flex flex-wrap gap-3">
        <Link
          className="rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white shadow-sm transition hover:bg-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
          href="/register"
        >
          免费开始
        </Link>
        <Link
          className="rounded-xl border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-700 shadow-sm transition hover:border-slate-400 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
          href="/login"
        >
          登录
        </Link>
      </div>
      <div className="mt-10 grid gap-4 sm:grid-cols-3">
        {[
          ["01", "导入职位", "粘贴 1–5 个岗位 JD，保留完整原文。"],
          ["02", "比较匹配", "逐条核对岗位要求与简历证据。"],
          ["03", "完成投递", "优化真实经历并记录求职进展。"],
        ].map(([number, title, description]) => (
          <section
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
            key={number}
          >
            <div className="text-sm font-semibold text-blue-600">{number}</div>
            <h2 className="mt-5 text-xl font-semibold text-slate-900">{title}</h2>
            <p className="mt-2 leading-7 text-slate-600">{description}</p>
          </section>
        ))}
      </div>
    </main>
  );
}
