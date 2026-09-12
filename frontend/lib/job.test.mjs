import assert from "node:assert/strict";
import test from "node:test";

import {
  buildJobBatchPayload,
  createEmptyJobBatch,
  createEmptyManualJob,
  validateJobBatch,
} from "./job.ts";

const longJd =
  "负责产品用户运营策略制定与执行，通过用户行为数据分析发现问题，并联动产品、研发和市场团队推进运营项目落地。";

function validDraft() {
  const draft = createEmptyJobBatch();
  draft.name = "  秋招重点岗位  ";
  draft.jobs[0].company_name = "  示例科技  ";
  draft.jobs[0].title = "  产品运营  ";
  draft.jobs[0].location = "  杭州  ";
  draft.jobs[0].department = "   ";
  draft.jobs[0].source_url = "  https://example.com/jobs/123  ";
  draft.jobs[0].raw_jd = `  ${longJd}  `;
  return draft;
}

test("manual batch starts with one empty job", () => {
  const draft = createEmptyJobBatch();

  assert.equal(draft.jobs.length, 1);
  assert.ok(draft.jobs[0].clientKey);
});

test("API payload trims values, converts blanks to null, and removes client keys", () => {
  const draft = validDraft();
  const payload = buildJobBatchPayload(draft);

  assert.deepEqual(payload, {
    name: "秋招重点岗位",
    jobs: [
      {
        company_name: "示例科技",
        title: "产品运营",
        location: "杭州",
        department: null,
        source_url: "https://example.com/jobs/123",
        raw_jd: longJd,
      },
    ],
  });
  assert.equal("clientKey" in payload.jobs[0], false);
});

test("validation requires company, title, and a 50-character JD", () => {
  const draft = createEmptyJobBatch();

  assert.deepEqual(validateJobBatch(draft), {
    jobIndex: 0,
    field: "company_name",
    message: "职位 1 需要填写公司名称。",
  });

  draft.jobs[0].company_name = "示例科技";
  draft.jobs[0].title = "产品运营";
  draft.jobs[0].raw_jd = "内容不足";
  assert.deepEqual(validateJobBatch(draft), {
    jobIndex: 0,
    field: "raw_jd",
    message: "职位 1 的 JD 至少需要 50 个字符。",
  });
});

test("validation accepts at most five jobs", () => {
  const draft = validDraft();
  draft.jobs = Array.from({ length: 6 }, () => createEmptyManualJob());

  assert.deepEqual(validateJobBatch(draft), {
    jobIndex: null,
    field: "jobs",
    message: "每个批次需要包含 1–5 个职位。",
  });
});

test("validation rejects non-http job links", () => {
  const draft = validDraft();
  draft.jobs[0].source_url = "javascript:alert(1)";

  assert.deepEqual(validateJobBatch(draft), {
    jobIndex: 0,
    field: "source_url",
    message: "职位 1 的职位链接需要以 http:// 或 https:// 开头。",
  });
});
