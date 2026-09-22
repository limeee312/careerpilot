import { NewApplicationForm } from "@/components/application/new-application-form";

export default async function NewApplicationPage({
  searchParams,
}: {
  searchParams: Promise<{ jobId?: string; versionId?: string }>;
}) {
  const { jobId, versionId } = await searchParams;
  return <NewApplicationForm jobId={jobId ?? ""} preferredVersionId={versionId ?? ""} />;
}
