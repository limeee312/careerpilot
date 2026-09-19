import assert from "node:assert/strict";
import test from "node:test";

import {
  buildApplicationEventPayload,
  buildApplicationStatusPayload,
  filterApplications,
  formatApplicationDate,
  formatApplicationTime,
  formatApplicationUpdatedAt,
  getApplicationFilterCounts,
  getApplicationEventLabel,
  getApplicationOutcomeLabel,
  getApplicationProgressLabel,
  getApplicationStageLabel,
  getApplicationStatusLabel,
  toDateTimeLocalValue,
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
  assert.equal(formatApplicationTime("2026-09-08T16:30:00Z"), "00:30");
  assert.equal(formatApplicationDate("not-a-date"), "日期未知");
  assert.equal(formatApplicationUpdatedAt("not-a-date"), "时间未知");
  assert.equal(toDateTimeLocalValue("not-a-date"), "");
});

test("timeline labels preserve custom nodes, outcomes, and terminal context", () => {
  const event = {
    id: "event-1",
    application_id: "application-1",
    event_type: "OTHER",
    custom_event_name: "HR 沟通",
    round_no: null,
    occurred_at: "2026-09-18T04:00:00Z",
    outcome: "COMPLETED",
    note: null,
    created_at: "2026-09-18T04:00:00Z",
    updated_at: "2026-09-18T04:00:00Z",
  };

  assert.equal(getApplicationEventLabel(event), "HR 沟通");
  assert.equal(getApplicationOutcomeLabel("COMPLETED"), "已完成");
  assert.equal(
    getApplicationProgressLabel({
      current_stage: "INTERVIEW",
      current_round: 1,
      process_status: "REJECTED",
    }),
    "一面淘汰",
  );
});

test("event payload enforces conditional round and custom name fields", () => {
  const missingRound = buildApplicationEventPayload({
    event_type: "INTERVIEW",
    custom_event_name: "",
    round_no: "",
    occurred_at: "2026-09-18T14:00",
    outcome: "PENDING",
    note: "",
  });
  assert.match(missingRound.error, /轮次/);

  const custom = buildApplicationEventPayload({
    event_type: "OTHER",
    custom_event_name: "  案例分析  ",
    round_no: "9",
    occurred_at: "2026-09-18T14:00",
    outcome: "COMPLETED",
    note: "  已提交  ",
  });
  assert.equal(custom.error, null);
  assert.equal(custom.data.custom_event_name, "案例分析");
  assert.equal(custom.data.round_no, null);
  assert.equal(custom.data.note, "已提交");
});

test("terminal status payload requires interview round and active stays minimal", () => {
  assert.deepEqual(
    buildApplicationStatusPayload("ACTIVE", "INTERVIEW", ""),
    { data: { process_status: "ACTIVE" }, error: null },
  );
  assert.match(
    buildApplicationStatusPayload("REJECTED", "INTERVIEW", "").error,
    /轮次/,
  );
  assert.deepEqual(
    buildApplicationStatusPayload("REJECTED", "INTERVIEW", "2"),
    {
      data: {
        process_status: "REJECTED",
        current_stage: "INTERVIEW",
        current_round: 2,
      },
      error: null,
    },
  );
});
