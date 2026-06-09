"""
============================================================
PHASE 3: CSV Utilities
============================================================
Handles writing the final output.csv in the required format.

Output format:
    ID,Bug Line,Explanation
    16,1,"Use only the VTT mode..."
============================================================
"""

import csv
import logging
from typing import List

from agents.bug_reporter import BugReport
import config

logger = logging.getLogger(__name__)


def write_output_csv(reports: List[BugReport], output_path: str = None) -> str:
    """
    Write bug reports to output.csv in the required format.

    Args:
        reports: List of BugReport objects from ExplanationAgent
        output_path: Optional override for output file path

    Returns:
        str: Path to the written CSV file

    Format:
        ID,Bug Line,Explanation
    """
    path = output_path or config.OUTPUT_CSV_PATH
    logger.info(f"Writing {len(reports)} reports to: {path}")

    # Sort by ID for consistent output
    sorted_reports = sorted(reports, key=lambda r: r.id)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(config.OUTPUT_COLUMNS)  # Header: ID, Bug Line, Explanation

        for report in sorted_reports:
            writer.writerow([
                report.id,
                report.bug_line,
                report.explanation,
            ])

    logger.info(f"Output CSV written successfully: {path}")
    return path


def validate_output_csv(path: str) -> dict:
    """
    Validate the output CSV format and content.

    Returns:
        dict with validation results:
            - valid: bool
            - row_count: int
            - errors: List[str]
    """
    errors = []
    row_count = 0

    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Check headers
            expected = set(config.OUTPUT_COLUMNS)
            actual = set(reader.fieldnames or [])
            if expected != actual:
                errors.append(f"Header mismatch: expected {expected}, got {actual}")

            for row_num, row in enumerate(reader, start=2):
                row_count += 1

                # Check ID is a positive integer
                try:
                    id_val = int(row.get("ID", ""))
                    if id_val <= 0:
                        errors.append(f"Row {row_num}: ID must be positive, got {id_val}")
                except ValueError:
                    errors.append(f"Row {row_num}: ID is not a valid integer")

                # Check Bug Line is a positive integer
                try:
                    line_val = int(row.get("Bug Line", ""))
                    if line_val <= 0:
                        errors.append(f"Row {row_num}: Bug Line must be positive, got {line_val}")
                except ValueError:
                    errors.append(f"Row {row_num}: Bug Line is not a valid integer")

                # Check Explanation is non-empty
                explanation = row.get("Explanation", "").strip()
                if not explanation:
                    errors.append(f"Row {row_num}: Explanation is empty")

    except FileNotFoundError:
        errors.append(f"File not found: {path}")
    except Exception as e:
        errors.append(f"Error reading file: {e}")

    return {
        "valid": len(errors) == 0,
        "row_count": row_count,
        "errors": errors,
    }
