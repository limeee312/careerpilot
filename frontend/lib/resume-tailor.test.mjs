import assert from "node:assert/strict";
import test from "node:test";

import {
  cloneTailorOutput,
  formatResumePeriod,
  getImprovementStatusLabel,
  getIncludedTailoredItems,
  getOrderedSkills,
  moveSkill,
  reorderIncludedItems,
} from "./resume-tailor.ts";
import {
  buildResumeVersionPayload,
  validateTailorDraftForSave,
} from "./resume-version.ts";

const sourceResume = {
  id: "resume-1",
  basic_info: {
    name: "林舟",
    phone: null,
    email: null,
    city: null,
    job_status: null,
    summary: "产品与数据分析经历",
  },
  education: [],
  experiences: [],
  projects: [],
  skills: [
    {
      id: "skill-excel",
      skill_name: "Excel",
      skill_category: null,
      proficiency: null,
    },
    {
      id: "skill-python",
      skill_name: "Python",
      skill_category: null,
      proficiency: null,
    },
  ],
  created_at: "2026-09-01T00:00:00Z",
  updated_at: "2026-09-01T00:00:00Z",
};

const tailoredItems = [
  { source_id: "exp-b", include: true, order: 2, bullets: [] },
  { source_id: "exp-unused", include: false, order: null, bullets: [] },
  { source_id: "exp-a", include: true, order: 1, bullets: [] },
];

test("included sections follow the AI order while excluded facts remain outside the draft", () => {
  assert.deepEqual(
    getIncludedTailoredItems(tailoredItems).map((item) => item.source_id),
    ["exp-a", "exp-b"],
  );
});

test("manual section reordering keeps contiguous order and preserves excluded items", () => {
  const reordered = reorderIncludedItems(tailoredItems, "exp-a", 1);

  assert.deepEqual(
    getIncludedTailoredItems(reordered).map((item) => [item.source_id, item.order]),
    [
      ["exp-b", 1],
      ["exp-a", 2],
    ],
  );
  assert.deepEqual(reordered.find((item) => item.source_id === "exp-unused"), {
    source_id: "exp-unused",
    include: false,
    order: null,
    bullets: [],
  });
});

test("skill ordering only resolves IDs present in the immutable source snapshot", () => {
  const order = moveSkill(["skill-excel", "skill-python"], "skill-python", -1);
  assert.deepEqual(order, ["skill-python", "skill-excel"]);
  assert.deepEqual(
    getOrderedSkills(sourceResume, [...order, "invented-skill"]).map(
      (skill) => skill.skill_name,
    ),
    ["Python", "Excel"],
  );
});

test("cloning a draft keeps edits isolated from the validated API response", () => {
  const source = {
    professional_summary: "原始概述",
    experiences: [
      {
        source_id: "exp-a",
        include: true,
        order: 1,
        bullets: [
          {
            text: "原始改写",
            evidence_refs: [
              { source_field: "description", source_quote: "真实原文" },
            ],
          },
        ],
      },
    ],
    projects: [],
    skill_order: ["skill-excel"],
    improvement_suggestions: [],
    warnings: [],
  };

  const cloned = cloneTailorOutput(source);
  cloned.experiences[0].bullets[0].text = "用户编辑";
  cloned.experiences[0].bullets[0].evidence_refs[0].source_quote = "引用副本";

  assert.equal(source.experiences[0].bullets[0].text, "原始改写");
  assert.equal(
    source.experiences[0].bullets[0].evidence_refs[0].source_quote,
    "真实原文",
  );
});

test("resume dates and gap states have stable user-facing labels", () => {
  assert.equal(formatResumePeriod("2025-01", "2025-08"), "2025.01 – 2025.08");
  assert.equal(formatResumePeriod("2025-01", null, true), "2025.01 – 至今");
  assert.equal(getImprovementStatusLabel("NO_EVIDENCE"), "暂无证据");
  assert.equal(getImprovementStatusLabel("PARTIAL_MATCH"), "部分匹配");
});

test("version payload uses trace metadata and normalizes editable text", () => {
  const draftData = {
    match_result_id: "match-1",
    prompt_version: "resume_tailor_v1",
    model: "test-model",
  };
  const draft = {
    professional_summary: "  数据分析经历  ",
    experiences: [
      {
        source_id: "exp-a",
        include: true,
        order: 1,
        bullets: [
          {
            text: "  梳理流程数据  ",
            evidence_refs: [
              { source_field: "description", source_quote: "梳理流程数据" },
            ],
          },
        ],
      },
    ],
    projects: [],
    skill_order: ["skill-excel"],
    improvement_suggestions: [],
    warnings: [],
  };

  const payload = buildResumeVersionPayload(draftData, draft);

  assert.equal(payload.match_result_id, "match-1");
  assert.equal(payload.prompt_version, "resume_tailor_v1");
  assert.equal(payload.draft.professional_summary, "数据分析经历");
  assert.equal(payload.draft.experiences[0].bullets[0].text, "梳理流程数据");
  assert.equal(draft.professional_summary, "  数据分析经历  ");
});

test("version save validation rejects blank included bullets", () => {
  const draft = {
    professional_summary: null,
    experiences: [
      {
        source_id: "exp-a",
        include: true,
        order: 1,
        bullets: [
          {
            text: "   ",
            evidence_refs: [
              { source_field: "description", source_quote: "真实原文" },
            ],
          },
        ],
      },
    ],
    projects: [],
    skill_order: [],
    improvement_suggestions: [],
    warnings: [],
  };

  assert.match(validateTailorDraftForSave(draft) ?? "", /不能包含空白要点/);
});
