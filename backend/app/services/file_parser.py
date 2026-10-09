"""Parse an uploaded procedure file into a single-row DataFrame."""

import io
import json
from pathlib import PurePath

import pandas as pd

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MiB, matching the frontend limit.
SUPPORTED_EXTENSIONS = {".csv", ".json", ".xlsx"}
# Identifier and outcome/label columns that must not be used as model input.
EXCLUDED_COLUMNS = ("id", "recur", "redo")

_XLSX_MAGIC = b"PK\x03\x04"


class FileParseError(ValueError):
    """The upload is unsupported or malformed. `status_code` is the HTTP status to return."""

    def __init__(self, detail: str, status_code: int = 422) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def parse_procedure_file(filename: str | None, content: bytes) -> pd.DataFrame:
    """Return exactly one procedure row, with excluded columns removed."""
    if not content:
        raise FileParseError("The uploaded file is empty.", 400)
    if len(content) > MAX_UPLOAD_BYTES:
        raise FileParseError("The uploaded file exceeds the 10 MiB limit.", 413)

    extension = PurePath(filename or "").suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise FileParseError("Unsupported file format. Upload a .csv, .json, or .xlsx file.", 415)

    # The extension alone does not prove the format, so each reader checks the content.
    if extension == ".xlsx":
        frame = _read_xlsx(content)
    elif extension == ".json":
        frame = _read_json(content)
    else:
        frame = _read_csv(content)

    frame = frame.dropna(how="all")
    if frame.empty or len(frame.columns) == 0:
        raise FileParseError("The uploaded file contains no data rows.")
    if len(frame) != 1:
        raise FileParseError(
            f"The uploaded file contains {len(frame)} rows. Upload one procedure per file."
        )

    frame.columns = [str(column).strip() for column in frame.columns]
    return frame.drop(columns=list(EXCLUDED_COLUMNS), errors="ignore").reset_index(drop=True)


def _read_csv(content: bytes) -> pd.DataFrame:
    if content.startswith(_XLSX_MAGIC):
        raise FileParseError("The file content does not match its .csv extension.", 415)
    try:
        return pd.read_csv(io.BytesIO(content))
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as error:
        raise FileParseError("The CSV file could not be parsed.") from error


def _read_json(content: bytes) -> pd.DataFrame:
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise FileParseError("The JSON file could not be parsed.") from error
    # Accept a single record object or a list of record objects.
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
        raise FileParseError("The JSON file must contain an object or a list of objects.")
    return pd.DataFrame.from_records(data)


def _read_xlsx(content: bytes) -> pd.DataFrame:
    if not content.startswith(_XLSX_MAGIC):
        raise FileParseError("The file content does not match its .xlsx extension.", 415)
    try:
        return pd.read_excel(io.BytesIO(content), engine="openpyxl")
    except Exception as error:  # openpyxl raises a variety of types for corrupt workbooks.
        raise FileParseError("The XLSX file could not be parsed.") from error
