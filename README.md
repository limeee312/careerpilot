# 职航 CareerPilot

职航是一个面向应届生、社招求职者、转行人群及职业方向不明确求职者的 AI 求职决策与过程管理平台。

MVP 0.1 聚焦一条可验证的核心闭环：用户维护真实简历母版，导入 1–5 个岗位 JD，获得有证据支撑的匹配排序，生成不虚构事实的岗位版简历，并记录投递进度。

## 当前状态

项目处于 MVP 0.1 工程初始化阶段。开发任务按 `CP-001` 至 `CP-033` 顺序推进，每个任务独立提交并通过相应验收。

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

完整的一键启动、环境变量、数据库迁移和测试说明将在 Milestone 0 完成后补齐。

当前前端可单独启动：

```bash
cd frontend
npm install
npm run dev
```

访问 <http://localhost:3000>。

## 开发原则

- AI 判断必须提供可追溯证据。
- 最终分数、排序和资格状态由后端确定性规则计算。
- 岗位版简历只能重组真实经历，不得新增技能、数字或成果。
- 所有用户数据按 `user_id` 隔离，越权访问统一返回 404。
