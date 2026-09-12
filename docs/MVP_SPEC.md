# 职航 CareerPilot MVP 0.1 开发实施规格

**文档版本：** v1.0  
**产品阶段：** MVP 0.1  
**目标：** 完成第一条可真实使用、可部署、可测试的 AI 求职决策闭环  
**文档用途：** 产品、前端、后端、AI、测试人员共同开发基线

---

# 一、MVP 0.1 要解决什么问题

MVP 0.1 不试图一次完成 CareerPilot 全部 P0 功能。

第一版只验证一个核心假设：

> 求职者是否愿意提供自己的真实简历，并通过“简历 × JD”的 AI 匹配分析和针对性简历优化，更快地完成职位投递决策。

因此 MVP 0.1 的完整用户闭环定义为：

```text
注册 / 登录
    ↓
填写简历母版
    ↓
手动导入 1–5 个目标岗位 JD
    ↓
AI 解析岗位
    ↓
AI 进行多维度职位匹配
    ↓
系统按匹配度排序
    ↓
用户查看职位匹配详情
    ↓
选择某职位
    ↓
AI 生成针对性简历
    ↓
用户确认 / 编辑 / 保存
    ↓
创建投递记录
    ↓
查看投递状态
```

只要这条链路可以稳定运行，MVP 0.1 即成立。

---

# 二、MVP 0.1 功能范围

## 2.1 本版本必须实现

### 用户系统

支持：

- 邮箱注册；
- 邮箱 + 密码登录；
- 登出；
- 登录状态保持；
- 获取当前登录用户。

### 简历系统

支持：

- 创建唯一简历母版；
- 在线结构化填写；
- 保存；
- 再次进入后读取；
- 修改；
- 简历完整度提示；
- 查看岗位针对性简历；
- 编辑岗位针对性简历。

### 职位导入

第一版仅支持：

**人工粘贴 JD。**

一次分析支持：

**1–5 个职位。**

每个职位至少包含：

- 公司；
- 职位名称；
- JD；
- 职位链接，可选；
- 城市，可选。

### AI Job Parser

把非结构化 JD 转为结构化职位信息。

### AI Job Matcher

根据：

```text
简历母版
×
目标职位
```

计算多维匹配结果。

支持：

- 硬性条件判断；
- 分项评分；
- 总分；
- 排名；
- 优势；
- 差距；
- 证据；
- 投递建议。

### 简历针对性优化

根据：

```text
简历母版
+
Target JD
```

生成目标岗位版简历。

禁止覆盖母版。

### 投递管理

支持：

- 从职位详情创建投递记录；
- 手动创建投递；
- 修改当前阶段；
- 修改流程状态；
- 查看投递列表；
- 查看基础 Timeline。

---

## 2.2 本版本明确不实现

以下全部进入 MVP 0.2 / 0.3：

- 招聘官网自动抓取；
- Playwright；
- 公司招聘网站 Adapter；
- 职业方向推荐；
- 点赞 / 踩推荐系统；
- Reminder；
- 邮件 / 短信提醒；
- 完整投递漏斗；
- AI 面试；
- 简历 PDF 自动排版导出；
- 多模型切换；
- Agent；
- 模型训练；
- 自动投递；
- 手机 App。

代码结构可为这些功能预留扩展空间，但**禁止为了未来功能增加当前不必要的复杂度**。

---

# 三、MVP 0.1 成功标准

只有以下完整流程均可在生产环境成功完成，才视为 MVP 0.1 完成：

```text
① 用户注册成功

② 登录成功

③ 填写一份简历母版并保存

④ 刷新页面后简历仍存在

⑤ 修改简历并再次保存

⑥ 手动录入至少两个真实JD

⑦ 系统成功解析JD

⑧ 系统完成匹配分析

⑨ 两个岗位能够形成明确排名

⑩ 用户能够查看分项评分和证据

⑪ 用户选择岗位生成针对性简历

⑫ AI没有虚构简历事实

⑬ 用户修改并保存岗位版简历

⑭ 创建投递记录

⑮ 投递记录刷新后仍存在

⑯ 用户能够更新投递阶段
```

---

# 四、总体技术架构

## 4.1 技术选型

### Frontend

```text
Next.js
TypeScript
App Router
Tailwind CSS
```

Next.js 当前官方推荐的 App Router 使用文件系统定义页面与 Layout，并支持现代 React 架构，因此 MVP 直接采用 App Router，不再使用 Pages Router。

Node.js 开发环境至少满足当前 Next.js 官方安装要求；项目初始化时使用当时最新稳定版本并锁定 lockfile。当前官方安装文档给出的最低 Node.js 版本为 20.9。

### Backend

```text
Python
FastAPI
Pydantic
SQLAlchemy
Alembic
```

FastAPI 根据业务模块拆 Router，而不是所有 API 写入单文件。FastAPI 自带基于 OpenAPI 的接口描述，可直接用于开发阶段接口调试和前后端联调。

### Database

```text
PostgreSQL
```

### AI

第一版只接一个 Provider。

建议：

```text
OpenAI Responses API
+
Structured Outputs
```

模型名称不得写死在业务代码：

```text
OPENAI_MODEL=...
```

统一放环境变量。

Structured Outputs 要求模型按照明确的 JSON Schema 输出，非常适合职位解析、职位评分等必须返回稳定字段的产品场景。当前 Responses API 中结构化输出配置位于 `text.format`。

### Development

```text
Git
GitHub
Docker Compose
pytest
ESLint
```

---

# 五、系统逻辑架构

```text
┌────────────────────────────┐
│           Browser          │
└─────────────┬──────────────┘
              │ HTTPS
              ↓
┌────────────────────────────┐
│      Next.js Frontend      │
│                            │
│ 页面 / 表单 / 状态 / UI     │
└─────────────┬──────────────┘
              │ REST API
              ↓
┌────────────────────────────┐
│         FastAPI            │
│                            │
│ Auth                       │
│ Resume                     │
│ Jobs                       │
│ Job Matching               │
│ Resume Tailoring           │
│ Applications               │
└──────┬───────────────┬─────┘
       │               │
       ↓               ↓
┌──────────────┐   ┌─────────────┐
│ PostgreSQL   │   │ AI Service  │
└──────────────┘   └──────┬──────┘
                          │
                          ↓
                  ┌───────────────┐
                  │ OpenAI API    │
                  └───────────────┘
```

---

# 六、项目目录结构

建议 GitHub 最终目录：

```text
careerpilot/
│
├── frontend/
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   └── register/
│   │   │
│   │   ├── (app)/
│   │   │   ├── layout.tsx
│   │   │   ├── dashboard/
│   │   │   ├── resumes/
│   │   │   ├── job-match/
│   │   │   ├── jobs/
│   │   │   └── applications/
│   │   │
│   │   ├── layout.tsx
│   │   └── page.tsx
│   │
│   ├── components/
│   │   ├── layout/
│   │   ├── resume/
│   │   ├── jobs/
│   │   ├── match/
│   │   ├── application/
│   │   └── ui/
│   │
│   ├── lib/
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   ├── validators.ts
│   │   └── types.ts
│   │
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   │
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── resumes.py
│   │   │       ├── jobs.py
│   │   │       ├── job_match.py
│   │   │       ├── resume_tailor.py
│   │   │       └── applications.py
│   │   │
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   │
│   │   ├── ai/
│   │   │   ├── client.py
│   │   │   ├── context_builder.py
│   │   │   ├── job_parser/
│   │   │   ├── job_matcher/
│   │   │   └── resume_tailor/
│   │   │
│   │   ├── auth/
│   │   └── exceptions/
│   │
│   ├── migrations/
│   ├── tests/
│   └── pyproject.toml
│
├── docs/
│   ├── PRD.md
│   ├── MVP_SPEC.md
│   ├── API.md
│   ├── DATABASE.md
│   └── AI_SKILLS.md
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
└── LICENSE
```

---

# 七、核心数据模型

所有业务主键统一使用 UUID。

所有表至少包含：

```text
id
created_at
updated_at
```

时间统一：

```text
数据库：UTC
前端：根据用户时区显示
```

---

# 八、User

表：

```text
users
```

字段：

| 字段 | 类型 | 约束 |
|---|---|---|
| id | UUID | PK |
| email | VARCHAR | UNIQUE, NOT NULL |
| password_hash | VARCHAR | NOT NULL |
| name | VARCHAR | NULL |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |

邮箱存储前：

```text
trim
lowercase
```

密码：

- 禁止保存明文；
- 后端完成安全哈希；
- API 永不返回 `password_hash`。

---

# 九、Resume Master 数据设计

原则：

> 简历不是长文本，而是结构化数据。

关系：

```text
User
1
↓
1
ResumeMaster
```

一个用户只允许拥有一个当前母版。

---

# 十、resume_masters

```text
id
user_id
name
phone
email
city
job_status
summary
created_at
updated_at
```

其中：

`user_id`：

```text
UNIQUE
FOREIGN KEY users.id
```

---

# 十一、resume_educations

```text
id
resume_master_id
school
degree
major
start_date
end_date
gpa
courses
description
sort_order
```

一个 Resume Master：

```text
1 → N Education
```

---

# 十二、resume_experiences

统一保存：

```text
WORK
INTERNSHIP
CAMPUS
OTHER
```

字段：

```text
id
resume_master_id
experience_type
organization
position
start_date
end_date
description
achievements
sort_order
```

其中：

`description`：

用户填写原始职责。

`achievements`：

用户填写结果或成果。

不得提前把 AI 润色后的文本写回这里。

---

# 十三、resume_projects

```text
id
resume_master_id
name
role
start_date
end_date
background
description
achievements
sort_order
```

---

# 十四、resume_skills

```text
id
resume_master_id
skill_name
skill_category
proficiency
sort_order
```

`proficiency`：

MVP 可为空。

不要要求用户一定填写：

```text
熟练 / 精通
```

避免制造虚假精确性。

---

# 十五、Job Import Batch

一次职位比较称为一个：

```text
JobMatchBatch
```

例如用户想比较腾讯的 5 个职位：

```text
Batch A
├── Job1
├── Job2
├── Job3
├── Job4
└── Job5
```

表：

```text
job_match_batches
```

字段：

```text
id
user_id
name
status
created_at
updated_at
```

status：

```text
DRAFT
PROCESSING
COMPLETED
PARTIAL_FAILED
FAILED
```

---

# 十六、Jobs

```text
jobs
```

字段：

```text
id
batch_id
user_id

company_name
title
location
department
source_url

raw_jd

responsibilities JSONB
requirements JSONB
hard_requirements JSONB
preferred_requirements JSONB
skill_tags JSONB
business_tags JSONB

parse_status

created_at
updated_at
```

其中：

```text
raw_jd
```

永远保留用户粘贴的原始文本。

AI 解析结果不能覆盖原文。

---

# 十七、Job Match Result

```text
job_match_results
```

字段：

```text
id
user_id
job_id
resume_master_id

eligibility_status
eligibility_reasons JSONB

total_score

strengths JSONB
gaps JSONB
recommendation
recommendation_level

resume_snapshot JSONB
job_snapshot JSONB

ai_model
prompt_version

created_at
```

必须保存：

```text
resume_snapshot
job_snapshot
```

原因：

如果用户一个月后修改母版，历史匹配结果不能随之失去依据。

---

# 十八、Job Match Dimension

```text
job_match_dimensions
```

字段：

```text
id
match_result_id

dimension
score
max_score

reason
evidence JSONB
```

dimension 枚举：

```text
EXPERIENCE
ABILITY
SKILL
EDUCATION
INDUSTRY
PREFERENCE
```

---

# 十九、Resume Version

```text
resume_versions
```

字段：

```text
id
user_id
resume_master_id
job_id

name

content JSONB

source_resume_snapshot JSONB
source_job_snapshot JSONB

ai_generated
ai_model
prompt_version

created_at
updated_at
```

例如：

```text
腾讯 - 产品运营
```

---

# 二十、Application

```text
applications
```

字段：

```text
id
user_id
job_id
resume_version_id

company_name
job_title
job_url

applied_at

current_stage
current_round

process_status

note

created_at
updated_at
```

---

# 二十一、Application Event

```text
application_events
```

字段：

```text
id
application_id

event_type
custom_event_name
round_no

occurred_at

outcome
note

created_at
```

event_type：

```text
APPLICATION
RESUME_SCREEN
ASSESSMENT
WRITTEN_TEST
AI_INTERVIEW
INTERVIEW
OFFER
OTHER
```

---

# 二十二、投递状态模型

不得把招聘流程写死。

需要两个维度：

## current_stage

表示：

> 当前 / 最后经历的环节。

例如：

```text
APPLICATION
RESUME_SCREEN
ASSESSMENT
WRITTEN_TEST
AI_INTERVIEW
INTERVIEW
OFFER
```

## process_status

表示：

> 整个申请是否还继续。

枚举：

```text
ACTIVE
REJECTED
OFFER
WITHDRAWN
```

例如：

```text
current_stage = INTERVIEW
current_round = 1
process_status = REJECTED
```

前端展示：

```text
一面淘汰
```

---

# 二十三、数据库关系

核心 ER：

```text
User
│
├── 1 ResumeMaster
│      ├── N Education
│      ├── N Experience
│      ├── N Project
│      ├── N Skill
│      └── N ResumeVersion
│
├── N JobMatchBatch
│      └── N Job
│             └── 1 JobMatchResult
│                    └── N JobMatchDimension
│
└── N Application
       └── N ApplicationEvent
```

---

# 二十四、认证方案

MVP 使用：

```text
Email
+
Password
+
JWT Session
```

推荐：

短期 Access Token。

生产环境优先存：

```text
HttpOnly
Secure
SameSite
Cookie
```

而不是 LocalStorage。

所有受保护接口必须经过：

```text
get_current_user
```

验证。

例如：

```text
GET /resume/master
```

不能接受前端传：

```text
user_id=123
```

然后直接查询。

必须：

```text
JWT
↓
current_user.id
↓
数据库查询
```

从根本上避免访问其他用户的数据。

---

# 二十五、统一 API 规范

API Prefix：

```text
/api/v1
```

成功返回：

```json
{
  "data": {},
  "meta": {}
}
```

普通错误：

```json
{
  "error": {
    "code": "RESUME_NOT_FOUND",
    "message": "尚未创建简历母版"
  }
}
```

HTTP Status 正确使用：

```text
200 success
201 created
204 deleted
400 validation/business error
401 unauthenticated
403 unauthorized
404 not found
409 conflict
422 validation error
500 internal error
502 upstream AI service error
```

---

# 二十六、Authentication API

## POST /api/v1/auth/register

Request：

```json
{
  "email": "user@example.com",
  "password": "ExamplePassword123"
}
```

Response：

```json
{
  "data": {
    "id": "uuid",
    "email": "user@example.com"
  }
}
```

校验：

- Email 格式；
- Email 唯一；
- 密码最低长度；
- 密码不可为空。

---

## POST /api/v1/auth/login

```json
{
  "email": "user@example.com",
  "password": "ExamplePassword123"
}
```

成功：

创建认证 Cookie。

失败：

```text
AUTH_INVALID_CREDENTIALS
```

---

## POST /api/v1/auth/logout

清理认证 Cookie。

---

## GET /api/v1/auth/me

返回：

```json
{
  "data": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "..."
  }
}
```

---

# 二十七、Resume API

## GET /api/v1/resume/master

如果没有：

```json
{
  "data": null
}
```

不要返回 500。

---

## PUT /api/v1/resume/master

创建和更新统一使用 Upsert。

Request 示例：

```json
{
  "basic_info": {
    "name": "张三",
    "phone": "13800000000",
    "email": "user@example.com",
    "city": "杭州",
    "job_status": "求职中",
    "summary": ""
  },

  "education": [
    {
      "school": "XX大学",
      "degree": "硕士",
      "major": "应用语言学",
      "start_date": "2024-09",
      "end_date": "2027-06",
      "gpa": "",
      "courses": "",
      "description": ""
    }
  ],

  "experiences": [],

  "projects": [],

  "skills": []
}
```

操作要求：

整个保存行为在一个 Database Transaction 内完成。

任何一部分失败：

全部回滚。

---

# 二十八、简历母版前端页面

Route：

```text
/resumes/master/edit
```

实现位于 Next.js `(app)` 路由组中；路由组名称不进入公开 URL。

布局：

```text
┌─────────────────────────────────────┐
│ 编辑简历母版                  保存 │
├──────────┬──────────────────────────┤
│ 基本信息 │                          │
│ 教育经历 │      当前编辑区域         │
│ 实习经历 │                          │
│ 项目经历 │                          │
│ 技能     │                          │
├──────────┴──────────────────────────┤
│                简历完整度 80%        │
└─────────────────────────────────────┘
```

---

# 二十九、Resume Form 交互要求

用户新增经历：

```text
+ 添加实习经历
```

生成新的 Experience Card。

支持：

```text
编辑
删除
上下调整顺序
```

删除已有内容时必须二次确认。

保存按钮：

```text
正常
↓
保存中...
↓
保存成功 ✓
```

保存失败：

不能丢失当前表单。

---

# 三十、简历完整度

MVP 使用简单规则，不使用 AI。

例如：

```text
基本信息            10%
至少1段教育经历      20%
至少1段工作/实习      25%
至少1段项目经历       20%
至少3项技能           10%
经历有成果描述        15%
```

前端显示：

```text
完整度 80%
```

但：

> 完整度不能阻止用户进行职位匹配。

如果简历严重缺失，只提示：

```text
简历信息较少，可能影响匹配结果准确性。
```

---

# 三十一、职位导入页面

Route：

```text
/job-match/new
```

该页面在 Next.js `app/(app)` 路由组内实现；`(app)` 仅用于组织受保护页面，
不会出现在浏览器 URL 中。

首版只做：

```text
手动粘贴职位
```

页面：

```text
新建职位匹配

公司名称
[                    ]

职位 1
职位名称 [          ]
城市     [          ]
职位链接 [          ]
JD
[                    ]
[                    ]

+ 添加另一个职位

最多5个

[开始分析]
```

---

# 三十二、职位输入校验

每个职位必须有：

```text
company_name
title
raw_jd
```

JD 最低字符数建议：

```text
>= 50
```

防止：

```text
JD = “产品经理”
```

直接进入 AI。

最多：

```text
5 Jobs / Batch
```

---

# 三十三、创建职位 Batch API

## POST /api/v1/job-match/batches

Request：

```json
{
  "name": "腾讯产品运营岗位比较",
  "jobs": [
    {
      "company_name": "腾讯",
      "title": "产品运营",
      "location": "深圳",
      "source_url": "",
      "raw_jd": "..."
    },
    {
      "company_name": "腾讯",
      "title": "用户运营",
      "location": "深圳",
      "source_url": "",
      "raw_jd": "..."
    }
  ]
}
```

后端流程：

```text
创建 Batch
↓
创建所有 Job
↓
status = DRAFT
↓
返回 Batch ID
```

---

# 三十四、启动职位匹配

## POST /api/v1/job-match/batches/{batch_id}/analyze

前置条件：

```text
当前用户存在ResumeMaster
+
Batch至少1个Job
```

否则：

```text
RESUME_REQUIRED
```

或者：

```text
BATCH_EMPTY
```

---

# 三十五、AI Job Parser

每个 Job 首先进入：

```text
Job Parser Skill
```

目的不是评分。

目的只是把 JD 转成统一结构。

Input：

```json
{
  "title": "...",
  "raw_jd": "..."
}
```

AI Context 不需要发送：

```text
姓名
电话
邮箱
```

---

# 三十六、Job Parser 输出 Schema

必须返回：

```json
{
  "role_summary": "string",
  "responsibilities_summary": [
    "string"
  ],
  "requirements": [
    {
      "requirement_key": "R1",
      "requirement_type": "HARD",
      "dimension": null,
      "requirement_text": "本科及以上学历",
      "source_quote": "本科及以上学历",
      "importance": 1
    }
  ],
  "business_domains": [
    "string"
  ],
  "tools": [
    "string"
  ],
  "ambiguous_points": [
    "string"
  ]
}
```

该逐条 Requirement 契约取代早期的聚合式
`hard_requirements / preferred_requirements / abilities / skills` 设计，
以 `docs/AI_SKILLS.md` 的 `job_parser_v1` 为最终工程基线。

其中：

- `HARD` 的 `dimension` 必须为 `null`；
- 非 `HARD` 必须映射一个主要能力维度；
- `requirement_key` 必须从 `R1` 开始连续且唯一；
- `source_quote` 必须能在原始 JD 中定位；
- Parser 不输出总分、推荐等级或候选人判断。

所有数组：

没有内容时：

```json
[]
```

禁止：

```text
null
```

除非 Schema 明确定义允许 null。

---

# 三十七、Job Parser 核心 Prompt 规则

系统指令必须明确：

```text
你是招聘职位结构化解析器。

只依据输入JD提取信息。

禁止增加JD中没有出现的硬性要求。

区分：
hard requirement
与
preferred requirement。

“优先”“加分”“熟悉更佳”
不得识别为hard requirement。

输出必须符合给定Schema。
```

---

# 三十八、AI Context Builder

所有发送给 AI 的简历先经过：

```text
AIContextBuilder
```

去除：

```text
姓名
手机号
个人邮箱
精确地址
其他非匹配所需身份信息
```

最终 AI 接收：

```text
Education
Experience
Projects
Skills
Summary
```

这既减少无关 Token，也降低隐私暴露。

---

# 三十九、职位匹配算法

匹配分两阶段。

## Stage A：Eligibility Gate

先判断：

```text
用户是否明显违反硬性条件
```

输出：

```text
PASS
WARN
FAIL
```

### PASS

没有发现明确冲突。

### WARN

存在无法确认或可能不满足的条件。

例如：

```text
JD：
英语可作为工作语言

Resume：
没有语言能力信息
```

### FAIL

存在明确冲突。

例如：

```text
JD：
仅2026届毕业生

Resume：
明确为2027届
```

---

# 四十、FAIL 仍然允许查看能力匹配

不能简单返回：

```text
0分
```

应展示：

```text
硬性条件：FAIL

能力匹配度：89

总体建议：
不建议优先投递
```

因为：

> Eligibility 与 Ability Fit 是两个不同概念。

---

# 四十一、Match Score Rubric

第一版固定：

| Dimension | 满分 |
|---|---:|
| Experience | 30 |
| Ability | 25 |
| Skill | 15 |
| Education | 10 |
| Industry | 10 |
| Preference | 10 |
| Total | 100 |

如果 MVP 0.1 尚未收集 Preference：

Preference 处理方式：

```text
默认记 5 / 10
```

并在 UI 标注：

```text
未填写求职偏好，本项采用中性分。
```

后续 P0 Career Profile 上线后替换。

---

# 四十二、Matcher Structured Output

模型必须返回：

```json
{
  "eligibility": {
    "status": "PASS",
    "reasons": []
  },

  "dimensions": {
    "experience": {
      "score": 24,
      "reason": "...",
      "evidence": [
        {
          "resume_evidence": "...",
          "job_requirement": "..."
        }
      ]
    },

    "ability": {
      "score": 21,
      "reason": "...",
      "evidence": []
    },

    "skill": {
      "score": 11,
      "reason": "...",
      "evidence": []
    },

    "education": {
      "score": 8,
      "reason": "...",
      "evidence": []
    },

    "industry": {
      "score": 7,
      "reason": "...",
      "evidence": []
    }
  },

  "strengths": [
    "..."
  ],

  "gaps": [
    {
      "gap": "...",
      "importance": "HIGH | MEDIUM | LOW",
      "suggestion": "..."
    }
  ],

  "recommendation": "..."
}
```

**AI 不返回 `total_score`。**

---

# 四十三、总分由后端计算

后端：

```text
total_score
=
experience
+
ability
+
skill
+
education
+
industry
+
preference
```

必须校验：

```text
0 <= experience <= 30
0 <= ability <= 25
...
```

如果 AI 返回：

```text
experience = 34
```

Schema / Service 必须拒绝。

不得偷偷保存错误值。

---

# 四十四、为什么总分不能让 AI 算

因为产品必须保证：

```text
相同评分规则
+
相同分项结果
=
相同总分
```

不能出现：

```text
24 + 21 + 11 + 8 + 7 + 5
```

AI 却输出：

```text
82
```

这种错误。

---

# 四十五、AI Evidence 原则

每项重要判断应优先返回：

```text
Resume Evidence
+
JD Requirement
```

例如：

```text
判断：
数据分析能力匹配度高

JD依据：
负责业务数据分析并通过数据驱动运营策略优化。

简历证据：
梳理近三年需求量及全流程耗时数据，搭建数据分析体系。
```

如果简历里没有证据：

AI 必须写：

```text
未发现相关证据
```

而不是自行推断。

---

# 四十六、Match Result 推荐等级

后端根据 Total Score 生成：

```text
90–100
A+ 强烈推荐

80–89
A 推荐

70–79
B 可考虑

60–69
C 匹配一般

<60
D 不优先
```

但 Eligibility = FAIL 时：

无论能力分数多高：

```text
recommendation_level = BLOCKED
```

页面显示：

```text
能力匹配较高，但存在明确硬性条件冲突。
```

---

# 四十七、职位匹配处理流程

```text
POST analyze
↓
验证当前用户
↓
读取ResumeMaster
↓
建立脱敏Resume Snapshot
↓
for each Job
    ↓
Job Parser
    ↓
保存结构化Job
    ↓
Job Matcher
    ↓
Structured Output验证
    ↓
后端计算Total Score
    ↓
保存MatchResult
↓
按total_score DESC排序
↓
Batch = COMPLETED
```

---

# 四十八、失败策略

5 个职位中：

```text
4成功
1失败
```

不能整批失败。

Batch：

```text
PARTIAL_FAILED
```

前端：

```text
4个岗位分析成功
1个岗位分析失败
[重新分析]
```

---

# 四十九、AI Retry

以下情况允许自动 retry 1 次：

- API timeout；
- transient server error；
- Structured Output validation failure。

超过一次：

记录失败。

禁止无限 retry。

---

# 五十、匹配 Loading UX

AI 分析不是即时操作。

前端点击：

```text
开始分析
```

立即进入：

```text
正在分析岗位...
```

按 Job 展示：

```text
产品运营
✓ JD解析完成
✓ 匹配完成

用户运营
✓ JD解析完成
● 正在进行匹配

AI产品经理
○ 等待分析
```

用户不能因为没有反馈而误以为页面卡死。

---

# 五十一、匹配结果页面

Route：

```text
/app/job-match/[batchId]
```

默认按：

```text
total_score DESC
```

排序。

展示：

```text
匹配结果

1 产品运营
  91分
  A+ 强烈推荐
  硬性条件 PASS
  [查看详情]

2 用户运营
  86分
  A 推荐
  硬性条件 PASS

3 AI产品经理
  79分
  B 可考虑
  硬性条件 WARN
```

如果只有一个岗位：

仍正常显示。

不要强制“Top 5”。

---

# 五十二、职位详情页面

Route：

```text
/app/jobs/[jobId]
```

页面必须包含：

```text
职位名称
公司
城市

Eligibility

总匹配分

六维评分

优势

主要差距

简历证据

职位核心要求

总体建议
```

底部主 CTA：

```text
[针对该职位优化简历]
```

次 CTA：

```text
[创建投递记录]
```

---

# 五十三、针对性简历 AI

Route：

```text
/app/jobs/[jobId]/tailor
```

前端点击：

```text
生成针对性简历
```

后端读取：

```text
Resume Master Snapshot
+
Job Snapshot
```

---

# 五十四、Resume Tailor 核心原则

AI 允许：

```text
重写
重新排序
压缩
强化
改变措辞
突出相关内容
```

AI 禁止：

```text
创造新公司
创造新项目
创造新技能
创造新数字
创造新成果
修改学校
修改学位
修改时间
修改个人身份信息
```

---

# 五十五、需要保持完全不变的字段

以下字段不得交给 AI 改写：

```text
姓名
电话
邮箱

学校名称
学历
专业
教育起止时间

公司名称
职位名称
经历起止时间

项目名称（除非用户自行修改）
```

AI 主要修改：

```text
Description
Achievements
Summary
Skill ordering
Experience ordering
Project ordering
```

---

# 五十六、Resume Tailor 输出

必须采用结构化输出：

```json
{
  "summary": "...",

  "experiences": [
    {
      "source_id": "原Experience UUID",
      "description": "...",
      "achievements": "..."
    }
  ],

  "projects": [
    {
      "source_id": "原Project UUID",
      "description": "...",
      "achievements": "..."
    }
  ],

  "skills": [
    {
      "source_skill_id": "uuid",
      "skill_name": "Excel"
    }
  ],

  "improvement_suggestions": [
    {
      "gap": "SQL",
      "suggestion": "若真实掌握SQL，可补充相关项目；若尚未掌握，建议后续学习。",
      "must_not_add_without_evidence": true
    }
  ]
}
```

使用：

```text
source_id
```

确保 AI 输出的每段内容都能追溯到原始经历。

---

# 五十七、防止 AI 虚构的后端检查

如果 AI 返回新的：

```text
Company
School
Skill
```

而 ResumeMaster 中不存在：

默认拒绝写入。

例如：

Resume Master：

```text
Excel
Python
```

AI 返回：

```text
SQL
```

系统不能直接把 SQL 加到简历。

应该转入：

```text
Improvement Suggestion
```

---

# 五十八、简历优化页面

使用左右对照：

```text
┌──────────────────────┬──────────────────────┐
│ 原简历               │ 针对性简历           │
│                      │                      │
│ 原实习经历           │ AI优化后的经历        │
│                      │ 可手动编辑            │
│                      │                      │
└──────────────────────┴──────────────────────┘

岗位差距与提升建议

[重新生成] [保存为岗位版简历]
```

---

# 五十九、保存 Resume Version

## POST /api/v1/resume/versions

只有用户主动点击：

```text
保存
```

才写数据库。

AI 生成结果先作为：

```text
draft
```

不要自动保存正式版本。

---

# 六十、Resume Library

Route：

```text
/resumes
```

实现位于 Next.js `(app)` 路由组中；路由组名称不进入公开 URL。

显示：

```text
⭐ 简历母版
最后修改 09-08
[编辑]

针对性简历

腾讯 · 产品运营
创建 09-08
[查看] [编辑]

阿里 · 用户运营
创建 09-09
[查看] [编辑]
```

---

# 六十一、投递管理

Route：

```text
/app/applications
```

MVP 0.1 不做复杂 Kanban。

使用：

```text
Table / List
```

字段：

```text
公司
职位
当前阶段
状态
投递日期
最后更新
```

支持筛选：

```text
全部
进行中
已淘汰
Offer
主动放弃
```

---

# 六十二、创建投递

## POST /api/v1/applications

Request：

```json
{
  "job_id": "uuid",
  "resume_version_id": "uuid",
  "company_name": "腾讯",
  "job_title": "产品运营",
  "job_url": "...",
  "applied_at": "2026-09-08",
  "note": ""
}
```

创建时自动：

```text
current_stage = APPLICATION
process_status = ACTIVE
```

同时自动创建：

```text
ApplicationEvent
event_type = APPLICATION
```

---

# 六十三、投递详情

Route：

```text
/app/applications/[id]
```

顶部：

```text
腾讯 · 产品运营

进行中

当前阶段：
一面
```

下面：

```text
Timeline
```

例如：

```text
09-08
已投递

09-10
在线测评

09-15
一面
```

---

# 六十四、添加 Event

## POST /api/v1/applications/{id}/events

Request：

```json
{
  "event_type": "INTERVIEW",
  "round_no": 1,
  "occurred_at": "2026-09-15T14:00:00",
  "outcome": "PENDING",
  "note": ""
}
```

系统同时更新：

```text
Application.current_stage
Application.current_round
```

---

# 六十五、结束流程

用户可以选择：

```text
流程终止
拿到Offer
主动放弃
```

更新：

```text
process_status
```

终止时：

要求用户选择当前阶段。

例如：

```text
当前阶段：INTERVIEW
Round：1
结果：REJECTED
```

前端：

```text
一面淘汰
```

---

# 六十六、Dashboard MVP

MVP 0.1 首页可以只做极简版：

```text
累计投递
进行中
流程终止
Offer
```

以及：

```text
最近投递
```

完整 Funnel 和 Reminder 留到 MVP 0.2。

避免首页阻塞核心闭环。

---

# 六十七、Dashboard API

## GET /api/v1/dashboard

Response：

```json
{
  "data": {
    "overview": {
      "total": 12,
      "active": 5,
      "rejected": 5,
      "offer": 1,
      "withdrawn": 1
    },

    "recent_applications": []
  }
}
```

---

# 六十八、前端全局状态要求

所有数据页面必须设计四种状态：

## Loading

例如：

```text
Skeleton
```

## Empty

例如：

```text
你还没有创建简历母版
[创建简历]
```

## Error

```text
加载失败
[重新加载]
```

## Success

正常展示。

禁止：

数据库没有数据时：

页面空白。

---

# 六十九、表单校验原则

前端：

负责即时体验。

后端：

负责最终可信校验。

不能只依赖前端。

例如：

前端限制：

```text
最多5个职位
```

后端仍必须验证：

```python
len(jobs) <= 5
```

---

# 七十、AI Service 抽象

禁止在：

```text
job_match.py API Router
```

中直接调用 OpenAI。

正确：

```text
Router
↓
JobMatchService
↓
AIJobMatcher
↓
AIClient
```

---

# 七十一、AI Client

接口建议抽象为：

```python
class AIClient:
    async def generate_structured(
        self,
        *,
        system_prompt,
        input_data,
        schema,
        model=None
    ):
        ...
```

以后更换模型时：

业务代码不需要重构。

---

# 七十二、Prompt Version

每一个 AI Skill 必须有明确版本：

```text
job_parser_v1
job_matcher_v1
resume_tailor_v1
```

数据库保存：

```text
prompt_version
```

原因：

未来修改 Prompt 后，需要知道历史结果是哪个版本生成的。

---

# 七十三、AI 日志

禁止记录完整敏感简历到普通应用日志。

建议记录：

```text
request_id
user_id
skill
model
latency
status
token_usage
error_type
prompt_version
```

不要记录：

```text
手机号
邮箱
完整简历正文
```

---

# 七十四、AI 超时

单次 AI 调用设置超时。

超时后：

```text
AI_TIMEOUT
```

前端：

```text
分析暂时未完成，请重新尝试。
```

不要返回：

```text
Internal Server Error
```

给普通用户。

---

# 七十五、AI 成本保护

MVP 即使只有测试用户，也建议：

每个用户：

```text
限制单个Batch最多5个Job
```

同时增加服务端 rate limit / usage protection。

否则用户反复：

```text
重新生成
重新生成
重新生成
```

会快速消耗 API 成本。

---

# 七十六、核心 API 清单

Authentication：

```text
POST   /auth/register
POST   /auth/login
POST   /auth/logout
GET    /auth/me
```

Resume：

```text
GET    /resume/master
PUT    /resume/master

GET    /resume/versions
POST   /resume/versions
GET    /resume/versions/{id}
PUT    /resume/versions/{id}
DELETE /resume/versions/{id}
```

Job Matching：

```text
POST   /job-match/batches
GET    /job-match/batches/{id}
POST   /job-match/batches/{id}/analyze
GET    /job-match/batches/{id}/results

GET    /jobs/{id}
GET    /jobs/{id}/match
```

Resume Tailor：

```text
POST   /jobs/{id}/resume-tailor
```

Application：

```text
POST   /applications
GET    /applications
GET    /applications/{id}
PUT    /applications/{id}

POST   /applications/{id}/events
PUT    /application-events/{id}
DELETE /application-events/{id}
```

Dashboard：

```text
GET    /dashboard
```

---

# 七十七、权限原则

所有数据对象都必须检查：

```text
object.user_id == current_user.id
```

例如用户请求：

```text
GET /jobs/abc
```

即使：

```text
abc
```

真实存在，但属于其他用户：

返回：

```text
404
```

不要告诉攻击者：

```text
这个Job存在但不是你的
```

---

# 七十八、环境变量

`.env.example`：

```text
# Backend

APP_ENV=development

DATABASE_URL=

JWT_SECRET=
JWT_EXPIRE_MINUTES=

FRONTEND_URL=http://localhost:3000

OPENAI_API_KEY=
OPENAI_MODEL=

# Frontend

NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

`.env`：

必须进入：

```text
.gitignore
```

---

# 七十九、本地开发启动

开发人员应能做到：

```text
git clone ...
```

然后按照 README：

```text
① 安装前端依赖
② 创建Python虚拟环境
③ 安装后端依赖
④ 配置.env
⑤ 启动PostgreSQL
⑥ 执行migration
⑦ 启动FastAPI
⑧ 启动Next.js
```

最终：

```text
Frontend
http://localhost:3000

Backend
http://localhost:8000
```

FastAPI 开发环境同时提供自动生成的 API 文档，供联调使用。

---

# 八十、Database Migration

禁止团队成员手工改生产数据库表。

使用：

```text
Alembic Migration
```

例如：

```text
001_create_users
002_create_resume_tables
003_create_job_tables
004_create_match_tables
005_create_application_tables
```

数据库结构修改必须：

```text
Schema Change
+
Migration
+
Code
```

一起提交。

---

# 八十一、测试策略

测试分为四层。

## Unit Test

重点：

```text
score calculation
eligibility logic
resume validation
application status
```

例如：

```text
Experience 25
Ability 20
Skill 10
Education 8
Industry 7
Preference 5

Total必须为75
```

---

# 八十二、API Integration Test

至少覆盖：

```text
注册
登录
简历保存
创建Batch
AI结果保存
创建ResumeVersion
创建Application
添加Event
```

AI 测试中默认 Mock Provider。

不要每次运行 pytest 都真实调用模型 API。

---

# 八十三、AI Contract Test

单独建立真实模型测试。

目标：

验证：

```text
Schema是否稳定
分数是否合法
Evidence是否来自输入
是否出现虚构内容
```

不进入每次 CI。

---

# 八十四、E2E Test

最关键的一条：

```text
Register
↓
Login
↓
Create Resume
↓
Create Job Batch
↓
Run Match
↓
Open Job
↓
Tailor Resume
↓
Save Version
↓
Create Application
```

整条链路必须通过。

如果未来采用 Playwright 做浏览器端 E2E，它支持 Chromium、Firefox 和 WebKit，并提供页面交互、断言和自动等待能力。

---

# 八十五、AI Eval 数据集

单独建立：

```text
tests/evals/
```

至少准备：

```text
20个真实或脱敏简历
+
每份3–5个岗位
```

人工标注：

```text
Best Match
Top 3
明显不适合职位
Hard Gate
关键优势
关键缺口
```

---

# 八十六、职位匹配 Eval 指标

MVP 不重点验证：

```text
AI给了87还是88
```

重点验证：

### Ranking

人工认为：

```text
A > B > C
```

AI 是否基本一致。

### Hard Gate Accuracy

明确硬性条件：

AI 是否判断正确。

### Evidence Grounding

AI 的优势判断：

能否找到真实简历证据。

### Hallucination Rate

是否出现：

```text
简历没有
AI却声称用户具有
```

的经历。

---

# 八十七、上线前 AI 最低标准

建议：

```text
Hard Gate重大错误 = 0
```

测试样本中不得出现明显：

```text
2027届
→
AI说满足仅2026届岗位
```

这类错误。

同时：

针对性简历测试集：

不得新增未经用户提供的：

```text
公司
学历
项目
技能
成果数字
```

---

# 八十八、错误码

统一业务错误至少包括：

```text
AUTH_EMAIL_EXISTS
AUTH_INVALID_CREDENTIALS

RESUME_REQUIRED
RESUME_INVALID

JOB_INVALID
JOB_LIMIT_EXCEEDED

BATCH_NOT_FOUND
BATCH_EMPTY

AI_TIMEOUT
AI_INVALID_OUTPUT
AI_PROVIDER_ERROR

MATCH_NOT_FOUND

RESUME_VERSION_NOT_FOUND

APPLICATION_NOT_FOUND

FORBIDDEN
```

---

# 八十九、前端错误文案

技术错误：

```text
AI_INVALID_OUTPUT
```

不能原样展示给用户。

用户看到：

```text
这次分析没有成功完成，请重新尝试。
```

开发环境日志保留真实错误。

---

# 九十、性能要求

MVP 不追求极端高并发。

但必须达到：

普通数据库页面：

```text
目标 < 1秒获得接口响应
```

AI 页面：

必须立即进入 Loading / Progress 状态。

5 个岗位可采用受控并发。

不要一次无限并发调用模型。

---

# 九十一、隐私要求

简历属于高敏感个人资料。

因此 MVP 至少落实：

```text
HTTPS
密码哈希
用户数据隔离
API Key服务端保存
AI前脱敏
生产数据库禁止公开访问
日志禁止打印完整简历
```

另外 UI 应明确告诉用户：

> AI 分析将使用简历中的教育、经历、项目和技能信息；姓名、电话、邮箱等与匹配无关的信息不会发送用于职位匹配。

---

# 九十二、Git 工作流

默认主分支：

```text
main
```

开发从 Feature Branch 进行：

```text
feature/auth
feature/resume-master
feature/job-input
feature/job-parser
feature/job-matcher
feature/resume-tailor
feature/applications
```

Bug：

```text
fix/...
```

---

# 九十三、Commit 示例

推荐：

```text
feat(auth): add email registration

feat(resume): implement resume master form

feat(match): add structured job matching

fix(match): enforce score upper bounds

test(application): add application event tests

docs(api): document resume endpoints
```

禁止：

```text
update
修改
test123
finish
```

---

# 九十四、Pull Request 最低要求

PR 必须写：

```text
What

做了什么。

Why

为什么这样设计。

How to test

如何验证。

Screenshots

如果涉及UI。
```

合并前：

```text
lint pass
tests pass
migration valid
no secrets
```

---

# 九十五、README 最终至少包含

```text
CareerPilot介绍

产品截图

核心能力

Architecture

Technology Stack

Project Structure

Local Development

Environment Variables

Database Migration

Testing

AI Architecture

Roadmap

License
```

招聘者进入 GitHub 后：

**一分钟内应该能理解这个产品解决什么问题，以及技术上做了什么。**

---

# 九十六、具体开发顺序

## Milestone 0：工程初始化

完成：

```text
GitHub仓库
Next.js
FastAPI
PostgreSQL
Docker Compose
CORS
.env.example
CI基本配置
```

验收：

```text
Frontend正常打开
Backend /health 返回200
Database连接成功
```

---

# 九十七、Milestone 1：Auth

完成：

```text
User table
Register
Login
Logout
Auth middleware
Protected route
```

验收：

```text
未登录不能访问/app
登录后正常访问
用户不能读取别人数据
```

---

# 九十八、Milestone 2：Resume Master

完成：

```text
Resume tables
Resume API
Resume Editor
Resume Library
完整度
```

验收：

```text
创建
刷新
编辑
再次刷新
数据完全一致
```

这是第一个重要里程碑。

---

# 九十九、Milestone 3：Manual Jobs

完成：

```text
Batch
Job
1–5职位输入
Job Parser
```

验收：

真实 JD：

```text
能够保存原文
能够生成结构化字段
```

---

# 一百、Milestone 4：Job Matcher

完成：

```text
Eligibility
Dimensions
Evidence
Total Score
Ranking
Result Page
Detail Page
```

验收：

输入：

```text
1 Resume
+
3 Jobs
```

系统能明确：

```text
1
2
3
```

排序。

---

# 一百零一、Milestone 5：Resume Tailor

完成：

```text
Tailor Skill
Truth Constraint
Draft
Preview
Edit
Save Version
Resume Library
```

验收：

母版：

```text
不发生改变。
```

岗位版：

```text
成功保存。
```

AI：

```text
没有新增不存在的事实。
```

---

# 一百零二、Milestone 6：Application

完成：

```text
Application List
Application Detail
Timeline
Create Event
Update Status
```

验收：

完整经历：

```text
投递
↓
测评
↓
一面
↓
淘汰
```

能正确保存和呈现。

---

# 一百零三、Milestone 7：Basic Dashboard

完成：

```text
累计投递
进行中
终止
Offer
最近投递
```

验收：

统计结果和数据库实际 Application 一致。

---

# 一百零四、Milestone 8：QA

完成：

```text
Unit
Integration
E2E
AI Eval
Security Review
Responsive UI
Empty/Error/Loading
```

发现 P0 blocker：

必须修复后再部署。

---

# 一百零五、Milestone 9：Deployment

至少需要：

```text
Production Frontend
Production Backend
Production PostgreSQL
HTTPS
Production env
Migration
Health Check
```

最终提供：

```text
Demo URL
+
GitHub URL
```

---

# 一百零六、Definition of Done

一个 Feature 不以：

> “代码写完了”

为 Done。

必须同时满足：

```text
功能实现
+
后端校验
+
数据库持久化
+
Loading
+
Empty
+
Error
+
权限
+
测试
+
文档
```

才能进入 Done。

---

# 一百零七、MVP 0.1 最终验收脚本

测试人员创建新用户：

```text
test@example.com
```

完成注册。

↓

建立：

```text
1份真实测试简历
```

↓

输入：

```text
3个不同匹配程度的岗位
```

例如：

```text
高度匹配
中度匹配
明显不匹配
```

↓

系统正确生成：

```text
职位排名
硬性条件
分项评分
Evidence
Gap
Recommendation
```

↓

选择第一名：

```text
生成针对性简历
```

↓

人工检查：

```text
没有虚构事实
```

↓

修改一行：

```text
保存岗位版
```

↓

刷新：

```text
仍然存在
```

↓

创建：

```text
Application
```

↓

增加：

```text
Assessment
Interview Round 1
```

↓

更新：

```text
REJECTED
```

↓

刷新投递详情：

应显示：

```text
一面淘汰
```

↓

Dashboard：

统计同步变化。

**整条流程无阻塞，即通过 MVP 0.1 产品验收。**

---

# 一百零八、MVP 0.1 之后的升级顺序

MVP 0.2：

```text
Reminder
完整Dashboard
投递漏斗
Career Profile
```

MVP 0.3：

```text
职业类型推荐
Ability Fit
Preference Fit
👍 / 👎 Feedback
```

MVP 0.4：

```text
招聘URL单岗位解析
```

MVP 0.5：

```text
公司招聘官网批量职位获取
API Adapter
HTML Parser
Playwright
```

V1.0：

```text
完整CareerPilot P0
```

---

# 一百零九、开发团队当前第一批 Ticket

完成项目评审后，可以直接创建以下开发任务：

```text
CP-001 Initialize monorepo

CP-002 Configure PostgreSQL

CP-003 Add backend config

CP-004 Implement User model

CP-005 Implement register API

CP-006 Implement login/logout

CP-007 Add frontend protected layout

CP-008 Create Resume database models

CP-009 Create Resume Master API

CP-010 Build Resume Master editor

CP-011 Build Resume Library

CP-012 Create Job Batch model

CP-013 Build manual Job input

CP-014 Implement Job Parser schema

CP-015 Implement Job Parser skill

CP-016 Create Match Result models

CP-017 Implement Matcher schema

CP-018 Implement Matcher skill

CP-019 Implement scoring service

CP-020 Build Match Result UI

CP-021 Build Job Detail UI

CP-022 Implement Resume Tailor skill

CP-023 Build Resume Tailor comparison UI

CP-024 Implement Resume Version storage

CP-025 Build Application models/API

CP-026 Build Application List

CP-027 Build Application Timeline

CP-028 Build Dashboard overview

CP-029 Add backend tests

CP-030 Add frontend E2E test

CP-031 Build AI Eval dataset

CP-032 Production deployment

CP-033 Complete README
```

开发团队可以直接以：

```text
CP-001 → CP-033
```

作为第一版 Backlog。

---

# 一百一十、产品负责人在开发期间需要重点把控的事项

开发人员不应该自行决定以下产品逻辑：

```text
职位评分维度
评分权重
Hard Gate定义
推荐等级
AI真实性规则
简历字段
投递状态模型
用户看到的解释方式
```

这些属于产品规则。

技术团队主要决定：

```text
代码实现
数据库性能
API组织
组件封装
部署
缓存
错误处理
测试
```

如果开发中发现 PRD 与技术现实冲突：

必须形成：

```text
Issue
→
产品判断
→
更新Specification
→
再开发
```

不能开发人员私自改变核心业务规则。

---

# 一百一十一、MVP 0.1 最核心的产品原则

整个项目开发过程中始终遵守四条原则：

### 1. AI 不替用户做不可解释的决定

不能只显示：

```text
匹配度92%
```

必须告诉用户：

```text
为什么。
```

### 2. AI 判断必须尽可能有证据

```text
Claim
+
Evidence
```

### 3. AI 可以优化表达，但不能创造求职事实

尤其是：

```text
技能
数字
成果
经历
```

### 4. 自动化能力不能阻断核心价值

即使未来：

```text
招聘网页抓取失败
```

用户依然应该可以：

```text
粘贴JD
→
完成职位比较
→
优化简历
```

CareerPilot 的核心价值是：

> **帮助用户做更好的求职决策。**

爬虫、Agent、自动化都只是实现该价值的技术手段，而不是产品本身。
