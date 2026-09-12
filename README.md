# 职航 CareerPilot

职航是一个面向应届生、社招求职者、转行人群及职业方向不明确求职者的 AI 求职决策与过程管理平台。

MVP 0.1 聚焦一条可验证的核心闭环：用户维护真实简历母版，导入 1–5 个岗位 JD，获得有证据支撑的匹配排序，生成不虚构事实的岗位版简历，并记录投递进度。

## 当前状态

项目处于 MVP 0.1 工程开发阶段。`CP-001` 至 `CP-018` 已实现，后续任务按 Backlog 顺序推进，每个任务独立提交并通过相应验收。

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
- `/resumes` 汇总当前简历母版与未来的岗位版简历；当前阶段展示真实母版状态，不生成占位版本数据。
- Job Batch 与 Job 数据层支持每批最多 5 个岗位、处理结果计数、用户所有权约束和级联删除，并永久保留用户输入的原始 JD。
- `POST /api/v1/job-match/batches` 在一个事务中保存当前用户的 1–5 个手动职位，并以 `DRAFT` 状态返回批次和原始 JD。
- `/job-match/new` 提供受登录保护的手动职位输入页，支持逐项增删、50 字符 JD 校验、错误保留与明确的保存状态。
- `job_parser_v1` 已建立严格的输入/输出契约：逐条要求区分 `HARD / CORE / STANDARD / PREFERRED`，非硬性要求映射单一能力维度，并由后端验证连续 Key、维度规则及 JD 原文引用。
- Job Parser 已接入 OpenAI Responses API 的 Pydantic Structured Outputs，服务层只在超时、5xx 或无效输出时重试一次，并返回模型、Prompt 版本、请求 ID 与 Token 用量供后续持久化。
- Job Parser 结果、原子岗位要求、Hard Gate、逐要求评估和六维得分均使用独立关系表持久化；Match Result 保存简历与 JD 快照，重新分析会追加历史记录，并由复合外键阻止跨用户或跨职位误关联。
- `job_matcher_v1` 已建立严格的输入/输出契约：Hard Gate 与非 Hard 要求分别逐条评估，AI 不返回总分或推荐等级；后端校验要求覆盖、证据来源 ID 和简历原文引用。
- Matcher 已接入字段白名单式脱敏 Context Builder 和版本化 Prompt；服务层使用 Pydantic Structured Outputs，只在超时、5xx 或无效输出时重试一次，并保留模型、Prompt 版本、请求 ID 与 Token 用量。

## 开发原则

- AI 判断必须提供可追溯证据。
- 最终分数、排序和资格状态由后端确定性规则计算。
- 岗位版简历只能重组真实经历，不得新增技能、数字或成果。
- 所有用户数据按 `user_id` 隔离，越权访问统一返回 404。
