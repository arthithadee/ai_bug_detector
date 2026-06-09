"""
AI Fallback Agent
Uses Groq API to scan for bugs if static checks fail.
"""

import json
import logging
from typing import List, Optional
from dataclasses import dataclass
from groq import Groq

from agents.data_ingestion import SampleRecord, InferredContext
from agents.mcp_retriever import MCPResult
import config

logger = logging.getLogger(__name__)

@dataclass
class SuggestedRule:
    rule_name: str
    description: str
    detection_pattern: str
    severity: str = "HIGH"

@dataclass
class LLMFinding:
    bug_detected: bool
    bug_line: int = 0
    bug_type: str = ""
    reasoning: str = ""
    confidence: float = 0.0
    suggested_rule: Optional[SuggestedRule] = None

SYS_PROMPT = """You are a senior C++ logic validator for RDI tests.
Given a code snippet, locate any RDI API misuse.
Reply ONLY with a strictly valid JSON object. No markdown fences.
Schema:
{
  "bug_detected": boolean,
  "bug_line": integer,
  "bug_type": "snake_case_name",
  "reasoning": "short explanation",
  "confidence": float 0.0 to 1.0,
  "suggested_rule": {
    "rule_name": "...",
    "description": "...",
    "detection_pattern": "...",
    "severity": "MEDIUM|HIGH|CRITICAL"
  }
}
Common issues: Missing RDI_BEGIN/END, invalid measurements, type mismatches.
"""

class AIAnalyzer:
    """
    Calls out to Groq when the deterministic static rules fail to find bugs.
    """
    def __init__(self):
        self.api_client = None
        self._is_active = False
        logger.info("AIAnalyzer booted.")

    def _setup_client(self):
        if not self._is_active:
            try:
                self.api_client = Groq(api_key=config.GROQ_API_KEY)
                self._is_active = True
            except Exception as e:
                logger.error(f"Groq setup err: {e}")
                self._is_active = False

    def scan_for_bugs(self, item: SampleRecord, ctx: InferredContext, docs: List[MCPResult]) -> Optional[LLMFinding]:
        self._setup_client()
        if not self.api_client: return None

        p = self._make_prompt(item, ctx)
        try:
            resp = self.api_client.chat.completions.create(
                model=getattr(config, "GROQ_MODEL", "llama3-8b-8192"),
                messages=[{"role": "system", "content": SYS_PROMPT}, {"role": "user", "content": p}],
                temperature=getattr(config, "LLM_TEMPERATURE", 0.15),
                max_completion_tokens=getattr(config, "LLM_MAX_TOKENS", 500)
            )
            txt = resp.choices[0].message.content
            return self._decode_finding(txt, item.id)
        except Exception as e:
            logger.error(f"LLM fail {item.id}: {e}")
            return None

    def _make_prompt(self, item: SampleRecord, ctx: InferredContext) -> str:
        lns = "\n".join(f"{c.line_number}: {c.content}" for c in ctx.code_lines)
        base = [ "Find RDI API bugs here:", "== CODE ==", lns ]
        if ctx.api_methods: base.extend(["", "== METHODS ==", ", ".join(ctx.api_methods)])
        if item.context: base.extend(["", "== DEV INTENT ==", item.context])
        base.append("REPLY JSON ONLY.")
        return "\n".join(base)

    def _decode_finding(self, txt: str, id_: int) -> Optional[LLMFinding]:
        txt = txt.strip()
        if txt.startswith("```"):
            lns = txt.split("\n")
            txt = "\n".join(l for l in lns if not l.startswith("```"))
        try:
            d = json.loads(txt)
        except json.JSONDecodeError:
            si = txt.find("{")
            ei = txt.rfind("}") + 1
            if si >= 0 and ei > si:
                try: d = json.loads(txt[si:ei])
                except json.JSONDecodeError: return None
            else: return None

        sr = None
        if "suggested_rule" in d and isinstance(d["suggested_rule"], dict):
            s_dict = d["suggested_rule"]
            sr = SuggestedRule(
                s_dict.get("rule_name", "unk"),
                s_dict.get("description", ""),
                s_dict.get("detection_pattern", ""),
                s_dict.get("severity", "MEDIUM")
            )
        return LLMFinding(
            bool(d.get("bug_detected", False)),
            int(d.get("bug_line", 0)),
            str(d.get("bug_type", "")),
            str(d.get("reasoning", "")),
            float(d.get("confidence", 0)),
            sr
        )
