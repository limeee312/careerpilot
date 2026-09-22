import { expect, test } from "@playwright/test";

test("register, match a job, save a tailored resume, and track an application", async ({ page }) => {
  const uncaught: string[] = [];
  page.on("pageerror", (error) => uncaught.push(error.message));

  await test.step("register and sign in", async () => {
    await page.goto("/register");
    await page.getByLabel("邮箱").fill("candidate@example.com");
    await page.getByLabel("密码").fill("correct-horse-battery-staple");
    await page.getByRole("button", { name: "创建账号" }).click();
    await expect(page).toHaveURL(/\/login\?registered=1/);
    await page.getByLabel("邮箱").fill("candidate@example.com");
    await page.getByLabel("密码").fill("correct-horse-battery-staple");
    await page.getByRole("button", { name: "登录", exact: true }).click();
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByRole("heading", { name: "开始记录第一份投递" })).toBeVisible();
  });

  await test.step("create a resume with verifiable experience", async () => {
    await page.getByRole("navigation", { name: "主导航" }).getByRole("link", { name: "我的简历" }).click();
    await page.getByRole("link", { name: "创建简历母版" }).first().click();
    await page.getByLabel("姓名").fill("林测试");
    await page.getByLabel("简历联系邮箱").fill("candidate@example.com");
    await page.getByRole("navigation", { name: "简历分区" }).getByRole("button", { name: /工作与实习/ }).click();
    await page.getByRole("button", { name: /添加工作或实习经历/ }).click();
    await page.getByLabel("组织 / 公司").fill("示例公司");
    await page.getByLabel("职位 / 角色").fill("产品运营");
    await page.getByLabel("开始年月").fill("2024-01");
    await page.getByLabel("结束年月").fill("2025-06");
    await page.getByLabel("职责与行动").fill("独立负责用户调研与活动复盘，形成产品运营方案。");
    await page.getByRole("button", { name: "保存", exact: true }).click();
    await expect(page.getByRole("button", { name: "保存成功 ✓" })).toBeVisible();
  });

  await test.step("create and analyze a job batch", async () => {
    await page.getByRole("navigation", { name: "主导航" }).getByRole("link", { name: "职位匹配" }).click();
    await page.getByRole("textbox", { name: /批次名称/ }).fill("产品运营测试批次");
    await page.getByRole("textbox", { name: /公司名称/ }).fill("目标公司");
    await page.getByRole("textbox", { name: /职位名称/ }).fill("增长产品运营");
    await page.getByPlaceholder("请粘贴完整职位描述，包括职责、任职要求及优先条件。").fill(
      "负责用户增长及活动运营，分析用户行为数据，设计并落地增长实验；需要跨团队沟通、熟练使用数据分析方法，持续复盘和优化产品体验。",
    );
    await page.getByRole("button", { name: "保存并开始分析" }).click();
    await expect(page).toHaveURL(/\/job-match\/22222222-/);
    await expect(page.getByText("全部分析完成。")).toBeVisible();
    await page.getByRole("link", { name: "查看详情" }).click();
    await expect(page).toHaveURL(/\/jobs\/33333333-/);
    await expect(page.getByRole("heading", { name: "增长产品运营" })).toBeVisible();
  });

  await test.step("generate and save a job-specific resume", async () => {
    await page.getByRole("link", { name: "针对该职位优化简历" }).click();
    await expect(page).toHaveURL(/\/resume-tailor$/);
    await page.getByRole("button", { name: "生成针对性简历" }).click();
    await expect(page.getByLabel("针对性职业概述")).toHaveValue("具有产品运营实战经历。");
    await page.getByLabel("针对性职业概述").fill("有用户调研和活动复盘经验的产品运营。");
    await page.getByRole("button", { name: "保存为岗位版简历" }).click();
    await expect(page.getByText(/已保存“目标公司 · 增长产品运营”/)).toBeVisible();
  });

  await test.step("create a linked application and see it in the tracker", async () => {
    await page.getByRole("link", { name: "创建投递记录 →" }).click();
    await expect(page.getByRole("heading", { name: "创建投递记录" })).toBeVisible();
    await expect(page.getByLabel("岗位版简历")).toHaveValue("55555555-5555-4555-8555-555555555555");
    await page.getByLabel("投递日期").fill("2026-09-21");
    await page.getByLabel("备注").fill("已在官网投递");
    await page.getByRole("button", { name: "确认创建投递" }).click();
    await expect(page).toHaveURL(/\/applications\/66666666-/);
    await expect(page.getByRole("heading", { name: "招聘流程时间线" })).toBeVisible();
    await page.getByRole("navigation", { name: "主导航" }).getByRole("link", { name: "投递管理" }).click();
    await expect(page.getByRole("link", { name: /目标公司.*增长产品运营/ })).toBeVisible();
    await page.getByRole("navigation", { name: "主导航" }).getByRole("link", { name: "首页" }).click();
    await expect(page.getByRole("region", { name: "投递状态总览" })).toContainText("累计投递");
    await expect(page.getByRole("region", { name: "投递状态总览" })).toContainText("1");
  });

  expect(uncaught).toEqual([]);
});
