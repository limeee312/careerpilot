"""Score reviewed Matcher predictions without calling an AI provider.

Usage: python tests/evals/score.py path/to/predictions.json
"""

import argparse
import json
import re
from pathlib import Path

from validate import read, require, validate


def normalize(text):
    return re.sub(r"\s+", "", text)


def ratio(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def score(predictions):
    jobs, cases = read("jobs.json"), read("cases.json")
    dataset = validate(jobs, cases, read("tailor_cases.json"))
    case_map = {case["id"]: case for case in cases}
    require(isinstance(predictions, list), "predictions must be an array")
    seen = set()
    top1 = top3 = unsuitable_last = gate_correct = critical_gate_false_passes = critical_gate_false_fails = gate_count = 0
    grounded = evidence_count = unsupported = reviewed_claims = 0

    for prediction in predictions:
        cid = prediction["case_id"]
        require(cid in case_map and cid not in seen, f"unknown or repeated case: {cid}")
        seen.add(cid)
        case = case_map[cid]
        ranked = prediction["ranked_job_ids"]
        gold_ids = [item["job_id"] for item in case["comparisons"]]
        require(len(ranked) == len(gold_ids) and set(ranked) == set(gold_ids), f"{cid}: incomplete ranking")
        top1 += ranked[0] == case["best_match"]
        top3 += len(set(ranked[:3]) & set(case["top_3"]))
        unsuitable_last += all(ranked.index(job_id) == len(ranked) - 1 for job_id in case["clearly_unsuitable"])
        expected_gates = {item["job_id"]: item["hard_gates"] for item in case["comparisons"]}
        actual_gates = prediction["hard_gates"]
        require(set(actual_gates) == set(expected_gates), f"{cid}: hard-gate job coverage")
        for job_id, expected in expected_gates.items():
            require(set(actual_gates[job_id]) == set(expected), f"{cid}/{job_id}: hard-gate key coverage")
            for key, gold in expected.items():
                actual = actual_gates[job_id][key]
                require(actual in {"PASS", "WARN", "FAIL"}, f"{cid}/{job_id}/{key}: invalid status")
                gate_count += 1
                gate_correct += actual == gold["status"]
                critical_gate_false_passes += gold["status"] == "FAIL" and actual == "PASS"
                critical_gate_false_fails += gold["status"] == "PASS" and actual == "FAIL"

        evidence = {(item["source_type"], item["source_id"]): item["content"] for item in case["resume_evidence"]}
        for ref in prediction.get("evidence_refs", []):
            require(ref["job_id"] in gold_ids, f"{cid}: unknown evidence job")
            evidence_count += 1
            grounded += normalize(ref["source_quote"]) in normalize(evidence.get((ref["source_type"], ref["source_id"]), ""))
        for claim in prediction.get("claim_reviews", []):
            require(claim["job_id"] in gold_ids and claim["claim"].strip() and claim["reviewer"].strip(), f"{cid}: incomplete claim review")
            require(type(claim["supported"]) is bool, f"{cid}: claim support must be boolean")
            reviewed_claims += 1
            unsupported += not claim["supported"]

    n = len(predictions)
    return {
        "dataset": dataset,
        "evaluated_cases": n,
        "coverage": ratio(n, len(cases)),
        "top_1_accuracy": ratio(top1, n),
        "top_3_recall": ratio(top3, 3 * n),
        "unsuitable_last_rate": ratio(unsuitable_last, n),
        "hard_gate_accuracy": ratio(gate_correct, gate_count),
        "critical_gate_false_passes": critical_gate_false_passes,
        "critical_gate_false_fails": critical_gate_false_fails,
        "evidence_grounding_rate": ratio(grounded, evidence_count),
        "reviewed_evidence_refs": evidence_count,
        "hallucination_rate": ratio(unsupported, reviewed_claims),
        "human_reviewed_claims": reviewed_claims,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions", type=Path)
    args = parser.parse_args()
    print(json.dumps(score(json.loads(args.predictions.read_text(encoding="utf-8"))), ensure_ascii=False, indent=2))
