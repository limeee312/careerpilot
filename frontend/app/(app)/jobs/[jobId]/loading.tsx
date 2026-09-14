export default function JobDetailLoading() {
  return (
    <div
      aria-live="polite"
      className="rounded-3xl border border-slate-200 bg-white px-6 py-20 text-center shadow-sm"
    >
      <div className="mx-auto h-9 w-9 animate-spin rounded-full border-4 border-blue-100 border-t-blue-600" />
      <p className="mt-4 text-sm font-medium text-slate-600">
        正在加载职位匹配详情…
      </p>
    </div>
  );
}
