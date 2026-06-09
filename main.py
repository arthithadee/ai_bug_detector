"""
Bug Hunter Coordinator - Pure CLI Run
Sequence: Data Ingestion -> MCP Search -> Rule Check -> [AI Check] -> Report Generation
No GUI, no flags. Reads samples.csv, outputs to output.csv.
"""

import sys
import os
import logging
import time

import argparse

# Inject local module paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from agents.data_ingestion import DataProcessor
from agents.mcp_retriever import DocSearcher
from agents.rule_analyzer import StaticAnalyzer
from agents.bug_reporter import ReportGenerator
from agents.llm_analyzer import AIAnalyzer
from agents.mcp_validator import DocumentValidator
from agents.rule_learner import AutoRuleBuilder
from utils.csv_utils import write_output_csv, validate_output_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("CLI_Pipeline")

def run():
    parser = argparse.ArgumentParser(description="EDITH Bug Detector - CLI")
    parser.add_argument("input_file", nargs="?", default="samples.csv", help="Input CSV file to analyze (default: samples.csv)")
    parser.add_argument("-o", "--output", default="output.csv", help="Output CSV file (default: output.csv)")
    args = parser.parse_args()

    print("\n============================================================")
    print("   [*] EDITH Bug Detector - CLI")
    print("   RDI C++ Analysis (Rules based + AI Intelligent fused)")
    print("============================================================\n")

    start_t = time.time()
    
    in_file = args.input_file if os.path.isabs(args.input_file) else os.path.join(config.BASE_DIR, args.input_file)
    out_file = args.output if os.path.isabs(args.output) else os.path.join(config.BASE_DIR, args.output)

    # --- Phase 1: Ingest Data ---
    logger.info("=== Phase 1: Ingestion & Context ===")
    dp = DataProcessor(in_file)
    records = dp.load_samples()
    logger.info(f"Loaded {len(records)} samples.")
    
    contexts = {r.id: dp.process_context(r) for r in records}

    # --- Phase 2: Search Docs & Static Checks ---
    logger.info("=== Phase 2: Static Analysis ===")
    searcher = DocSearcher()
    mcp_docs = {r.id: searcher.fetch_docs(contexts[r.id]) for r in records}
    
    analyzer = StaticAnalyzer()
    violations = {r.id: analyzer.run_checks(r, contexts[r.id], mcp_docs[r.id]) for r in records}

    # --- Phase 3: AI Fallback ---
    logger.info("=== Phase 3: AI Rescue ===")
    ai = AIAnalyzer()
    val = DocumentValidator()
    rb = AutoRuleBuilder()
    
    ai_up = 0
    ai_rej = 0
    rules_added = 0

    unmatched = [r for r in records if violations[r.id].rule_name == "no_match"]
    logger.info(f"{len(unmatched)} records passed to AI.")

    for r in unmatched:
        ans = ai.scan_for_bugs(r, contexts[r.id], mcp_docs[r.id])
        if not ans or not ans.bug_detected: continue

        chk = val.verify_finding(ans, mcp_docs[r.id], r)
        if not chk.validated:
            ai_rej += 1
            continue

        cite = f" | Doc ref: {chk.supporting_docs[0][:100]}" if chk.supporting_docs else ""
        violation = violations[r.id]
        violation.rule_name = f"ai_found_{ans.bug_type}"
        violation.line_number = ans.bug_line
        violation.explanation = f"Line {ans.bug_line}: {ans.bug_type} - {ans.reasoning[:350]}{cite}"
        violation.confidence = ans.confidence
        ai_up += 1

        new_rule = rb.construct_rule(ans, chk)
        if new_rule: rules_added += 1

    # --- Phase 4: Reports ---
    logger.info("=== Phase 4: Output Generation ===")
    rep_gen = ReportGenerator()
    reports = [rep_gen.compile(r, violations[r.id], contexts[r.id], mcp_docs[r.id]) for r in records]

    # Quick summary
    from collections import namedtuple
    ReportTup = namedtuple('ReportTup', ['id', 'bug_line', 'explanation'])
    tuples = [ReportTup(r.id, r.bug_line, r.explanation) for r in reports]
    
    of = write_output_csv(tuples, out_file)
    verdict = validate_output_csv(of)

    elapsed = time.time() - start_t
    print(f"\nCompleted in {elapsed:.1f}s. AI Upgrades: {ai_up}. CSV status: {'Pass' if verdict['valid'] else 'Fail'}.")
    print(f"Results saved to {of}.")

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("Aborted.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
