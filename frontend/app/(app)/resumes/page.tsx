import type { Metadata } from "next";

import { ResumeLibrary } from "@/components/resume/resume-library";

export const metadata: Metadata = {
  title: "我的简历 | 职航 CareerPilot",
};

export default function ResumesPage() {
  return <ResumeLibrary />;
}
