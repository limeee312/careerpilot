import assert from "node:assert/strict";
import test from "node:test";

import {
  getAnalysisStatusLabel,
  getAnalysisSteps,
  getEligibilityLabel,
  getMatchProgress,
  getRankLabel,
  isTerminalBatchStatus,
  prepareBatchForAnalysis,
} from "./job-match.ts";

function batch(overrides = {}) {
  return {
    id: "batch-1",
    name: "秋招岗位",
    status: "PROCESSING",
    total_jobs: 5,
    successful_jobs: 2,
    failed_jobs: 1,
    jobs: [
      {
        job_id: "job-1",
        company_name: "示例科技",
        title: "产品运营",
        location: "杭州",
        department: null,
        source_url: null,
        analysis_status: "COMPLETED",
        error_code: null,
        result: {
          id: "result-1",
          rank: 1,
          near_tie_group: 1,
          is_tied: false,
          eligibility_status: "PASS",
          total_score: "91.25",
          display_score: 91,
          confidence_score: "90.00",
          confidence_level: "HIGH",
          recommendation_level: "PRIORITY",
          recommendation: "优先投递",
          created_at: "2026-09-14T10:00:00Z",
        },
      },
    ],
    created_at: "2026-09-14T09:00:00Z",
    updated_at: "2026-09-14T10:00:00Z",
    ...overrides,
  };
}

test("terminal batch states exclude drafts and active analysis", () => {
  assert.equal(isTerminalBatchStatus("DRAFT"), false);
  assert.equal(isTerminalBatchStatus("PROCESSING"), false);
  assert.equal(isTerminalBatchStatus("COMPLETED"), true);
  assert.equal(isTerminalBatchStatus("PARTIAL_FAILED"), true);
  assert.equal(isTerminalBatchStatus("FAILED"), true);
});

test("batch progress counts successful and failed jobs without exceeding total", () => {
  assert.deepEqual(getMatchProgress(batch()), {
    resolvedJobs: 3,
    percent: 60,
  });
  assert.deepEqual(
    getMatchProgress(batch({ successful_jobs: 7, failed_jobs: 2 })),
    { resolvedJobs: 5, percent: 100 },
  );
});

test("analysis steps distinguish parser and matcher progress", () => {
  assert.deepEqual(getAnalysisSteps("PENDING"), {
    parsing: "waiting",
    matching: "waiting",
  });
  assert.deepEqual(getAnalysisSteps("PARSING"), {
    parsing: "active",
    matching: "waiting",
  });
  assert.deepEqual(getAnalysisSteps("MATCHING"), {
    parsing: "complete",
    matching: "active",
  });
  assert.deepEqual(getAnalysisSteps("COMPLETED"), {
    parsing: "complete",
    matching: "complete",
  });
});

test("status, eligibility, and tied-rank labels are user-facing", () => {
  assert.equal(getAnalysisStatusLabel("MATCHING"), "正在匹配简历证据");
  assert.equal(getEligibilityLabel("WARN"), "条件待核实");
  assert.equal(
    getRankLabel({ ...batch().jobs[0].result, rank: 2, is_tied: true }),
    "并列第 2",
  );
  assert.equal(
    getRankLabel({ ...batch().jobs[0].result, rank: null }),
    "不参与排序",
  );
});

test("starting another run clears prior results and progress", () => {
  const prepared = prepareBatchForAnalysis(
    batch({ status: "PARTIAL_FAILED" }),
  );

  assert.equal(prepared.status, "PROCESSING");
  assert.equal(prepared.successful_jobs, 0);
  assert.equal(prepared.failed_jobs, 0);
  assert.equal(prepared.jobs[0].analysis_status, "PENDING");
  assert.equal(prepared.jobs[0].result, null);
});
