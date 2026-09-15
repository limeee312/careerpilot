# CareerPilot MVP 0.1 AI Skills Specification

**建议文件：**

```text
docs/AI_SKILLS.md
```

Skill：

```text
01 Job Parser
02 Resume–Job Matcher
03 Resume Tailor
```

版本：

```text
job_parser_v1
job_matcher_v1
resume_tailor_v1
```

---

# 1. AI 架构原则

所有 Skill 统一：

```text
Input
↓
Context Builder
↓
Versioned Prompt
↓
LLM Structured Output
↓
Pydantic Validation
↓
Deterministic Backend Logic
↓
Database
```

AI 负责：

```text
语义理解
证据匹配
文本生成
```

Backend 负责：

```text
数字计算
ID验证
权限
事实约束
状态
排序
持久化
```

---

# 2. 禁止 AI 自己做的事情

禁止模型直接决定：

```text
最终总分
岗位排名
推荐等级阈值
数据库ID
用户身份
招聘流程状态
```

这些全部由代码处理。

---

# 3. Resume Context

三个 Skill 共用统一 Resume Context。

发送 AI 前必须脱敏。

禁止发送：

```text
姓名
电话
个人邮箱
身份证
精确地址
```

结构：

```json
{
  "education": [],
  "experiences": [],
  "projects": [],
  "skills": [],
  "summary": ""
}
```

每项保留：

```text
source_id
```

用于 Evidence Grounding。

---

# Skill 01 — Job Parser

# 4. 目的

将：

```text
非结构化 JD
```

转换为：

```text
标准化职位要求
+
原子 Requirements
```

Parser：

**不读取简历。**

Parser：

**不进行匹配。**

---

# 5. Parser Input

```python
class JobParserInput(BaseModel):
    company_name: str
    title: str
    location: str | None = None
    raw_jd: str
```

---

# 6. Requirement Dimension

```python
from enum import Enum

class RequirementType(str, Enum):
    HARD = "HARD"
    CORE = "CORE"
    STANDARD = "STANDARD"
    PREFERRED = "PREFERRED"


class MatchDimension(str, Enum):
    RESPONSIBILITY = "RESPONSIBILITY"
    TOOLS_METHODS = "TOOLS_METHODS"
    BUSINESS_DOMAIN = "BUSINESS_DOMAIN"
    OWNERSHIP = "OWNERSHIP"
    OUTCOME = "OUTCOME"
    COMMUNICATION = "COMMUNICATION"
```

Hard：

```text
dimension = null
```

---

# 7. Job Parser Pydantic Output

```python
from pydantic import BaseModel, Field
from typing import Literal


class ParsedRequirement(BaseModel):
    requirement_key: str = Field(
        description="R1, R2, R3...按JD出现顺序"
    )

    requirement_type: RequirementType

    dimension: MatchDimension | None

    requirement_text: str

    source_quote: str

    importance: Literal[1, 2]


class JobParserOutput(BaseModel):
    role_summary: str

    responsibilities_summary: list[str]

    requirements: list[ParsedRequirement]

    business_domains: list[str]

    tools: list[str]

    ambiguous_points: list[str]
```

---

# 8. Parser Prompt

## System Prompt — job_parser_v1

```text
你是 CareerPilot 的职位JD结构化解析器。

你的任务不是评价候选人，而是忠实地将输入JD拆解成可供后续匹配使用的结构化要求。

【基本原则】

1. 只依据输入JD。
2. 禁止利用行业常识补充JD没有写出的要求。
3. 禁止推测招聘方未表达的偏好。
4. 每个Requirement只表达一个相对独立的要求。
5. 尽量避免重复要求。
6. 必须区分：
   HARD
   CORE
   STANDARD
   PREFERRED。
7. “优先”“加分”“更佳”“preferred”等不得标记为HARD。
8. 只有明确表达必须满足、资格限制或客观准入条件时才标记HARD。
9. HARD不进入能力评分，因此dimension必须为null。
10. 其他要求必须映射到一个最主要的MatchDimension。
11. source_quote必须来自输入JD，不能自己改写成JD不存在的事实。
12. 如果JD存在歧义，将其写入ambiguous_points，不自行决定。
13. 不要把职位标题中的词自动当作岗位要求。
14. 输出必须严格符合指定JSON Schema。

【Requirement Type】

HARD：
不满足即可能没有投递资格的明确条件。

CORE：
岗位主要工作、主要交付物或JD重点强调能力。

STANDARD：
日常职责、一般能力或一般技能要求。

PREFERRED：
明确表述为优先、加分、熟悉更佳的条件。

【Dimension】

RESPONSIBILITY：
实际负责的工作任务和交付内容。

TOOLS_METHODS：
工具、数据分析方法、研究方法、执行方法、质量方法。

BUSINESS_DOMAIN：
行业、业务流程、用户场景、客户或领域知识。

OWNERSHIP：
独立负责程度、复杂度、项目规模、跨团队推进。

OUTCOME：
结果、指标、闭环、验证、迭代、落地。

COMMUNICATION：
语言应用、汇报、文档、沟通协调。

【Importance】

importance=2：
JD明确强调“核心”“重点”“主要”“负责XX整体”等明显核心要求。

其他：
importance=1。

不要为了增加importance进行推断。
```

---

# 9. Parser Backend Validation

返回后检查：

### 9.1 Key 唯一

```text
R1
R2
...
```

不得重复。

### 9.2 Hard Dimension

如果：

```text
type = HARD
```

则：

```text
dimension must be None
```

### 9.3 非 Hard

必须：

```text
dimension != None
```

### 9.4 source_quote

必须能够在：

```text
raw_jd
```

中找到。

允许：

```text
空白符规范化
```

后比较。

如果 source_quote 无法定位：

返回：

```text
AI_INVALID_OUTPUT
```

Retry 一次。

---

# 10. Parser Test Case

输入：

```text
岗位：产品运营

职责：
1. 负责产品用户运营策略制定与执行；
2. 通过用户行为数据分析发现问题并推动产品优化；
3. 联动产品、研发和市场团队推进运营项目落地。

要求：
1. 本科及以上学历；
2. 具备良好的数据分析能力；
3. 熟悉SQL优先。
```

期望至少产生：

```text
HARD
本科及以上学历

CORE / RESPONSIBILITY
负责用户运营策略制定与执行

CORE / TOOLS_METHODS
通过用户行为数据分析发现问题

CORE或STANDARD / OWNERSHIP
跨产品、研发、市场推进项目

PREFERRED / TOOLS_METHODS
熟悉SQL
```

禁止：

```text
把SQL变成Hard Gate
```

---

# Skill 02 — Resume–Job Matcher

# 11. 设计目标

Matcher 不回答：

> 这个人能不能拿 Offer？

它只回答：

> 根据当前简历证据，这个人和这个 JD 的要求匹配到什么程度？

因此：

```text
Match Score ≠ Offer Probability
```

---

# 12. Matcher 输入

```python
class ResumeEvidenceItem(BaseModel):
    source_type: Literal[
        "education",
        "experience",
        "project",
        "skill",
        "summary"
    ]

    source_id: str | None

    content: str


class MatcherInput(BaseModel):
    parsed_job: JobParserOutput

    resume_evidence: list[ResumeEvidenceItem]
```

MVP 0.1 暂不把用户职业偏好交给 Matcher。

职业偏好未来独立成为：

```text
Preference Score
```

不污染能力匹配。

---

# 13. Match Level

```python
class MatchLevel(int, Enum):
    NONE = 0
    WEAK = 1
    TRANSFERABLE = 2
    DIRECT_PARTIAL = 3
    DIRECT_STRONG = 4
```

定义：

### 4

有直接同类任务经验，并且范围 / 深度能够支持该要求。

### 3

直接做过主要部分，但范围、复杂度或深度存在小缺口。

### 2

相邻经验具有明显迁移价值，但没有直接完成目标任务。

### 1

只有课程、基础接触、辅助参与或非常弱的间接证据。

### 0

明确不具备，或当前完全没有可支持证据。

---

# 14. Evidence Grade

```python
class EvidenceGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    X = "X"
```

定义：

### A

存在：

```text
具体任务
+
个人行动
+
明确结果/交付
```

并且可以定位来源。

### B

存在：

```text
具体任务
+
个人行动
```

但结果或范围不足。

### C

只有：

```text
技能自述
课程
证书
职责概述
```

没有实际应用实例。

### X

```text
无证据
信息矛盾
或只能推断
```

---

# 15. Hard Gate Output

```python
class GateEvidence(BaseModel):
    source_type: str | None
    source_id: str | None
    source_quote: str | None


class GateAssessment(BaseModel):
    requirement_key: str

    status: EligibilityStatus

    reason: str

    evidence: list[GateEvidence]
```

---

# 16. Requirement Assessment

```python
class ResumeEvidenceRef(BaseModel):
    source_type: Literal[
        "education",
        "experience",
        "project",
        "skill",
        "summary"
    ]

    source_id: str | None

    source_quote: str


class RequirementAssessment(BaseModel):
    requirement_key: str

    match_level: int = Field(ge=0, le=4)

    evidence_grade: EvidenceGrade

    status: Literal[
        "MATCHED",
        "PARTIAL",
        "CONFIRMED_GAP",
        "UNKNOWN"
    ]

    reason: str

    evidence: list[ResumeEvidenceRef]
```

---

# 17. Matcher Output

```python
class MatchGap(BaseModel):
    requirement_key: str

    importance: Literal["HIGH", "MEDIUM", "LOW"]

    gap: str

    improvement_direction: str


class MatcherOutput(BaseModel):
    gate_assessments: list[GateAssessment]

    requirement_assessments: list[RequirementAssessment]

    strengths: list[str]

    gaps: list[MatchGap]

    overall_reasoning: str
```

注意：

**没有 `total_score` 字段。**

也没有：

```text
recommendation_level
```

这些全部由 Backend 算。

---

# 18. Matcher Prompt

## System Prompt — job_matcher_v1

```text
你是 CareerPilot 的岗位匹配证据评估器。

你的任务是把一个已经结构化的职位要求，与候选人的结构化简历证据逐项进行匹配。

你不是招聘官。
你不能预测候选人是否会被录用。
你不能评价其他候选人的竞争力。

【总原则】

1. 所有判断必须来自提供的简历内容。
2. 禁止推断候选人没有明确提供的技能、经验、成果或能力。
3. “简历没有写”与“已确认不会”必须区分。
4. 每个Requirement必须独立判断。
5. 一个Requirement不能因为候选人在其他方面优秀而被视为满足。
6. Hard Gate与能力评分完全分离。
7. 高能力匹配不能抵消Hard Gate失败。
8. 不允许把相邻技能直接视为等价技能。
9. 参与项目不自动等于独立负责。
10. 数量规模不自动等于业务成果。
11. 使用AI工具不自动等于具备AI模型开发经验。
12. 输出必须严格遵循Schema。

【Hard Gate】

对每一个HARD requirement输出：

PASS：
简历存在明确满足证据。

WARN：
候选人是否满足无法从当前简历确认。

FAIL：
简历明确事实与要求冲突。

如果简历没有写语言能力：
通常应为WARN，而不是FAIL。

【Requirement Match】

每个非HARD requirement分别判断Match Level。

4：
直接完成同类任务，并有足够范围或深度。

3：
直接完成主要任务，但存在范围或深度差距。

2：
存在高度可迁移的相邻经验。

1：
仅有浅层接触、课程、辅助参与或技能声明。

0：
无任何当前证据，或明确不具备。

【Evidence Grade】

A：
具体任务 + 候选人行动 + 明确交付或结果。

B：
具体任务 + 候选人行动，但结果/范围不足。

C：
技能、课程、证书或一般性职责描述。

X：
无证据、证据矛盾或只能靠推测。

Evidence Grade不是能力评价，而是当前材料能支持该判断的证据强度。

【Unknown与Gap】

如果职位要求SQL，而简历没有提到SQL：

status = UNKNOWN
而不是自动写成：
“候选人不会SQL”。

如果候选人明确说明不会SQL：

status = CONFIRMED_GAP。

【Evidence】

每条Evidence必须引用输入Resume中真实存在的文本。

source_id必须来自输入。

source_quote不得改写成候选人没有提供的内容。

【Strengths】

只提炼有A/B级证据支持的关键优势。

【Gaps】

重点列：
- 核心要求缺口；
- 高权重但证据不足的要求；
- 明确技能缺口。

improvement_direction描述未来可以如何补证或提升。

不能把尚未完成的提升写成候选人已经具备。

不要计算最终分数。
不要输出录用概率。
```

---

# 19. Matcher 后端评分

Backend 读取：

```text
JobRequirement
+
RequirementAssessment
```

## Evidence Cap

```python
EVIDENCE_CAP = {
    "A": 4,
    "B": 3,
    "C": 1,
    "X": 0,
}
```

## Dimension Max

```python
DIMENSION_MAX = {
    "RESPONSIBILITY": 35,
    "TOOLS_METHODS": 20,
    "BUSINESS_DOMAIN": 15,
    "OWNERSHIP": 15,
    "OUTCOME": 10,
    "COMMUNICATION": 5,
}
```

## Item Score

```python
effective_level = min(
    assessment.match_level,
    EVIDENCE_CAP[assessment.evidence_grade]
)
```

然后：

```python
normalized_requirement_weight = (
    requirement.importance /
    sum_importance_within_dimension
)
```

```python
item_score = (
    dimension_max
    * normalized_requirement_weight
    * effective_level
    / 4
)
```

若 JD 缺少某个维度，该维度记为 `N/A`，不按 0 分处理。所有实际出现维度按照原始
`DIMENSION_MAX` 占其合计权重的比例重新归一至 100，再代入上述公式。数据库只保存
实际出现的维度，其归一后 `max_score` 合计为 100。

---

# 20. Matcher Recommendation

## Eligibility

如果任一 Hard Gate：

```text
FAIL
```

则：

```text
eligibility = FAIL
recommendation = BLOCKED
```

如果没有 FAIL，但存在 WARN：

```text
eligibility = WARN
```

否则：

```text
PASS
```

---

# 21. Score Level

仅在：

```text
PASS / WARN
```

下用于正常排序。

```text
85–100 PRIORITY
75–84  STRONG
65–74  SELECTIVE
<65    LOW
```

后端保存两位小数总分，并使用该小数进行排序；页面展示和推荐分档统一使用
`ROUND_HALF_UP` 四舍五入后的整数分数。

WARN：

UI 增加：

```text
条件待核实
```

---

# 22. Matcher Confidence

按非 Hard Requirements 的实际权重：

```python
coverage = {
    "A": 1.0,
    "B": 1.0,
    "C": 0.5,
    "X": 0.0
}
```

加权求和得到：

```text
confidence_score
```

等级：

```text
>=85 HIGH
60–84 MEDIUM
<60 LOW
```

存在未知 Hard Gate：

最高：

```text
MEDIUM
```

---

# 23. Matcher 排序

排序算法：

```text
第一层：
Eligibility FAIL 排除正常可投排序

第二层：
Total Score DESC

第三层：
若分差 ≤ 3：
视为近似并列

第四层：
比较 RESPONSIBILITY 得分率

第五层：
Confidence

仍然相同：
并列
```

不要制造：

```text
81.5 vs 81.3
```

这种虚假精度。

UI 总分推荐：

```text
整数
```

近似并列采用“组首分数锚定”，不使用相邻分数链式扩张：先按总分降序，以每组最高分
为锚点，将与锚点分差不超过 3 分的岗位纳入该组；组内依次比较
`RESPONSIBILITY` 得分率与 `Confidence`。两项仍相同才共享名次。没有
`RESPONSIBILITY` 要求时，其得分率为 `N/A`，在该项比较中排在有适用值的岗位之后。
`Eligibility = FAIL` 的岗位保留展示，但不进入上述正常排序。

---

# 24. Matcher Test Case A — 明确匹配

JD：

```text
负责用户数据分析，并推动运营策略优化。
```

Resume：

```text
梳理近三年业务需求及全流程耗时数据，
搭建数据分析体系，
定位流程异常并推动优化。
```

合理输出：

```text
match_level = 3

evidence_grade = A或B
```

具体依据取决于 Resume 是否有明确结果。

不得：

```text
因为都出现“数据分析”
自动给4
```

---

# 25. Matcher Test Case B — 相邻技能

JD：

```text
熟练使用SQL完成数据分析。
```

Resume：

```text
熟练使用Python进行数据分析。
```

不得：

```text
SQL MATCHED
```

合理：

```text
match_level <= 2

如果没有SQL证据：
status = UNKNOWN
```

---

# 26. Matcher Test Case C — Hard Gate

JD：

```text
招聘对象：
2026年9月至2027年8月毕业。
```

Resume：

```text
毕业时间：
2027年6月
```

必须：

```text
PASS
```

如果 Resume：

```text
2028年6月
```

必须：

```text
FAIL
```

---

# 27. Matcher Test Case D — 未知

JD：

```text
英语可作为工作语言。
```

Resume 完全没有语言信息。

必须：

```text
WARN
```

不能：

```text
FAIL
```

---

# Skill 03 — Resume Tailor

# 28. 设计目标

Resume Tailor 不是：

> 根据JD帮用户创造一份更厉害的简历。

而是：

> 从用户已有真实经历中选择、排序和重写最相关的信息，使简历更清晰地呈现岗位所需要的真实能力。

---

# 29. Tailor 输入

必须使用：

```text
Resume Snapshot
+
Parsed Job
+
Job Match Result
```

Matcher 的：

```text
strengths
gaps
evidence
```

可以作为 Tailor 的辅助信息。

但 Tailor 仍以原始 Resume 为最终事实源。

---

# 30. Tailor 输入 Schema

```python
class SourceExperience(BaseModel):
    source_id: str

    experience_type: str

    organization: str

    position: str

    start_date: str | None

    end_date: str | None

    description: str

    achievements: str | None


class SourceProject(BaseModel):
    source_id: str

    name: str

    role: str | None

    description: str

    achievements: str | None


class SourceSkill(BaseModel):
    source_id: str

    skill_name: str


class TailorInput(BaseModel):
    resume_summary: str | None

    experiences: list[SourceExperience]

    projects: list[SourceProject]

    skills: list[SourceSkill]

    parsed_job: JobParserOutput

    match_strengths: list[str]

    match_gaps: list[str]
```

Education 不需要进入 AI Rewrite。

Backend 最终自己原样合并。

---

# 31. Tailored Bullet

关键设计：

AI 不只返回：

```text
改写后的句子
```

还必须返回它从哪里来的。

```python
class EvidenceReference(BaseModel):
    source_field: Literal[
        "description",
        "achievements"
    ]

    source_quote: str


class TailoredBullet(BaseModel):
    text: str

    evidence_refs: list[EvidenceReference]
```

---

# 32. Tailored Experience

```python
class TailoredExperience(BaseModel):
    source_id: str

    include: bool

    order: int | None

    bullets: list[TailoredBullet]
```

---

# 33. Tailored Project

```python
class TailoredProject(BaseModel):
    source_id: str

    include: bool

    order: int | None

    bullets: list[TailoredBullet]
```

---

# 34. Improvement Suggestion

```python
class ImprovementSuggestion(BaseModel):
    job_requirement: str

    current_status: Literal[
        "NO_EVIDENCE",
        "WEAK_EVIDENCE",
        "PARTIAL_MATCH"
    ]

    suggestion: str

    do_not_claim_yet: bool = True
```

---

# 35. Tailor Output

```python
class ResumeTailorOutput(BaseModel):
    professional_summary: str | None

    experiences: list[TailoredExperience]

    projects: list[TailoredProject]

    skill_order: list[str]

    improvement_suggestions: list[ImprovementSuggestion]

    warnings: list[str]
```

`skill_order`：

不是技能名称。

必须返回：

```text
Skill source_id
```

---

# 36. Resume Tailor Prompt

## System Prompt — resume_tailor_v1

```text
你是 CareerPilot 的岗位针对性简历编辑器。

你的任务是根据目标岗位，从候选人已经提供的真实简历材料中：

选择
排序
压缩
重组
改写

最相关的信息。

你不是经历生成器。

【最高优先级规则】

1. 不得创造候选人没有提供的事实。
2. 不得创造新公司、职位、项目、学校、学历、技能、工具。
3. 不得创造数字、百分比、用户量、收入、效率提升、成果规模。
4. 不得把团队成果改写成候选人的个人成果。
5. 不得把参与、协助改写成独立负责或主导。
6. 不得把提案、原型、试运行改写成已正式上线或已取得结果。
7. 不得把相邻工具写成目标工具。
8. 不得修改时间。
9. 不得改变原始成果指标的含义。
10. 如果目标岗位要求某能力，但Resume没有证据，将其放入improvement_suggestions，不写进正式简历。

【允许的操作】

可以：
- 调整经历顺序；
- 删除明显无关的经历；
- 调整同一经历中Bullet顺序；
- 合并重复表达；
- 精简背景；
- 强化动作和方法；
- 使用与JD一致的专业术语，但前提是该术语真实描述候选人的已有工作；
- 保留真实数字；
- 把岗位最相关的真实成果提前。

【Bullet写法】

优先表达：

动作
+
方法
+
工作范围
+
真实结果

但如果源材料没有结果：
不要创造结果。

每个Bullet尽量只表达一个核心贡献。

【Evidence Grounding】

每一个生成Bullet都必须至少提供一个evidence_ref。

evidence_ref.source_quote必须来自对应source_id的原始description或achievements。

如果无法找到足够证据：
不要生成该Bullet。

【Professional Summary】

只有Resume存在足够强的岗位相关证据时才生成。

禁止：

“学习能力强”
“责任心强”
“热爱互联网”
“具备优秀沟通能力”

这类没有证据的泛化描述。

【Skills】

只能重新排序输入中的技能。

不能新增技能。

【Gap】

岗位要求但简历没有充分支持的能力：

输出到improvement_suggestions。

例如：
目标岗位需要SQL，但Resume没有SQL。

正确：
建议完成SQL数据分析项目并形成可展示成果。

错误：
在Skills中增加“熟练SQL”。

【输出】

严格遵循指定Schema。
```

---

# 37. Tailor Backend Validation

这是整个功能最重要的一步。

不能只相信 Prompt。

---

# 38. source_id 白名单

AI 返回所有：

```text
experience.source_id
project.source_id
skill_order
```

必须属于输入集合。

例如：

```python
returned_ids <= source_ids
```

否则：

```text
AI_INVALID_OUTPUT
```

---

# 39. Evidence Quote 校验

例如 AI 返回：

```json
{
  "source_field": "description",
  "source_quote": "搭建数据分析体系"
}
```

Backend 必须检查：

该 quote 是否真实存在于对应：

```text
Experience.description
```

中。

不存在：

拒绝该 Bullet。

---

# 40. 数字防幻觉

Backend 对所有生成 Bullet 提取：

```text
数字
百分比
货币
时间规模
```

例如：

```text
30%
1000+
3年
20万元
```

生成文本中的数字：

原则上必须存在于对应 Source Evidence 中。

如果不存在：

标记：

```text
UNSUPPORTED_NUMBER
```

不得自动写入 ResumeVersion。

---

# 41. Skill 防幻觉

例如原 Resume Skill：

```text
Excel
Python
Power BI
```

AI 返回：

```text
SQL
```

必须拒绝。

新技能只能：

```text
Improvement Suggestion
```

---

# 42. 不可变字段由 Backend 组装

不要让 AI 输出：

```text
Company
Position
School
Degree
Start Date
End Date
```

最终 Resume Version：

```text
Immutable fields
来自Resume Snapshot

Editable fields
来自AI Draft
```

因此即使模型出错：

也不能修改：

```text
公司
学校
职位
时间
```

---

# 43. Resume Version Assembly

Backend：

```text
ResumeMaster Snapshot

+ TailorOutput
↓
ResumeVersion
```

例如：

```python
experience = {
    "organization": source.organization,
    "position": source.position,
    "start_date": source.start_date,
    "end_date": source.end_date,
    "bullets": ai_output.bullets
}
```

---

# 44. Tailor Test A — 合理改写

Source：

```text
负责整理过去三年的翻译需求量和流程耗时数据，
分析异常环节并推动流程优化。
```

JD：

```text
要求具备数据分析和流程优化能力。
```

允许：

```text
梳理近三年翻译需求量及全流程耗时数据，
定位流程异常并推动优化。
```

---

# 45. Tailor Test B — 禁止创造数字

Source：

```text
推动流程优化。
```

不得生成：

```text
推动流程优化，使效率提升30%。
```

因为：

```text
30%
```

没有来源。

---

# 46. Tailor Test C — 禁止技能补写

JD：

```text
熟悉SQL。
```

Resume：

```text
Excel
Python
```

不得：

```text
熟练使用SQL、Python进行数据分析。
```

必须进入：

```text
Improvement Suggestions
```

---

# 47. Tailor Test D — 团队与个人成果

Source：

```text
参与团队年度活动运营，
团队累计触达10万用户。
```

不得：

```text
独立负责年度运营活动，触达10万用户。
```

可以：

```text
参与年度活动运营，所在团队累计触达10万用户。
```

---

# 48. Tailor Test E — 项目状态

Source：

```text
设计数据周报PRD，方案待研发评审。
```

不得：

```text
上线自动化数据周报系统。
```

允许：

```text
设计数据周报PRD，形成自动化质量监控方案并推进研发评审。
```

---

# 49. AI Skill 文件结构

建议：

```text
backend/app/ai/
│
├── client.py
├── context_builder.py
│
├── job_parser/
│   ├── prompt_v1.md
│   ├── schemas.py
│   ├── service.py
│   └── tests/
│
├── job_matcher/
│   ├── prompt_v1.md
│   ├── schemas.py
│   ├── scoring.py
│   ├── service.py
│   └── tests/
│
└── resume_tailor/
    ├── prompt_v1.md
    ├── schemas.py
    ├── validator.py
    ├── service.py
    └── tests/
```

---

# 50. Service 调用模式

例如 Job Matcher：

```python
async def match_job(
    resume,
    parsed_job,
    ai_client
):
    context = build_match_context(
        resume=resume,
        parsed_job=parsed_job
    )

    ai_output = await ai_client.generate_structured(
        system_prompt=JOB_MATCHER_PROMPT_V1,
        input_data=context,
        response_model=MatcherOutput,
    )

    validate_match_output(
        ai_output,
        resume,
        parsed_job
    )

    score = calculate_score(
        ai_output,
        parsed_job
    )

    return build_match_result(
        ai_output,
        score
    )
```

---

# 51. AI Retry Policy

Retry 最多：

```text
1次
```

只在：

```text
timeout
5xx
schema validation failure
```

发生。

以下情况不 Retry：

```text
用户输入为空
Resume不存在
JD长度不足
权限错误
```

---

# 52. Eval 数据目录

```text
tests/evals/
├── job_parser/
├── job_matcher/
└── resume_tailor/
```

每个 Case：

```text
input.json
expected.json
notes.md
```

---

# 53. Job Parser Eval

重点：

```text
Hard Gate识别准确率
Preferred误判为Hard的比例
Requirement遗漏率
Requirement重复率
source_quote grounding
```

P0 最重要：

```text
Preferred → Hard
```

重大误判：

应接近：

```text
0
```

---

# 54. Matcher Eval

重点：

```text
Hard Gate Accuracy
Ranking
Evidence Grounding
Unknown vs Confirmed Gap
Hallucination
```

人工测试：

```text
Resume
+
3–5 Jobs
```

提前人工标：

```text
首选
Top3
明显不匹配
Hard Gate
核心证据
```

---

# 55. Tailor Eval

逐条检查：

```text
Company unchanged
Position unchanged
Dates unchanged
School unchanged

No new skills
No new metrics
No invented outcomes

Team results remain team results

Proposal remains proposal

Every bullet grounded
```

---

# 56. AI Release Gate

Prompt 新版本例如：

```text
job_matcher_v2
```

不得直接上线。

必须：

```text
旧Eval数据集
↓
v1
vs
v2
↓
比较
```

只有在：

```text
Hard Gate不退化
Grounding不退化
Hallucination不升高
Ranking持平或提升
```

时才能切换 Production。

---

# 57. Prompt Version

生产数据库必须保存：

```text
skill_name
prompt_version
model
```

因此未来看到：

```text
Score 84
```

可以知道：

```text
job_matcher_v3
Model X
2026-xx-xx
```

产生。

---

# 58. AI 最终职责边界

## Job Parser

负责：

```text
理解JD
```

不负责：

```text
评价候选人
```

---

## Job Matcher

负责：

```text
把职位要求和真实简历证据逐项对应
```

不负责：

```text
最终算分
预测Offer
```

---

## Resume Tailor

负责：

```text
重新组织真实经历
```

不负责：

```text
创造更漂亮的虚假经历
```

---

# 59. 三个 Skill 的数据链

```text
用户输入 Raw JD
        ↓
    Job Parser
        ↓
Job Requirements
        │
        │
Resume Master
        │
        ↓
    Job Matcher
        ↓
Requirement Assessments
        ↓
Backend Score
        ↓
Match Result
        │
        ├──────────────┐
        ↓              ↓
    Resume Master   Target Job
        │              │
        └──────┬───────┘
               ↓
         Resume Tailor
               ↓
          Resume Draft
               ↓
        Backend Validation
               ↓
         User Review
               ↓
         Resume Version
```

该架构作为 CareerPilot MVP 0.1 AI 层开发基线。

---

# 60. MVP 0.1 Provider 实现约定

`job_parser_v1` 通过 OpenAI Responses API 的 Pydantic Structured Outputs 调用。
`OPENAI_API_KEY`、`OPENAI_MODEL` 和 `OPENAI_TIMEOUT_SECONDS` 只配置在后端环境中，
代码不锁定具体付费模型。

SDK 自带重试关闭，由 Skill Service 严格执行本文件第 51 节的策略：原始请求
加最多一次重试。Job Parser Service 返回经过 Pydantic 和确定性引用校验的输出，
同时携带 `skill_name`、`prompt_version`、实际模型、请求 ID、尝试次数和 Token
用量，供后续运行记录持久化使用。

CP-015 不直接把解析结果写入数据库。持久化由包含 Job 状态流转与事务边界的
后续编排层统一完成，避免 AI Provider 适配器承担业务状态职责。

---

# 61. MVP 0.1 Resume Tailor 实现约定

`resume_tailor_v1` 使用当前 Match Result 中冻结的 Resume Snapshot、Parsed Job、
Strengths 与 Gaps 构建输入。Context Builder 只发送 summary、experiences、projects
与 skills，不发送姓名、电话、邮箱、城市、求职状态或 Education。

AI 输出先经过 Pydantic Contract，再由 Backend 确定性检查：

```text
source_id 白名单与去重
include / order / bullets 一致性
Skill source_id 完整排列
Evidence Quote 原文定位
数字与 JD Tool 来源
参与 / 协助不得升级为主导
团队指标不得改写为个人成果
待评审 / 原型 / 试运行不得改写为已上线
Improvement Suggestion 必须对应真实 Requirement
```

`POST /api/v1/jobs/{job_id}/resume-tailor` 只生成并返回 Draft 与追踪信息，不写入
数据库，也不修改 Resume Master。Resume Version 的用户确认、编辑与保存由
CP-023 和 CP-024 承接。
