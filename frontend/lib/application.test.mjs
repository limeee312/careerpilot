import assert from "node:assert/strict";
import test from "node:test";

import {
  filterApplications,
  formatApplicationDate,
  formatApplicationUpdatedAt,
  getApplicationFilterCounts,
  getApplicationStageLabel,
  getApplicationStatusLabel,
} from "./application.ts";

function application(id, processStatus) {
  return {
    id,
    job_id: null,
    resume_version_id: null,
    company_name: "示例公司",
    job_title: "产品经理",
    job_url: null,
    applied_at: "2026-09-08T00:00:00Z",
    current_stage: "APPLICATION",
    current_round: null,
    process_status: processStatus,
    note: null,
    created_at: "2026-09-08T00:00:00Z",
    updated_at: "2026-09-08T00:00:00Z",
  };
}

test("application labels cover lifecycle statuses and interview rounds", () => {
  assert.equal(getApplicationStatusLabel("ACTIVE"), "进行中");
  assert.equal(getApplicationStatusLabel("REJECTED"), "已淘汰");
  assert.equal(getApplicationStatusLabel("OFFER"), "Offer");
  assert.equal(getApplicationStatusLabel("WITHDRAWN"), "主动放弃");
  assert.equal(getApplicationStageLabel("APPLICATION", null), "已投递");
  assert.equal(getApplicationStageLabel("INTERVIEW", 1), "一面");
  assert.equal(getApplicationStageLabel("INTERVIEW", 7), "第 7 轮面试");
  assert.equal(getApplicationStageLabel("INTERVIEW", null), "面试");
});

test("application filters and counts use the four product statuses", () => {
  const applications = [
    application("active-1", "ACTIVE"),
    application("active-2", "ACTIVE"),
    application("offer-1", "OFFER"),
    application("rejected-1", "REJECTED"),
  ];

  assert.deepEqual(
    filterApplications(applications, "ACTIVE").map(({ id }) => id),
    ["active-1", "active-2"],
  );
  assert.equal(filterApplications(applications, "ALL"), applications);
  assert.deepEqual(getApplicationFilterCounts(applications), {
    ALL: 4,
    ACTIVE: 2,
    REJECTED: 1,
    OFFER: 1,
    WITHDRAWN: 0,
  });
});

test("application date formatters are stable in the product timezone", () => {
  assert.equal(formatApplicationDate("2026-09-08T16:30:00Z"), "2026-09-09");
  assert.equal(formatApplicationUpdatedAt("2026-09-08T16:30:00Z"), "09-09 00:30");
  assert.equal(formatApplicationDate("not-a-date"), "日期未知");
  assert.equal(formatApplicationUpdatedAt("not-a-date"), "时间未知");
});
