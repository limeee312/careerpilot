import type { Metadata } from "next";

import { ResumeEditor } from "@/components/resume/resume-editor";

export const metadata: Metadata = {
  title: "编辑简历母版 | 职航 CareerPilot",
};

export default function ResumeMasterEditPage() {
  return <ResumeEditor />;
}
