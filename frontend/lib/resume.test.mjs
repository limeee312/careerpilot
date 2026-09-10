import assert from "node:assert/strict";
import test from "node:test";

import {
  buildResumePayload,
  calculateResumeCompleteness,
  createEmptyEducation,
  createEmptyExperience,
  createEmptyProject,
  createEmptyResume,
  createEmptySkill,
  formatResumeUpdatedAt,
  validateResume,
} from "./resume.ts";

test("an empty resume has zero completeness and is sparse", () => {
  const result = calculateResumeCompleteness(createEmptyResume());

  assert.equal(result.score, 0);
  assert.equal(result.isSparse, true);
  assert.equal(result.items.every((item) => !item.complete), true);
});

test("resume update timestamps render as a readable calendar date", () => {
  assert.equal(
    formatResumeUpdatedAt("2026-09-10T09:19:11Z", "UTC"),
    "2026年9月10日",
  );
  assert.equal(formatResumeUpdatedAt("not-a-date", "UTC"), "未知日期");
});

test("the documented completeness rules add up to 100 percent", () => {
  const resume = createEmptyResume();
  resume.basic_info.name = "林舟";
  resume.basic_info.email = "candidate@example.com";

  const education = createEmptyEducation();
  education.school = "示例大学";
  education.degree = "本科";
  education.major = "信息管理";
  education.start_date = "2022-09";
  education.end_date = "2026-06";
  resume.education.push(education);

  const experience = createEmptyExperience();
  experience.experience_type = "WORK";
  experience.organization = "示例公司";
  experience.position = "产品经理";
  experience.start_date = "2026-01";
  experience.description = "负责用户调研与需求分析";
  experience.achievements = "完成流程改造并交付分析报告";
  resume.experiences.push(experience);

  const project = createEmptyProject();
  project.name = "用户研究项目";
  project.description = "完成访谈和洞察整理";
  resume.projects.push(project);
  for (const name of ["SQL", "Python", "Excel"]) {
    const skill = createEmptySkill();
    skill.skill_name = name;
    resume.skills.push(skill);
  }

  const result = calculateResumeCompleteness(resume);

  assert.equal(result.score, 100);
  assert.equal(result.isSparse, false);
  assert.equal(result.items.every((item) => item.complete), true);
});

test("campus experience does not satisfy the work or internship rule", () => {
  const resume = createEmptyResume();
  const experience = createEmptyExperience();
  experience.experience_type = "CAMPUS";
  resume.experiences.push(experience);

  const result = calculateResumeCompleteness(resume);
  const workItem = result.items.find((item) => item.key === "experience");

  assert.equal(workItem?.complete, false);
});

test("API payload trims values, removes client keys, and clears a current end date", () => {
  const resume = createEmptyResume();
  resume.basic_info.name = "  林舟  ";
  resume.basic_info.phone = "   ";

  const experience = createEmptyExperience();
  experience.id = "8b9ca72a-65f3-4cef-b3af-66dbab172f9c";
  experience.organization = "  示例公司 ";
  experience.position = " 产品实习生 ";
  experience.start_date = "2026-01";
  experience.end_date = "2026-08";
  experience.is_current = true;
  experience.description = "  分析用户反馈  ";
  resume.experiences.push(experience);

  const payload = buildResumePayload(resume);

  assert.equal(payload.basic_info.name, "林舟");
  assert.equal(payload.basic_info.phone, null);
  assert.deepEqual(payload.experiences[0], {
    id: experience.id,
    experience_type: "INTERNSHIP",
    organization: "示例公司",
    position: "产品实习生",
    start_date: "2026-01",
    end_date: null,
    is_current: true,
    description: "分析用户反馈",
    achievements: null,
  });
  assert.equal("clientKey" in payload.experiences[0], false);
});

test("validation catches reversed dates and duplicate skills before save", () => {
  const resume = createEmptyResume();
  const education = createEmptyEducation();
  education.school = "示例大学";
  education.degree = "本科";
  education.major = "信息管理";
  education.start_date = "2026-09";
  education.end_date = "2025-06";
  resume.education.push(education);

  assert.match(
    validateResume(resume)?.message ?? "",
    /结束年月不能早于开始年月/,
  );

  education.end_date = "2026-10";
  for (const name of ["SQL", "SQL"]) {
    const skill = createEmptySkill();
    skill.skill_name = name;
    resume.skills.push(skill);
  }
  assert.deepEqual(validateResume(resume), {
    section: "skills",
    message: "同一份简历不能包含重名技能。",
  });
});
