"""Check eval coverage, contract shape, references, and label provenance.

Run with ``python tests/evals/validate.py`` from any working directory.
This checks structural consistency; it cannot establish human-label correctness.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent / "matcher"
STATUSES = {"PASS", "WARN", "FAIL"}
TYPES = {"HARD", "CORE", "STANDARD", "PREFERRED"}
DIMENSIONS = {
    "RESPONSIBILITY", "TOOLS_METHODS", "BUSINESS_DOMAIN", "OWNERSHIP",
    "OUTCOME", "COMMUNICATION",
}


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(jobs, cases, tailor_cases):
    require(len(jobs) >= 4, "job catalog too small")
    require(len(cases) >= 20, "at least 20 resume cases required")
    job_map = {job["id"]: job for job in jobs}
    require(len(job_map) == len(jobs), "duplicate job id")
    require(len({case["id"] for case in cases}) == len(cases), "duplicate case id")

    for job in jobs:
        label = job["id"]
        parser_input, parsed = job["parser_input"], job["parsed_job"]
        raw_jd = parser_input["raw_jd"]
        require(len(raw_jd) >= 50, f"{label}: JD too short for parser input")
        requirements = parsed["requirements"]
        require(requirements, f"{label}: no requirements")
        require([r["requirement_key"] for r in requirements] == [f"R{i}" for i in range(1, len(requirements) + 1)], f"{label}: requirement keys")
        for requirement in requirements:
            kind, dimension = requirement["requirement_type"], requirement["dimension"]
            require(kind in TYPES, f"{label}: invalid requirement type")
            require((dimension is None) == (kind == "HARD"), f"{label}: HARD dimension mismatch")
            require(dimension is None or dimension in DIMENSIONS, f"{label}: unknown dimension")
            require(requirement["importance"] in (1, 2), f"{label}: importance")
            require(requirement["source_quote"] in raw_jd, f"{label}: ungrounded JD quote")

    for case in cases:
        cid = case["id"]
        require(case["source_kind"] in {"synthetic", "deidentified_real"}, f"{cid}: source kind")
        evidence = case["resume_evidence"]
        evidence_map = {(item["source_type"], item["source_id"]): item["content"] for item in evidence}
        require(len(evidence_map) == len(evidence) and evidence, f"{cid}: duplicate or empty resume evidence")
        require(all(item["source_type"] in {"education", "experience", "project", "skill", "summary"} for item in evidence), f"{cid}: invalid evidence type")
        comparisons = case["comparisons"]
        require(3 <= len(comparisons) <= 5, f"{cid}: expected 3–5 jobs")
        ids = [item["job_id"] for item in comparisons]
        require(len(set(ids)) == len(ids) and set(ids) <= job_map.keys(), f"{cid}: duplicate or unknown job")
        require([item["expected_rank"] for item in comparisons] == list(range(1, len(ids) + 1)), f"{cid}: rank order")
        require(case["best_match"] == ids[0] and case["top_3"] == ids[:3], f"{cid}: best/top3 disagree with ranks")
        require(case["clearly_unsuitable"] and set(case["clearly_unsuitable"]) <= set(ids), f"{cid}: unsuitable label")
        require(set(case["clearly_unsuitable"]) == {item["job_id"] for item in comparisons if item["clearly_unsuitable"]}, f"{cid}: unsuitable flags disagree")

        for item in comparisons:
            label = f"{cid}/{item['job_id']}"
            requirements = {r["requirement_key"]: r for r in job_map[item["job_id"]]["parsed_job"]["requirements"]}
            hard_keys = {key for key, requirement in requirements.items() if requirement["requirement_type"] == "HARD"}
            require(set(item["hard_gates"]) == hard_keys, f"{label}: missing/extra hard-gate label")
            for key, gate in item["hard_gates"].items():
                require(gate["status"] in STATUSES, f"{label}: invalid gate status")
                require(bool(gate["evidence"]) == (gate["status"] != "WARN"), f"{label}: conclusive gate needs evidence; WARN needs no decisive evidence")
                for ref in gate["evidence"]:
                    require(ref["source_quote"] in evidence_map.get((ref["source_type"], ref["source_id"]), ""), f"{label}: ungrounded gate quote")
            for strength in item["key_strengths"]:
                require(strength["requirement_key"] in requirements and strength["requirement_key"] not in hard_keys, f"{label}: invalid strength requirement")
                require(strength["source_quote"] in evidence_map.get((strength["source_type"], strength["source_id"]), ""), f"{label}: ungrounded strength")
            require(item["key_gaps"], f"{label}: missing key gap")
            for gap in item["key_gaps"]:
                require(gap["requirement_key"] in requirements and gap["reason"].strip(), f"{label}: invalid gap")
                require(requirements[gap["requirement_key"]]["source_quote"] not in " ".join(evidence_map.values()), f"{label}: gap contradicted by an exact resume quote")
            if item["expected_rank"] == 1:
                require(item["key_strengths"], f"{label}: best match needs grounded strength")

    require(len(tailor_cases) >= 5, "at least five tailor guardrail probes required")
    require(len({item["id"] for item in tailor_cases}) == len(tailor_cases), "duplicate tailor probe")
    require({item["unsupported_claim_category"] for item in tailor_cases} >=
            {"company", "degree", "project", "skill", "metric"}, "missing fabrication category")
    case_map = {case["id"]: case for case in cases}
    for probe in tailor_cases:
        cid = probe["case_id"]
        require(cid in case_map and probe["job_id"] in {item["job_id"] for item in case_map[cid]["comparisons"]}, f"{probe['id']}: invalid case/job")
        require(probe["expected"] == "reject_as_new_fact", f"{probe['id']}: invalid expected behavior")
        require(probe["unsupported_claim_probe"] not in " ".join(item["content"] for item in case_map[cid]["resume_evidence"]), f"{probe['id']}: probe already in source")

    return {"resumes": len(cases), "jobs": len(jobs),
            "comparisons": sum(len(case["comparisons"]) for case in cases),
            "tailor_probes": len(tailor_cases),
            "synthetic": sum(case["source_kind"] == "synthetic" for case in cases),
            "deidentified_real": sum(case["source_kind"] == "deidentified_real" for case in cases)}


if __name__ == "__main__":
    print(json.dumps(validate(read("jobs.json"), read("cases.json"), read("tailor_cases.json")), ensure_ascii=False))
