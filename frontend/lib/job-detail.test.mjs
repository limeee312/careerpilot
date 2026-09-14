import assert from "node:assert/strict";
import test from "node:test";

import {
  clampPercent,
  formatDetailScore,
  getAssessmentStatusLabel,
  getDimensionCards,
  getEvidenceSourceLabel,
  getMatchLevelLabel,
  getRequirementTypeLabel,
} from "./job-detail.ts";

test("dimension cards always expose six fixed dimensions and mark missing ones N/A", () => {
  const cards = getDimensionCards([
    {
      dimension: "RESPONSIBILITY",
      raw_score: "28.000",
      max_score: "35.000",
      normalized_score: "80.000",
    },
  ]);

  assert.equal(cards.length, 6);
  assert.equal(cards[0].label, "工作职责");
  assert.equal(cards[0].score.normalized_score, "80.000");
  assert.equal(cards[1].label, "工具与方法");
  assert.equal(cards[1].score, null);
  assert.equal(cards[5].label, "沟通协作");
});

test("requirement and evidence labels preserve UNKNOWN and transferable semantics", () => {
  assert.equal(getAssessmentStatusLabel("UNKNOWN"), "证据未知");
  assert.equal(getMatchLevelLabel(2), "可迁移");
  assert.equal(getRequirementTypeLabel("PREFERRED"), "优先条件");
  assert.equal(getEvidenceSourceLabel("experience"), "工作与实习");
  assert.equal(getEvidenceSourceLabel(null), "无直接来源");
});

test("detail scores avoid false precision and progress widths stay bounded", () => {
  assert.equal(formatDetailScore("28.000"), "28");
  assert.equal(formatDetailScore("28.125"), "28.1");
  assert.equal(formatDetailScore("not-a-number"), "N/A");
  assert.equal(clampPercent("105"), 100);
  assert.equal(clampPercent("-3"), 0);
  assert.equal(clampPercent("72.5"), 72.5);
});
