"""Materialize the curated synthetic pilot fixtures. No personal data."""

import json
from pathlib import Path

ROOT = Path(__file__).parent / "matcher"

# id, title, HARD requirement, CORE responsibility, STANDARD method, PREFERRED
JOBS = [
    ("product_ops", "产品运营", "本科及以上学历", "分析用户行为并优化产品体验", "使用 SQL 分析转化漏斗", "独立完成 A/B 测试报告"),
    ("community_ops", "社群运营", "本科及以上学历", "维护社群活跃和用户关系", "分析社群互动数据", "建立社群活动 SOP"),
    ("community_assistant", "社群运营助理", "大专及以上学历", "处理社群反馈和内容审核", "使用表格整理用户问题", "建立社群活动 SOP"),
    ("content_ops", "内容运营", "本科及以上学历", "策划并发布短视频内容", "复盘内容播放和转化数据", "撰写直播脚本"),
    ("data_analyst", "数据分析师", "本科及以上学历", "建立业务指标和分析报表", "使用 SQL 查询业务数据", "应用统计因果推断"),
    ("ux_research", "用户研究员", "硕士及以上学历", "组织用户访谈与可用性研究", "整理访谈记录形成研究洞察", "设计眼动实验"),
    ("product_manager", "产品经理", "本科及以上学历", "开展需求调研并制定产品方案", "编写 PRD 和验收标准", "参与商业化定价项目"),
    ("ux_design", "交互设计师", "本科及以上学历", "绘制交互原型并验证体验", "使用 Figma 制作交互稿", "维护跨端设计系统"),
    ("frontend_dev", "前端开发", "本科及以上学历", "开发 React 用户界面", "使用 TypeScript 和自动化测试", "完成无障碍审计"),
    ("backend_dev", "后端开发", "计算机及相关专业本科及以上学历", "开发 API 和数据库服务", "使用 Python 实现接口", "维护分布式消息队列"),
    ("growth_ops", "增长运营", "本科及以上学历", "设计获客和留存实验", "分析渠道转化和投放数据", "管理品牌投放预算"),
    ("international_ops", "海外运营", "本科及以上学历", "执行海外本地化活动", "使用英语与海外团队沟通", "熟悉海外税务合规"),
    ("customer_success", "客户成功", "本科及以上学历", "推动 B2B 客户上线及使用", "使用 CRM 跟踪客户问题", "主导续约谈判"),
    ("grad27_product", "2027届产品管培生", "仅限2027届毕业生", "开展用户调研并提出产品建议", "编写 PRD 文档", "参与商业化项目"),
    ("senior_product", "资深产品经理", "至少3年产品经理经验", "制定产品路线图并推进落地", "使用 SQL 跟踪产品指标", "管理海外产品团队"),
    ("qa_engineer", "软件测试工程师", "大专及以上学历", "设计并执行软件测试用例", "使用 Python 编写自动化测试", "开展性能压测"),
    ("sales_ops", "销售运营", "本科及以上学历", "维护销售漏斗与业务报表", "使用 CRM 和表格分析线索", "制定销售激励制度"),
]

# Case ID, education, major, graduation, product-manager years (if stated),
# experience, skills, four jobs in authored rank order, one grounded strength.
PROFILES = [
    ("C01", "本科", "市场营销", 2027, None, "负责用户行为分析和产品体验优化，跟踪转化漏斗。", "SQL、用户访谈", ["product_ops", "grad27_product", "community_ops", "backend_dev"], "用户行为分析和产品体验优化"),
    ("C02", "本科", "信息管理", 2027, 1, "担任产品经理1年，完成用户调研、PRD 编写和版本验收。", "PRD、原型设计", ["product_manager", "grad27_product", "product_ops", "senior_product"], "完成用户调研、PRD 编写和版本验收"),
    ("C03", "本科", "广告学", 2026, None, "设计获客和留存实验，复盘渠道转化与活动效果。", "SQL、活动复盘", ["growth_ops", "product_ops", "data_analyst", "grad27_product"], "设计获客和留存实验"),
    ("C04", "大专", "电子商务", 2027, None, "处理社群反馈与内容审核，记录用户问题。", "表格、用户沟通", ["community_assistant", "grad27_product", "community_ops", "backend_dev"], "处理社群反馈与内容审核"),
    ("C05", "本科", "新闻传播", 2027, None, "策划并发布短视频内容，分析播放完成率。", "剪辑、内容策划", ["content_ops", "community_ops", "growth_ops", "backend_dev"], "策划并发布短视频内容"),
    ("C06", "本科", "统计学", 2027, None, "建立业务指标报表，使用 SQL 查询订单数据。", "SQL、Excel、仪表板", ["data_analyst", "product_ops", "growth_ops", "backend_dev"], "建立业务指标报表"),
    ("C07", "硕士", "统计学", 2026, None, "构建用户留存报表，使用 SQL 和 Python 分析数据。", "SQL、Python、统计建模", ["data_analyst", "ux_research", "product_ops", "frontend_dev"], "构建用户留存报表"),
    ("C08", "本科", "经济学", 2027, None, "分析渠道转化与广告投放数据，提出获客实验。", "SQL、渠道归因", ["growth_ops", "data_analyst", "product_ops", "ux_research"], "提出获客实验"),
    ("C09", "硕士", "应用心理学", 2027, None, "组织用户访谈和可用性研究，形成研究洞察报告。", "访谈、定性分析", ["ux_research", "product_manager", "grad27_product", "backend_dev"], "组织用户访谈和可用性研究"),
    ("C10", "本科", "工业设计", 2026, None, "使用 Figma 绘制交互原型并进行可用性验证。", "Figma、交互设计", ["ux_design", "product_manager", "ux_research", "backend_dev"], "绘制交互原型并进行可用性验证"),
    ("C11", "本科", "社会学", 2027, None, "开展用户访谈并编写需求分析和 PRD 初稿。", "访谈、PRD", ["grad27_product", "product_manager", "ux_research", "backend_dev"], "开展用户访谈并编写需求分析"),
    ("C12", "硕士", "人机交互", 2026, None, "主持用户访谈和可用性测试，整理研究洞察。", "可用性测试、访谈", ["ux_research", "product_manager", "data_analyst", "grad27_product"], "主持用户访谈和可用性测试"),
    ("C13", "本科", "计算机科学", 2027, None, "开发 React 用户界面，使用 TypeScript 编写组件测试。", "React、TypeScript、测试", ["frontend_dev", "backend_dev", "product_manager", "ux_research"], "开发 React 用户界面"),
    ("C14", "本科", "计算机科学", 2026, None, "使用 Python 开发 API 和数据库服务，编写接口测试。", "Python、SQL、API", ["backend_dev", "data_analyst", "frontend_dev", "grad27_product"], "使用 Python 开发 API 和数据库服务"),
    ("C15", "本科", "软件工程", 2027, None, "开发 Python API 并维护关系型数据库，分析慢查询。", "Python、SQL、数据库", ["backend_dev", "data_analyst", "frontend_dev", "ux_research"], "开发 Python API 并维护关系型数据库"),
    ("C16", "大专", "软件测试", 2027, None, "设计并执行回归测试用例，使用 Python 编写测试脚本。", "Python、测试用例", ["qa_engineer", "frontend_dev", "grad27_product", "backend_dev"], "设计并执行回归测试用例"),
    ("C17", "本科", "英语", 2027, None, "使用英语协调海外团队，执行海外本地化活动。", "英语、本地化", ["international_ops", "content_ops", "customer_success", "backend_dev"], "执行海外本地化活动"),
    ("C18", "本科", "工商管理", 2026, None, "推动 B2B 客户上线，使用 CRM 跟踪客户问题。", "CRM、客户培训", ["customer_success", "product_ops", "international_ops", "grad27_product"], "推动 B2B 客户上线"),
    ("C19", "本科", "市场营销", 2027, None, "维护销售漏斗与业务报表，使用 CRM 分析线索。", "CRM、Excel、报表", ["sales_ops", "customer_success", "growth_ops", "backend_dev"], "维护销售漏斗与业务报表"),
    ("C20", "本科", "信息管理", 2022, 4, "担任产品经理4年，制定产品路线图并跟踪产品指标。", "SQL、路线图", ["senior_product", "product_manager", "product_ops", "grad27_product"], "制定产品路线图并跟踪产品指标"),
]


def gate(case, job):
    cid, degree, major, graduation, pm_years, *_ = case
    job_id = job[0]
    if job_id == "grad27_product":
        return ("PASS" if graduation == 2027 else "FAIL", f"毕业年份：{graduation}", f"{cid}-edu")
    if job_id == "senior_product":
        if pm_years is None:
            return ("WARN", None, None)
        return ("PASS" if pm_years >= 3 else "FAIL", f"产品经理年限：{pm_years}年", f"{cid}-exp")
    if job_id == "backend_dev":
        return ("PASS" if degree in {"本科", "硕士"} and major in {"计算机科学", "软件工程"} else "FAIL", f"专业：{major}", f"{cid}-edu")
    if job_id == "ux_research":
        return ("PASS" if degree == "硕士" else "FAIL", f"学历：{degree}", f"{cid}-edu")
    if job_id in {"community_assistant", "qa_engineer"}:
        return ("PASS", f"学历：{degree}", f"{cid}-edu")
    return ("PASS" if degree in {"本科", "硕士"} else "FAIL", f"学历：{degree}", f"{cid}-edu")


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    jobs = []
    lookup = {}
    for job_id, title, hard, core, method, preferred in JOBS:
        raw_jd = f"岗位：{title}。任职要求：{hard}；{core}；{method}；{preferred}。"
        requirements = [
            dict(requirement_key=f"R{i}", requirement_type=kind, dimension=dimension,
                 requirement_text=quote, source_quote=quote, importance=importance)
            for i, (kind, dimension, quote, importance) in enumerate([
                ("HARD", None, hard, 1), ("CORE", "RESPONSIBILITY", core, 2),
                ("STANDARD", "TOOLS_METHODS", method, 1),
                ("PREFERRED", "BUSINESS_DOMAIN", preferred, 1),
            ], start=1)
        ]
        jobs.append({"id": job_id, "parser_input": {"company_name": "评估样本企业", "title": title,
                      "location": "杭州", "raw_jd": raw_jd},
                     "parsed_job": {"role_summary": core, "responsibilities_summary": [core],
                                    "requirements": requirements, "business_domains": [], "tools": [],
                                    "ambiguous_points": []}})
        lookup[job_id] = (job_id, title, hard, core, method, preferred)

    cases = []
    for case in PROFILES:
        cid, degree, major, graduation, pm_years, experience, skills, rankings, strength = case
        education = f"学历：{degree}；专业：{major}；毕业年份：{graduation}"
        if pm_years is not None:
            experience += f" 产品经理年限：{pm_years}年。"
        evidence = [
            {"source_type": "education", "source_id": f"{cid}-edu", "content": education},
            {"source_type": "experience", "source_id": f"{cid}-exp", "content": experience},
            {"source_type": "skill", "source_id": f"{cid}-skill", "content": f"技能：{skills}"},
        ]
        comparisons = []
        for rank, job_id in enumerate(rankings, start=1):
            status, quote, source_id = gate(case, lookup[job_id])
            comparisons.append({"job_id": job_id, "expected_rank": rank,
                                "clearly_unsuitable": rank == 4,
                                "hard_gates": {"R1": {"status": status,
                                                      "evidence": ([] if quote is None else [{"source_type": "experience" if job_id == "senior_product" else "education", "source_id": source_id, "source_quote": quote}])}},
                                "key_strengths": ([{"requirement_key": "R2", "source_type": "experience",
                                                    "source_id": f"{cid}-exp", "source_quote": strength}] if rank == 1 else []),
                                "key_gaps": [{"requirement_key": "R1" if cid == "C12" and rank == 4 else "R2" if rank == 4 else "R4",
                                              "reason": ("毕业年份为2026，与仅限2027届的要求冲突" if cid == "C12" and rank == 4
                                                         else f"简历未提供{lookup[job_id][3 if rank == 4 else 5]}的直接证据")}]} )
        cases.append({"id": cid, "source_kind": "synthetic", "resume_evidence": evidence,
                      "best_match": rankings[0], "top_3": rankings[:3],
                      "clearly_unsuitable": [rankings[3]], "comparisons": comparisons})

    for name, obj in [("jobs.json", jobs), ("cases.json", cases)]:
        (ROOT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    tailor_probes = [
        ("C05", "content_ops", "metric", "单条视频获得100万次播放"),
        ("C09", "ux_research", "skill", "熟练使用眼动追踪设备"),
        ("C13", "frontend_dev", "company", "曾在星河科技担任前端负责人"),
        ("C17", "international_ops", "degree", "拥有英语语言学硕士学位"),
        ("C20", "senior_product", "project", "主导欧洲跨境支付项目"),
    ]
    tailor_cases = [{"id": f"T{i:02d}", "case_id": cid, "job_id": job_id,
                     "unsupported_claim_category": category,
                     "unsupported_claim_probe": probe,
                     "expected": "reject_as_new_fact"}
                    for i, (cid, job_id, category, probe) in enumerate(tailor_probes, 1)]
    (ROOT / "tailor_cases.json").write_text(
        json.dumps(tailor_cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
