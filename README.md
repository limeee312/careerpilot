# 职航 CareerPilot

职航是一个面向应届生、社招求职者、转行人群及职业方向不明确求职者的 AI 求职决策与过程管理平台。

MVP 0.1 聚焦一条可验证的核心闭环：用户维护真实简历母版，导入 1–5 个岗位 JD，获得有证据支撑的匹配排序，生成不虚构事实的岗位版简历，并记录投递进度。

## 当前状态

项目处于 MVP 0.1 工程开发阶段。`CP-001` 至 `CP-023`（含 `CP-019A`）已实现，后续任务按 Backlog 顺序推进，每个任务独立提交并通过相应验收。

## 技术栈

- Frontend：Next.js、TypeScript、App Router、Tailwind CSS
- Backend：Python、FastAPI、Pydantic、SQLAlchemy、Alembic
- Database：PostgreSQL
- AI：OpenAI Responses API、Structured Outputs
- Quality：pytest、ESLint、GitHub Actions

## 项目结构

```text
careerpilot/
├── frontend/   # Next.js Web 应用
├── backend/    # FastAPI API 服务
├── docs/       # 产品、数据库与 AI 工程规格
└── README.md
```

## 产品与工程基线

- [产品需求文档](docs/PRD.md)
- [MVP 0.1 开发实施规格](docs/MVP_SPEC.md)
- [数据库 Schema 与 ERD](docs/DATABASE.md)
- [AI Skills 工程规格](docs/AI_SKILLS.md)

## 本地开发

前置要求：

- Node.js 24
- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Docker 与 Docker Compose

首次启动：

```bash
cp .env.example .env
docker compose up --build
```

服务地址：

- Frontend：<http://localhost:3000>
- Backend：<http://localhost:8000>
- OpenAPI：<http://localhost:8000/docs>
- Liveness：<http://localhost:8000/health>
- Readiness：<http://localhost:8000/health/ready>

如需分别启动服务，先启动数据库：

```bash
docker compose up -d db
```

再启动后端：

```bash
cd backend
uv sync --all-groups
uv run alembic upgrade head
uv run fastapi dev app/main.py
```

另一个终端启动前端：

```bash
cd frontend
npm install
npm run dev
```

## 测试

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest

cd ../frontend
npm test
npm run lint
npm run build
```

GitHub Actions 会额外启动真实 PostgreSQL 服务，执行迁移并验证数据库连接。

## 当前能力

- 邮箱注册与密码登录，使用 HttpOnly Cookie 保持会话；
- `/dashboard` 服务端会话保护，以及前端注册、登录、登出流程；
- 每个用户一份结构化简历母版，包含教育、经历、项目与技能子表；
- 数据库强制所有权基数、级联删除、经历类型和技能名称唯一性。
- `GET /api/v1/resume/master` 获取当前用户母版，`PUT` 同一路径在一个事务中创建或更新全部内容；
- 简历日期按 `YYYY-MM` 收发，数据库以当月 1 日保存，不把存储用日期展示为真实日。
- `/resumes/master/edit` 提供受登录保护的结构化简历编辑器，支持分区增删、排序、保存状态与确定性完整度提示。
- `/resumes` 汇总当前简历母版与已保存的岗位版简历；列表数据来自用户隔离的 Resume Version API，不生成占位版本数据。
- Job Batch 与 Job 数据层支持每批最多 5 个岗位、处理结果计数、用户所有权约束和级联删除，并永久保留用户输入的原始 JD。
- `POST /api/v1/job-match/batches` 在一个事务中保存当前用户的 1–5 个手动职位，并以 `DRAFT` 状态返回批次和原始 JD。
- `/job-match/new` 提供受登录保护的手动职位输入页，支持逐项增删、50 字符 JD 校验、错误保留与明确的保存状态。
- `job_parser_v1` 已建立严格的输入/输出契约：逐条要求区分 `HARD / CORE / STANDARD / PREFERRED`，非硬性要求映射单一能力维度，并由后端验证连续 Key、维度规则及 JD 原文引用。
- Job Parser 已接入 OpenAI Responses API 的 Pydantic Structured Outputs，服务层只在超时、5xx 或无效输出时重试一次，并返回模型、Prompt 版本、请求 ID 与 Token 用量供后续持久化。
- Job Parser 结果、原子岗位要求、Hard Gate、逐要求评估和六维得分均使用独立关系表持久化；Match Result 保存简历与 JD 快照，重新分析会追加历史记录，并由复合外键阻止跨用户或跨职位误关联。
- `job_matcher_v1` 已建立严格的输入/输出契约：Hard Gate 与非 Hard 要求分别逐条评估，AI 不返回总分或推荐等级；后端校验要求覆盖、证据来源 ID 和简历原文引用。
- Matcher 已接入字段白名单式脱敏 Context Builder 和版本化 Prompt；服务层使用 Pydantic Structured Outputs，只在超时、5xx 或无效输出时重试一次，并保留模型、Prompt 版本、请求 ID 与 Token 用量。
- Matcher 评分服务使用 `Decimal` 确定性计算 Evidence Cap、有效维度权重、总分、Eligibility、Confidence 与 Recommendation；缺失维度按 `N/A` 处理，推荐等级与页面整数分数使用同一四舍五入口径。
- 职位排序将 `FAIL` 岗位移出正常可投序列；分差不超过 3 分时采用组首分数锚定，再比较职责匹配率和置信度，避免相邻分数链式扩大并列范围。
- `POST /api/v1/job-match/batches/{id}/analyze` 串联 Parser、Matcher、后端评分与不可变结果持久化；单个岗位失败不回滚已成功结果，重新分析追加历史记录。
- `GET /api/v1/job-match/{id}` 返回批次进度、当前轮岗位状态与确定性排序结果；所有权不匹配统一返回 `BATCH_NOT_FOUND`。
- 创建职位批次后会进入 `/job-match/[batchId]` 自动发起分析并轮询逐岗位进度；完成后展示整数分数、推荐等级、Hard Gate、证据置信度及后端确定性排名。
- 匹配结果页保留部分成功结果，明确显示失败岗位并支持重新分析；未知硬性条件显示“条件待核实”，明确冲突岗位不进入正常可投排序。
- `GET /api/v1/jobs/{id}` 与 `/api/v1/jobs/{id}/match` 返回当前分析轮次的用户隔离详情，包含六维分数、Hard Gate、原子要求、优势、Gap 与简历证据引用。
- `/jobs/[jobId]` 展示完整的可解释匹配详情；缺失维度明确标记为 `N/A`，并说明匹配分衡量简历证据契合度而非 Offer 概率。
- `resume_tailor_v1` 使用匹配时保存的 Resume/JD Snapshot 生成可审阅 Draft；发送 AI 前排除姓名、电话、邮箱、城市和教育信息，不读取用户当前已修改的母版内容。
- `POST /api/v1/jobs/{id}/resume-tailor` 只返回当前用户职位的未持久化草稿，不修改简历母版；只有后续明确保存操作才会创建 Resume Version。
- Tailor 后端会校验来源 ID、原文引用、技能排列、数字、JD 工具、团队成果归属、负责程度与项目状态，拒绝无证据的增强表述。
- `/jobs/[jobId]/resume-tailor` 提供原简历与针对性草稿的左右对照，支持逐条审阅证据、编辑概述与 Bullet，以及调整经历、项目和技能顺序。
- Resume Tailor 仅在用户明确点击时调用 AI；重新生成失败会保留当前草稿，保存成功后才显示为岗位版简历。
- `POST /api/v1/resume/versions` 会重新校验人工编辑后的草稿，并从冻结快照组装公司、职位、日期、教育和技能等不可变字段；每次保存创建独立 `SAVED` 版本。
- `GET /api/v1/resume/versions` 与 `GET /api/v1/resume/versions/{id}` 均按当前用户隔离，保存后的岗位版简历会出现在简历库中且不覆盖母版。

## 开发原则

- AI 判断必须提供可追溯证据。
- 最终分数、排序和资格状态由后端确定性规则计算。
- 岗位版简历只能重组真实经历，不得新增技能、数字或成果。
- 所有用户数据按 `user_id` 隔离，越权访问统一返回 404。
