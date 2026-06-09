"""
Rule Learner - converts LLM answers into rules.
"""

import os
import hashlib
import logging
import re
from datetime import datetime
from typing import Optional

from agents.llm_analyzer import LLMFinding
from agents.mcp_validator import MCPValidation
import config

logger = logging.getLogger(__name__)

class AutoRuleBuilder:
    def __init__(self):
        self.r_dir = config.LEARNED_RULES_DIR
        self.r_file = os.path.join(self.r_dir, "learned_rules.py")
        self._init_dir()
        self._hashes = self._load()

    def _init_dir(self):
        os.makedirs(self.r_dir, exist_ok=True)
        it = os.path.join(self.r_dir, "__init__.py")
        if not os.path.exists(it):
            with open(it, "w") as f: f.write('""\n')
        if not os.path.exists(self.r_file):
            with open(self.r_file, "w") as f:
                f.write('LEARNED_RULES = {}\ndef register_rule(n):\n    def dec(fn):\n        LEARNED_RULES[n] = fn\n        return fn\n    return dec\n\n')

    def construct_rule(self, finding: LLMFinding, val: MCPValidation) -> Optional[str]:
        if not finding.suggested_rule: return None
        r = finding.suggested_rule
        h = hashlib.sha256(f"{r.rule_name}::{r.detection_pattern}".encode()).hexdigest()[:16]

        if h in self._hashes: return None

        code = self._run_code_gen(finding, val, h)
        try:
            with open(self.r_file, "a", encoding="utf-8") as f: f.write(code)
            self._hashes.add(h)
            return r.rule_name
        except Exception as e:
            logger.error(f"Save fail: {e}")
            return None

    def _run_code_gen(self, f: LLMFinding, v: MCPValidation, h: str) -> str:
        r = f.suggested_rule
        sn = re.sub(r'[^a-z0-9_]', '_', r.rule_name.lower())
        d = r.description.replace('"', '\\"')
        p = r.detection_pattern.replace('"', '\\"')
        bt = f.bug_type.replace('"', '\\"')
        cite = f" According to docs: {v.supporting_docs[0][:100]}" if v.supporting_docs else ""
        
        return f'''
# Hash: {h}
@register_rule("{sn}")
def _chk_{sn}(lines, code, sample):
    """{d}"""
    import re
    try:
        pat = re.compile(r"""{p}""", re.IGNORECASE)
        for L in lines:
            if pat.search(L.stripped):
                return (L.line_number, f"Line {{L.line_number}}: {bt} - {d} |{cite}", {f.confidence:.2f})
    except:
        sm = """{p}""".lower()
        for L in lines:
            if sm in L.stripped.lower():
                return (L.line_number, f"Line {{L.line_number}}: {bt} - {d} |{cite}", {f.confidence:.2f})
    return None
'''

    def _load(self):
        s = set()
        if os.path.exists(self.r_file):
            with open(self.r_file, "r", encoding="utf-8") as f:
                for ln in f:
                    if ln.startswith("# Hash:"): s.add(ln.replace("# Hash:", "").strip())
        return s
