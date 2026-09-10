import Link from "next/link";

export default function AuthLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden px-6 py-12">
      <div className="absolute left-6 top-6 sm:left-10 sm:top-8">
        <Link
          className="font-semibold tracking-tight text-slate-900 transition hover:text-blue-700"
          href="/"
        >
          职航 CareerPilot
        </Link>
      </div>
      {children}
    </main>
  );
}
