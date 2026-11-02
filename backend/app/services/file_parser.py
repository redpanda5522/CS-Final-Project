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


def parse_procedure_file(
    filename: str | None, content: bytes, row_index: int | None = None
) -> tuple[pd.DataFrame, int]:
    """Return one procedure row, with excluded columns removed, and the file's row count.

    A file with several rows needs `row_index` (0-based, counting only non-empty rows,
    the same way the frontend's CSV preview numbers them).
    """
    frame = _read_upload(filename, content)
    row_count = len(frame)
    if row_index is None:
        if row_count != 1:
            raise FileParseError(
                f"The uploaded file contains {row_count} rows. Choose a row in the CSV preview, "
                "or upload one procedure per file."
            )
        row_index = 0
    elif row_index >= row_count:
        raise FileParseError(
            f"Row {row_index + 1} does not exist; the uploaded file has {row_count} "
            f"row{'' if row_count == 1 else 's'}."
        )

    row = frame.iloc[[row_index]].reset_index(drop=True)
    row.columns = [str(column).strip() for column in row.columns]
    return row.drop(columns=list(EXCLUDED_COLUMNS), errors="ignore"), row_count

'''
    Parse a training file into a DataFrame.
    @param filename: The name of the uploaded file
    @param content: The content of the uploaded file
    @param target_column: The column to predict
    @return: A DataFrame containing the training data
'''
def parse_train_file(
    filename: str | None, content: bytes, target_column: str = "recur"
) -> pd.DataFrame:
    """Return all non-empty rows, preserving the requested target column."""
    frame = _read_upload(filename, content)
    normalized_columns = [str(column).strip() for column in frame.columns]
    normalized_keys = [column.casefold() for column in normalized_columns]
    target_key = target_column.strip().casefold()
    if any(not column for column in normalized_columns):
        raise FileParseError("The training file contains an empty column name.")
    if len(set(normalized_keys)) != len(normalized_keys):
        raise FileParseError("The training file contains duplicate column names.")
    if not target_key:
        raise FileParseError("The target column name must not be empty.")
    frame.columns = normalized_columns
    if target_key not in normalized_keys:
        raise FileParseError(f"The training file must contain the '{target_column.strip()}' target column.")
    return frame.reset_index(drop=True)


def _read_upload(filename: str | None, content: bytes) -> pd.DataFrame:
    """Read and validate a complete supported upload."""
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
    frame.columns = [str(column).strip() for column in frame.columns]
    return frame


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
