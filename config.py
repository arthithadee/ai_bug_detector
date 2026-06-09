"""
============================================================
PHASE 0: Configuration & Constants
============================================================
Central configuration for the Agentic Bug Hunter system.
All tunable parameters and known RDI API patterns are defined here.
"""

import os

# ── Paths ──────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_CSV_PATH = os.path.join(BASE_DIR, "samples.csv")
OUTPUT_CSV_PATH = os.path.join(BASE_DIR, "output.csv")

# ── MCP Server ─────────────────────────────────────────────
MCP_SERVER_URL = "http://localhost:8003/sse"
MCP_QUERY_TOP_K = 5
MCP_TIMEOUT_SECONDS = 30
MCP_ENABLED = True

# ── Load .env if present (local dev) ───────────────────────
ENV_FILE = os.path.join(BASE_DIR, ".env")
if os.path.exists(ENV_FILE):
    with open(ENV_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

# ── Groq / LLM Fallback ───────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = "openai/gpt-oss-120b"
LLM_TEMPERATURE = 0.15
LLM_MAX_TOKENS = 8192
LLM_CONFIDENCE_THRESHOLD = 0.6   # Minimum LLM confidence to proceed
LLM_FALLBACK_ENABLED = True      # Master switch for LLM fallback
LEARNED_RULES_DIR = os.path.join(BASE_DIR, "rules")

# ── Output ─────────────────────────────────────────────────
OUTPUT_COLUMNS = ["ID", "Bug Line", "Explanation"]
MAX_EXPLANATION_LENGTH = 500

# ── Known Valid RDI Getter Functions ───────────────────────
# These are the correct function names for rdi.id(...).getXxx()
VALID_GETTER_FUNCTIONS = {
    "getVector", "getValue", "getWaveform", "getPassFail",
    "getMultiPassFail", "getReadBit", "getReadData", "getFFV",
    "getAlarmValue", "getAlarmBurstValue", "getHumSensor",
    "getTempThresh", "getMeasValue", "getBurstPassFail",
    "getAverage", "getSamples", "getDigCapData",
}

# ── Known Valid RDI API Methods ────────────────────────────
# Methods in rdi.xxx() chains that are valid
VALID_RDI_METHODS = {
    "dc", "func", "emap", "digCap", "smartVec", "protocol",
    "alarm", "route", "pmux", "cogo", "port", "wait",
    "pin", "vForce", "iForce", "vMeas", "iMeas",
    "vForceRange", "iForceRange", "iMeasRange", "vMeasRange",
    "iClamp", "vClamp", "execute", "burst", "begin", "end",
    "label", "copyLabel", "writeData", "readBit", "readData",
    "waveform", "addWaveform", "repeat", "FS", "samples",
    "FFV", "module", "readHumSensor", "readTempThresh",
    "setOn", "setOff", "retrievePmuxPinStatus",
    "enable", "node", "passNode", "failNode",
    "burstUpload", "burstRunTime", "runTimeVal",
    "vecEditMode", "readMode", "initDiscard",
    "digCapBurstSiteUpload", "pname", "write", "read",
    "interSiteUpload", "id",
}

# ── Known Typo Corrections ─────────────────────────────────
# Maps common wrong function names to correct ones
KNOWN_TYPO_CORRECTIONS = {
    "iMeans": "iMeas",
    "vMeans": "vMeas",
    "imeas": "iMeas",
    "imeasRange": "iMeasRange",
    "imeasrange": "iMeasRange",
    "vmeas": "vMeas",
    "readHumanSeniority": "readHumSensor",
    "getHumanSeniority": "getHumSensor",
    "getFFC": "getFFV",
    "push_forward": "push_back",
}

# ── Valid AVI64 vForceRange Values ─────────────────────────
VALID_VFORCE_RANGES = {2, 5, 10, 15, 20, 30}

# ── Max Allowed Values ─────────────────────────────────────
MAX_DIGCAP_SAMPLES = 8192

# ── Valid Vector<string> Methods ───────────────────────────
VALID_VECTOR_METHODS = {
    "clear", "push_back", "pop_back", "size", "empty",
    "begin", "end", "erase", "insert", "resize",
    "at", "front", "back", "data", "assign",
}

# ── Valid Units ────────────────────────────────────────────
VALID_UNITS = {"V", "mV", "uV", "A", "mA", "uA", "nA", "kHz", "MHz", "Hz", "ms", "us", "ns", "s"}
INVALID_UNITS = {"mAh": "mA", "Ah": "A"}
