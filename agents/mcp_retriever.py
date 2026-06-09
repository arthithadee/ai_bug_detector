"""
MCP Documentation Retriever 
Queries MCP server for vector docs on RDI code.
"""

import asyncio
import logging
import json
from dataclasses import dataclass
from typing import List

from agents.data_ingestion import InferredContext
import config

logger = logging.getLogger(__name__)

@dataclass
class MCPResult:
    text: str
    score: float

class DocSearcher:
    """
    Search agent connecting to FastMCP to fetch context docs.
    """
    def __init__(self, endpoint: str = None):
        self.endpoint = endpoint or config.MCP_SERVER_URL
        self._is_online = None
        logger.info(f"DocSearcher started with {self.endpoint}")

    def fetch_docs(self, ctx: InferredContext) -> List[MCPResult]:
        if not getattr(config, "MCP_ENABLED", True) or self._is_online is False:
            return []
        try:
            return asyncio.run(self._run_async(ctx))
        except Exception as e:
            logger.warning(f"Search failed for {ctx.sample_id}: {e}")
            self._is_online = False
            return []

    async def _run_async(self, ctx: InferredContext) -> List[MCPResult]:
        docs = []
        try:
            from fastmcp import Client
            async with Client(self.endpoint) as client:
                self._is_online = True
                for q in ctx.search_queries:
                    try:
                        resp = await client.call_tool("search_documents", {"query": q})
                        docs.extend(self._format_response(resp))
                    except Exception as err:
                        logger.debug(f"Query err: {err}")
        except Exception as err:
            logger.warning(f"Connection err: {err}")
            self._is_online = False

        unique_docs = self._remove_dups(docs)
        unique_docs.sort(key=lambda x: x.score, reverse=True)
        return unique_docs[:getattr(config, "MCP_QUERY_TOP_K", 3)]

    def _format_response(self, raw_data) -> List[MCPResult]:
        out = []
        try:
            if isinstance(raw_data, list):
                for i in raw_data:
                    txt = getattr(i, 'text', str(i))
                    try:
                        p = json.loads(txt)
                        if isinstance(p, list):
                            for d in p:
                                if isinstance(d, dict):
                                    out.append(MCPResult(d.get("text", ""), float(d.get("score", 0))))
                        elif isinstance(p, dict):
                            out.append(MCPResult(p.get("text", ""), float(p.get("score", 0))))
                    except (json.JSONDecodeError, TypeError):
                        out.append(MCPResult(txt, 0.5))
        except Exception:
            pass
        return out

    def _remove_dups(self, docs: List[MCPResult]) -> List[MCPResult]:
        seen = set()
        res = []
        for d in docs:
            k = d.text[:100].strip()
            if k and k not in seen:
                seen.add(k)
                res.append(d)
        return res
