"""
MCP Validator - cross-checks AI findings with docs.
"""

import logging
import re
from typing import List
from dataclasses import dataclass

from agents.data_ingestion import SampleRecord
from agents.mcp_retriever import MCPResult
from agents.llm_analyzer import LLMFinding
import config

logger = logging.getLogger(__name__)

@dataclass
class MCPValidation:
    validated: bool
    supporting_docs: List[str]
    validation_reason: str = ""

class DocumentValidator:
    """
    Verifies that the LLM didn't hallucinate API rules.
    """
    def __init__(self):
        logger.info("DocumentValidator started.")

    def verify_finding(self, finding: LLMFinding, docs: List[MCPResult], item: SampleRecord) -> MCPValidation:
        if not finding.bug_detected:
            return MCPValidation(False, [], "No bug to validate.")

        thresh = getattr(config, "LLM_CONFIDENCE_THRESHOLD", 0.75)
        if finding.confidence < thresh:
            return MCPValidation(False, [], f"Confidence {finding.confidence} < {thresh}")

        if not docs:
            if finding.confidence >= 0.85:
                return MCPValidation(True, [], "No docs, but conf is high enough.")
            return MCPValidation(False, [], "No docs to validate against.")

        llm_kw = self._get_kws(finding.reasoning + " " + finding.bug_type)
        sup = []
        ov = 0

        for d in docs:
            if d.score < 0.2: continue
            dkw = self._get_kws(d.text)
            inter = llm_kw & dkw
            if len(inter) >= 2:
                sup.append(d.text[:200] + ("..." if len(d.text) > 200 else ""))
                ov += len(inter)

        if sup:
            return MCPValidation(True, sup, f"Found {len(sup)} docs with {ov} overlap.")

        if finding.confidence >= 0.9:
            return MCPValidation(True, [], "No docs hit, but confidence >= 0.9")

        return MCPValidation(False, [], "No supporting docs found for keyword match.")

    def _get_kws(self, txt: str) -> set:
        toks = {t.lower() for t in re.findall(r'[a-zA-Z_]\w{2,}', txt)}
        stops = {"the","and","for","that","this","with","from","not","are","was","but","has","had","have","been",
                 "will","can","should","would","could","may","must","shall","used","use","using","line","code",
                 "function","method","call","value","parameter","argument","type","error","bug","issue","incorrect",
                 "wrong","invalid"}
        return toks - stops
