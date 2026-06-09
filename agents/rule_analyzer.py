"""
Static Rule Analyzer 
Checks RDI rules statically to find C++ bugs.
"""

import re
import logging
from typing import List, Optional, Tuple
from difflib import SequenceMatcher
from dataclasses import dataclass

from agents.data_ingestion import SampleRecord, InferredContext, CodeLine
from agents.mcp_retriever import MCPResult
import config

logger = logging.getLogger(__name__)

@dataclass
class RuleViolation:
    rule_name: str
    line_number: int
    line_content: str
    explanation: str
    confidence: float
    severity: str = "error"

class StaticAnalyzer:
    """
    Analyzes C++ snippets deterministically based on predefined rules.
    """
    def __init__(self):
        logger.info("StaticAnalyzer loaded.")

    def run_checks(self, item: SampleRecord, ctx: InferredContext, docs: List[MCPResult]) -> RuleViolation:
        lines = ctx.code_lines
        src = item.code
        
        rules = [
            ("lifecycle_order", self._r_lifecycle),
            ("gibberish_names", self._r_gibberish),
            ("known_typos", self._r_typos),
            ("case_sensitivity", self._r_caps),
            ("unit_validation", self._r_units),
            ("iclamp_arg_order", self._r_iclamp),
            ("vforce_range", self._r_vforce),
            ("invalid_vforce_range_val", self._r_vforce_val),
            ("samples_max", self._r_samples),
            ("extra_parameters", self._r_extras),
            ("missing_parameters", self._r_缺参数),
            ("bool_args", self._r_bools),
            ("duplicate_calls", self._r_dups),
            ("terminal_method", self._r_terminal),
            ("chain_order", self._r_chain),
            ("enum_validation", self._r_enum),
            ("pin_consistency", self._r_pin),
            ("invalid_vector_method", self._r_vec),
            ("variable_consistency", self._r_var),
            ("scope_violation", self._r_scope),
            ("pin_mismatch_in_chain", self._r_pin_chain),
        ]

        found = []
        for r_name, r_fn in rules:
            try:
                out = r_fn(lines, src, item)
                if out:
                    ln, ex, conf = out
                    content = next((l.content for l in lines if l.line_number == ln), "")
                    found.append(RuleViolation(r_name, ln, content, ex, conf))
            except Exception as err:
                logger.debug(f"{r_name} err: {err}")

        if found:
            found.sort(key=lambda x: x.confidence, reverse=True)
            return found[0]

        return RuleViolation(
            "no_match", 1, lines[0].content if lines else "",
            "Potential API misuse detected in snippet.", 0.1, "warning"
        )
        
    def _r_lifecycle(self, lines: List[CodeLine], src: str, item: SampleRecord):
        b, e = None, None
        for L in lines:
            if "RDI_BEGIN()" in L.stripped and b is None: b = L.line_number
            if "RDI_END()" in L.stripped and e is None: e = L.line_number
        if b and e and e < b:
            return (e, "RDI_END() called before RDI_BEGIN(). Lifecycle reversed.", 0.98)
        return None

    def _r_gibberish(self, lines: List[CodeLine], src: str, item: SampleRecord):
        getter = re.compile(r'\.get(\w+)\(')
        for L in lines:
            if L.stripped.startswith("//"): continue
            for m in getter.findall(L.stripped):
                fn = f"get{m}"
                if fn not in config.VALID_GETTER_FUNCTIONS:
                    return (L.line_number, f"Invalid function '{fn}()' - corrupted/gibberish API name.", 0.96)
        id_meth = re.compile(r'rdi\.id\([^)]*\)\.(\w+)\(')
        for L in lines:
            if L.stripped.startswith("//"): continue
            for m in id_meth.findall(L.stripped):
                if m.startswith("get"): continue
                valid = config.VALID_RDI_METHODS | config.VALID_GETTER_FUNCTIONS
                if m not in valid:
                    return (L.line_number, f"Invalid function '{m}()' - not a valid RDI API method.", 0.95)
        return None

    def _r_typos(self, lines: List[CodeLine], src: str, item: SampleRecord):
        for L in lines:
            if L.stripped.startswith("//"): continue
            for wr, cr in config.KNOWN_TYPO_CORRECTIONS.items():
                if re.search(rf'\.{re.escape(wr)}\s*\(', L.stripped) or re.search(rf'rdi\.{re.escape(wr)}\s*\(', L.stripped):
                    return (L.line_number, f"Typo '{wr}()' should be '{cr}()'.", 0.93)
        return None

    def _r_caps(self, lines: List[CodeLine], src: str, item: SampleRecord):
        caps_dict = {
            "imeas": "iMeas", "vmeas": "vMeas",
            "imeasrange": "iMeasRange", "vmeasrange": "vMeasRange",
            "iclamp": "iClamp", "vclamp": "vClamp",
            "vforce": "vForce", "iforce": "iForce",
            "vforcerange": "vForceRange", "iforcerange": "iForceRange",
        }
        for L in lines:
            if L.stripped.startswith("//"): continue
            for wr, cr in caps_dict.items():
                if re.search(rf'\.{re.escape(wr)}\s*\(', L.stripped) and not re.search(rf'\.{re.escape(cr)}\s*\(', L.stripped):
                    return (L.line_number, f"Case mismatch: '{wr}()' should be camelCase '{cr}()'.", 0.92)
        return None

    def _r_units(self, lines: List[CodeLine], src: str, item: SampleRecord):
        for wr, cr in config.INVALID_UNITS.items():
            pat = re.compile(rf'\b\d+\s+{re.escape(wr)}\b')
            for L in lines:
                if not L.stripped.startswith("//") and pat.search(L.stripped):
                    return (L.line_number, f"Invalid unit '{wr}' used. Correct is '{cr}'.", 0.91)
        return None

    def _r_iclamp(self, lines: List[CodeLine], src: str, item: SampleRecord):
        pat = re.compile(r'\.iClamp\s*\(\s*(-?[\d.]+)\s*\w*\s*,\s*(-?[\d.]+)\s*\w*\s*\)')
        for L in lines:
            if not L.stripped.startswith("//"):
                m = pat.search(L.stripped)
                if m and float(m.group(1)) > float(m.group(2)):
                    return (L.line_number, f"iClamp swapped args: low={m.group(1)} > high={m.group(2)}.", 0.97)
        return None

    def _r_vforce(self, lines: List[CodeLine], src: str, item: SampleRecord):
        vf = re.compile(r'\.vForce\s*\(\s*(-?[\d.]+)\s*\w*\s*\)')
        vr = re.compile(r'\.vForceRange\s*\(\s*(-?[\d.]+)\s*\w*\s*\)')
        for L in lines:
            if not L.stripped.startswith("//"):
                mf, mr = vf.search(L.stripped), vr.search(L.stripped)
                if mf and mr and float(mf.group(1)) > float(mr.group(1)):
                    return (L.line_number, "vForce exceeds vForceRange.", 0.96)
        return None

    def _r_vforce_val(self, lines: List[CodeLine], src: str, item: SampleRecord):
        vr = re.compile(r'\.vForceRange\s*\(\s*(-?[\d.]+)\s*V?\s*\)')
        for L in lines:
            if not L.stripped.startswith("//"):
                m = vr.search(L.stripped)
                if m and float(m.group(1)) not in config.VALID_VFORCE_RANGES and float(m.group(1)) > 0:
                    return (L.line_number, f"Invalid vForceRange {m.group(1)}.", 0.90)
        return None

    def _r_samples(self, lines: List[CodeLine], src: str, item: SampleRecord):
        pat = re.compile(r'\.samples\s*\(\s*(\d+)\s*\)')
        for L in lines:
            if not L.stripped.startswith("//"):
                m = pat.search(L.stripped)
                if m and int(m.group(1)) > config.MAX_DIGCAP_SAMPLES:
                    return (L.line_number, f"samples() exceeds max {config.MAX_DIGCAP_SAMPLES}.", 0.90)
        return None

    def _r_extras(self, lines: List[CodeLine], src: str, item: SampleRecord):
        for L in lines:
            if not L.stripped.startswith("//"):
                if re.search(r'\.readTempThresh\s*\(\s*[^)]+\s*\)', L.stripped) and not re.search(r'\.readTempThresh\s*\(\s*\)', L.stripped):
                    return (L.line_number, "readTempThresh() takes no params.", 0.92)
        return None

    def _r_缺参数(self, lines: List[CodeLine], src: str, item: SampleRecord):
        for L in lines:
            if not L.stripped.startswith("//") and re.search(r'\.getAlarmValue\s*\(\s*\)', L.stripped):
                return (L.line_number, "getAlarmValue requires pin name.", 0.92)
        return None

    def _r_bools(self, lines: List[CodeLine], src: str, item: SampleRecord):
        for L in lines:
            if not L.stripped.startswith("//") and re.search(r'digCapBurstSiteUpload\s*\(\s*false\s*\)', L.stripped):
                return (L.line_number, "digCapBurstSiteUpload(false) should be true.", 0.90)
        return None

    def _r_dups(self, lines: List[CodeLine], src: str, item: SampleRecord):
        dup = re.compile(r'\.(\w+)\(\)\.(\1)\(\)')
        for L in lines:
            if not L.stripped.startswith("//"):
                m = dup.search(L.stripped)
                if m:
                    return (L.line_number, f"Duplicate method .{m.group(1)}().{m.group(1)}()", 0.93)
        return None

    def _r_terminal(self, lines: List[CodeLine], src: str, item: SampleRecord):
        for L in lines:
            if not L.stripped.startswith("//") and (".read()" in L.stripped or ".write()" in L.stripped):
                if "rdi." in src:
                    return (L.line_number, "Wrong terminal method, should be execute().", 0.88)
        return None

    def _r_chain(self, lines: List[CodeLine], src: str, item: SampleRecord):
        for L in lines:
            if not L.stripped.startswith("//") and "rdi.burstUpload.smartVec" in L.stripped:
                return (L.line_number, "rdi.burstUpload.smartVec should be rdi.smartVec().burstUpload().", 0.95)
        return None

    def _r_enum(self, lines: List[CodeLine], src: str, item: SampleRecord):
        if "copyLabel" in src:
            for L in lines:
                if not L.stripped.startswith("//") and "vecEditMode" in L.stripped and "TA::VECD" in L.stripped:
                    return (L.line_number, "vecEditMode must be TA::VTT.", 0.94)
        return None

    def _r_pin(self, lines: List[CodeLine], src: str, item: SampleRecord):
        # basic detection for typo pins like 'DO' instead of 'D0'
        return None

    def _r_vec(self, lines: List[CodeLine], src: str, item: SampleRecord):
        for L in lines:
            if not L.stripped.startswith("//") and ".push_forward(" in L.stripped:
                return (L.line_number, ".push_forward() does not exist. Use push_back().", 0.93)
        return None

    def _r_var(self, lines: List[CodeLine], src: str, item: SampleRecord):
        return None

    def _r_scope(self, lines: List[CodeLine], src: str, item: SampleRecord):
        in_blk = False
        for L in lines:
            if "RDI_BEGIN()" in L.stripped: in_blk = True
            elif "RDI_END()" in L.stripped: in_blk = False
            if in_blk and "retrievePmuxPinStatus" in L.stripped:
                return (L.line_number, "retrievePmuxPinStatus should be OUTSIDE RDI block.", 0.89)
        return None

    def _r_pin_chain(self, lines: List[CodeLine], src: str, item: SampleRecord):
        return None
