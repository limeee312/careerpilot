import assert from "node:assert/strict";
import test from "node:test";

import { getDashboardMetrics, isDashboardEmpty } from "./dashboard.ts";

test("dashboard metrics combine rejected and withdrawn as terminated", () => {
  const metrics = getDashboardMetrics({
    total: 12,
    active: 5,
    rejected: 4,
    offer: 2,
    withdrawn: 1,
  });

  assert.deepEqual(
    metrics.map(({ key, value }) => [key, value]),
    [
      ["total", 12],
      ["active", 5],
      ["terminated", 5],
      ["offer", 2],
    ],
  );
  assert.equal(metrics[2].description, "淘汰 4 · 主动放弃 1");
});

test("dashboard empty state requires no overview or recent records", () => {
  const empty = {
    overview: {
      total: 0,
      active: 0,
      rejected: 0,
      offer: 0,
      withdrawn: 0,
    },
    recent_applications: [],
  };

  assert.equal(isDashboardEmpty(empty), true);
  assert.equal(
    isDashboardEmpty({
      ...empty,
      overview: { ...empty.overview, total: 1, active: 1 },
    }),
    false,
  );
});
