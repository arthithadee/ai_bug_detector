"""
Reporter module for structuring bugs into plain output logs/csv rows.
"""

import logging
from dataclasses import dataclass
from typing import List

from agents.data_ingestion import SampleRecord, InferredContext
from agents.mcp_retriever import MCPResult
from agents.rule_analyzer import RuleViolation
import config

logger = logging.getLogger(__name__)

@dataclass
class BugReport:
    id: int
    bug_line: int
    explanation: str

class ReportGenerator:
    """
    Creates final concise explanations of the bugs.
    """
    def __init__(self):
        logger.info("ReportGenerator started.")

    def compile(self, item: SampleRecord, violation: RuleViolation, ctx: InferredContext, docs: List[MCPResult]) -> BugReport:
        desc = violation.explanation

        if docs and violation.confidence < 0.95:
            doc_ctx = self._get_doc_context(docs)
            if doc_ctx:
                desc = f"{desc} {doc_ctx}"

        desc = " ".join(desc.split())
        max_len = getattr(config, "MAX_EXPLANATION_LENGTH", 250)
        if len(desc) > max_len:
            desc = desc[:max_len - 3] + "..."

        return BugReport(id=item.id, bug_line=violation.line_number, explanation=desc)

    def _get_doc_context(self, docs: List[MCPResult]) -> str:
        if not docs: return ""
        d = docs[0]
        if d.score < 0.3: return ""
        text = d.text[:150].strip()
        if len(d.text) > 150: text += "..."
        return f"(Doc context: {text})"
