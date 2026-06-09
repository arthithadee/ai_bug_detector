"""
Loads CSV samples and extracts RDI API chains/contexts to prepare for analysis.
"""

import csv
import re
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class SampleRecord:
    id: int
    code: str
    explanation: str = ""
    context: str = ""
    correct_code: str = ""

@dataclass
class CodeLine:
    line_number: int
    content: str
    stripped: str

@dataclass
class InferredContext:
    sample_id: int
    api_calls: List[str]
    api_methods: List[str]
    search_queries: List[str]
    code_lines: List[CodeLine]

# --- Extractors ---

RDI_API_PATTERN = re.compile(r'rdi\.[\w()."\',:+\-*/\s]*(?:;|$)', re.MULTILINE)
METHOD_PATTERN = re.compile(r'\.(\w+)\s*\(')
ROOT_METHOD_PATTERN = re.compile(r'rdi\.(\w+)')

class DataProcessor:
    """
    Handles both ingestion of CSV records and inference of API context.
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        logger.info(f"DataProcessor linked to file: {file_path}")

    def load_and_infer(self) -> List[InferredContext]:
        records = self._read_csv()
        contexts = []
        for rec in records:
            ctx = self._extract_context(rec)
            contexts.append((rec, ctx))
        return contexts  # Actually, let's keep it separate or accessible. Return tuple.

    def load_samples(self) -> List[SampleRecord]:
        return self._read_csv()

    def _read_csv(self) -> List[SampleRecord]:
        logger.info(f"Reading from {self.file_path}")
        results = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cols = set(reader.fieldnames or [])
            if not {"ID", "Code"}.issubset(cols):
                raise ValueError("Missing ID or Code columns")

            has_ctx = "Context" in cols
            has_corr = "Correct Code" in cols
            has_exp = "Explanation" in cols

            for i, row in enumerate(reader, 2):
                try:
                    obj = SampleRecord(
                        id=int(row["ID"].strip()),
                        code=row["Code"].strip(),
                        context=row.get("Context", "").strip() if has_ctx else "",
                        correct_code=row.get("Correct Code", "").strip() if has_corr else "",
                        explanation=row.get("Explanation", "").strip() if has_exp else "",
                    )
                    results.append(obj)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Row {i} error: {e}")
        return results

    def process_context(self, item: SampleRecord) -> InferredContext:
        return self._extract_context(item)

    def _extract_context(self, item: SampleRecord) -> InferredContext:
        lines = self._get_lines(item.code)
        apis = self._get_apis(item.code)
        methods = self._get_methods(item.code, item.context)
        queries = self._build_queries(item.context, methods, apis)

        return InferredContext(
            sample_id=item.id,
            api_calls=apis,
            api_methods=methods,
            search_queries=queries,
            code_lines=lines,
        )

    def _get_lines(self, src: str) -> List[CodeLine]:
        raw_parts = src.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        return [CodeLine(line_number=idx+1, content=L, stripped=L.strip()) for idx, L in enumerate(raw_parts)]

    def _get_apis(self, src: str) -> List[str]:
        return [match.strip().rstrip(";").strip() for match in RDI_API_PATTERN.findall(src) if match.strip()]

    def _get_methods(self, src: str, ctx: str) -> List[str]:
        text = f"{src}\n{ctx}"
        found = []
        for m in METHOD_PATTERN.findall(text):
            if m not in found:
                found.append(m)
        for m in ROOT_METHOD_PATTERN.findall(text):
            if m not in found:
                found.append(m)
        return found

    def _build_queries(self, ctx: str, meth: List[str], apis: List[str]) -> List[str]:
        q = []
        if ctx:
            top_line = ctx.split("\n")[0].strip()
            if top_line:
                q.append(top_line)
        
        core_methods = [m for m in meth if m not in ("pin", "execute", "begin", "end", "id")]
        if core_methods:
            q.append(f"rdi {' '.join(core_methods[:4])} parameters usage")
            
        if apis:
            for c in apis:
                if len(c) > 20:
                    q.append(c[:100])
                    break
        return q[:3]
