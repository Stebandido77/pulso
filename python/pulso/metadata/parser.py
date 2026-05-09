"""DDI 1.2.2 XML parser for DANE GEIH codebooks.

Public surface:

* :class:`DDIParseError` — raised on malformed / wrong-version input.
* :func:`parse_ddi` — parse one ``codeBook`` and return a per-year dict
  matching the shape of one entry in ``dane_codebook.json``.

The parser is deliberately tolerant: it skips optional elements rather
than failing, but it raises on structural problems (wrong root, wrong
namespace, wrong DDI version, missing ``<dataDscr>``).

Encoding note: every file read uses ``encoding="utf-8"`` explicitly to
avoid Windows ``cp1252`` UnicodeDecodeError on tildes/ñ.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from lxml import etree

if TYPE_CHECKING:
    from pulso.metadata.schema import Variable, YearEntry

DDI_NS = "http://www.icpsr.umich.edu/DDI"
NS = {"ddi": DDI_NS}

# Tags inside <var> that we read.
_TAG_LABL = f"{{{DDI_NS}}}labl"
_TAG_VAR_FORMAT = f"{{{DDI_NS}}}varFormat"
_TAG_QSTN = f"{{{DDI_NS}}}qstn"
_TAG_QSTN_LIT = f"{{{DDI_NS}}}qstnLit"
_TAG_UNIVERSE = f"{{{DDI_NS}}}universe"
_TAG_RESP_UNIT = f"{{{DDI_NS}}}respUnit"
_TAG_CATGRY = f"{{{DDI_NS}}}catgry"
_TAG_CAT_VALU = f"{{{DDI_NS}}}catValu"
_TAG_VALRNG = f"{{{DDI_NS}}}valrng"
_TAG_RANGE = f"{{{DDI_NS}}}range"
_TAG_TXT = f"{{{DDI_NS}}}txt"


class DDIParseError(Exception):
    """Raised when the XML cannot be parsed as a DDI 1.2.2 codebook."""


def _text(elem: etree._Element | None) -> str | None:
    """Return ``elem.text.strip()`` or ``None`` if elem/text is empty."""
    if elem is None or elem.text is None:
        return None
    stripped = elem.text.strip()
    return stripped or None


def _epoch_for_year(year: int) -> str:
    """Map an integer year to a pulso epoch key.

    Matches the boundaries declared in ``pulso/data/epochs.json``:
    2007-2020 = ``geih_2006_2020``; 2021+ = ``geih_2021_present``.
    """
    if year >= 2021:
        return "geih_2021_present"
    return "geih_2006_2020"


def _infer_year_from_root(root: etree._Element) -> int | None:
    """Best-effort year extraction from <codeBook ID=…> or <IDNo>.

    Used as a sanity check; the canonical year comes from the caller.
    """
    code_id = root.get("ID") or ""
    # Look for a 4-digit year in the ID slug (e.g. DANE-DIMPE-GEIH-2024).
    for token in code_id.split("-"):
        if token.isdigit() and len(token) == 4:
            return int(token)
    # Fallback: <IDNo> children.
    idnos = root.findall(f".//{{{DDI_NS}}}IDNo")
    for idno in idnos:
        text = _text(idno) or ""
        for token in text.replace("/", "-").split("-"):
            if token.isdigit() and len(token) == 4:
                return int(token)
    return None


def _parse_var(var_elem: etree._Element) -> tuple[str, Variable, YearEntry]:
    """Parse one ``<var>`` element.

    Returns
    -------
    (code, top_record, year_record)
        ``code`` is the DANE variable name (``<var name="…">``); ``top_record``
        and ``year_record`` are the same content under different shapes
        (the top-level Variable mirrors the most-recent-year YearEntry).
    """
    code = var_elem.get("name")
    if not code:
        raise DDIParseError(f"<var> element without 'name' attribute (ID={var_elem.get('ID')!r})")

    label = _text(var_elem.find(_TAG_LABL))
    var_format = var_elem.find(_TAG_VAR_FORMAT)
    fmt_type = var_format.get("type") if var_format is not None else None

    # Categories
    categories: dict[str, str] | None = None
    catgry_elems = var_elem.findall(_TAG_CATGRY)
    if catgry_elems:
        categories = {}
        for cat in catgry_elems:
            value_el = cat.find(_TAG_CAT_VALU)
            label_el = cat.find(_TAG_LABL)
            value = _text(value_el)
            cat_label = _text(label_el)
            if value is None:
                # malformed category — skip but continue
                continue
            categories[value] = cat_label or ""

    # Type inference: presence of categories wins; else use varFormat type.
    var_type: str
    if categories:
        var_type = "categorical"
    elif fmt_type == "numeric":
        var_type = "numeric"
    elif fmt_type == "character":
        var_type = "character"
    else:
        var_type = "unknown"

    # Question text
    qstn = var_elem.find(_TAG_QSTN)
    question_text = _text(qstn.find(_TAG_QSTN_LIT)) if qstn is not None else None

    # Universe / response unit
    universe = _text(var_elem.find(_TAG_UNIVERSE))
    response_unit = _text(var_elem.find(_TAG_RESP_UNIT))

    # Value range
    value_range = None
    valrng = var_elem.find(_TAG_VALRNG)
    if valrng is not None:
        rng = valrng.find(_TAG_RANGE)
        if rng is not None:
            try:
                vmin = float(rng.get("min")) if rng.get("min") is not None else None
                vmax = float(rng.get("max")) if rng.get("max") is not None else None
                if vmin is not None and vmax is not None:
                    value_range = {"min": vmin, "max": vmax}
            except (TypeError, ValueError):
                value_range = None

    # Notes (concatenated <txt>)
    txt_elems = var_elem.findall(_TAG_TXT)
    notes_parts = [t for t in (_text(el) for el in txt_elems) if t]
    notes = "\n\n".join(notes_parts) if notes_parts else None

    # Year-level record (subset of fields per the schema).
    year_record: YearEntry = {  # type: ignore[typeddict-item]
        "epoch": "",  # filled in by caller
        "file_id_in_year": var_elem.get("files"),
        "var_id_in_year": var_elem.get("ID"),
        "label": label,
        "type": var_type,  # type: ignore[typeddict-item]
        "question_text": question_text,
        "categories": categories,
        "value_range": value_range,
    }

    top_record: Variable = {  # type: ignore[typeddict-item]
        "code": code,
        "label": label or code,
        "type": var_type,  # type: ignore[typeddict-item]
        "question_text": question_text,
        "universe": universe,
        "response_unit": response_unit,
        "categories": categories,
        "value_range": value_range,
        "notes": notes,
        "available_in": {},
    }

    return code, top_record, year_record


def _validate_root(root: etree._Element) -> None:
    qname = etree.QName(root.tag)
    if qname.localname != "codeBook":
        raise DDIParseError(f"Expected root element 'codeBook', got {qname.localname!r}")
    if qname.namespace != DDI_NS:
        raise DDIParseError(f"Expected DDI namespace {DDI_NS!r}, got {qname.namespace!r}")
    version = root.get("version")
    if version != "1.2.2":
        raise DDIParseError(f"Expected DDI version '1.2.2', got {version!r}")


def parse_ddi(path: str | Path, *, year: int | None = None) -> dict[str, Any]:
    """Parse a DANE DDI-XML codeBook into a per-year dict.

    Parameters
    ----------
    path
        Filesystem path to a DDI XML file.
    year
        Survey year for the file. If ``None``, the parser tries to infer
        it from ``<codeBook ID="…">``. Used to assign ``epoch`` to each
        variable's year-entry.

    Returns
    -------
    dict
        With keys ``year``, ``ddi_id``, ``file_descriptors``, ``variables``.
        ``variables[code]`` is the per-year Variable record (with
        ``available_in[str(year)]`` already populated).

    Raises
    ------
    DDIParseError
        On malformed XML, wrong root, wrong namespace, or wrong DDI version.
    FileNotFoundError
        If ``path`` does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    try:
        # lxml.etree.parse handles UTF-8 declaration in the XML preamble.
        tree = etree.parse(str(p))
    except etree.XMLSyntaxError as exc:
        raise DDIParseError(f"Malformed XML in {p}: {exc}") from exc

    root = tree.getroot()
    _validate_root(root)

    inferred_year = _infer_year_from_root(root)
    effective_year = year if year is not None else inferred_year
    if effective_year is None:
        raise DDIParseError(
            f"Could not infer survey year from {p}; pass `year=` explicitly to parse_ddi()."
        )
    epoch = _epoch_for_year(effective_year)
    year_str = str(effective_year)

    # File descriptors (informational).
    file_descriptors: dict[str, str] = {}
    for f in root.findall(f".//{{{DDI_NS}}}fileDscr"):
        fid = f.get("ID")
        if not fid:
            continue
        fname_el = f.find(f".//{{{DDI_NS}}}fileName")
        fname = _text(fname_el)
        if fname:
            file_descriptors[fid] = fname

    # Variables.
    data_dscr = root.find(f"{{{DDI_NS}}}dataDscr")
    if data_dscr is None:
        raise DDIParseError(f"No <dataDscr> element in {p}; not a valid GEIH codeBook.")

    variables: dict[str, dict[str, Any]] = {}
    for var_elem in data_dscr.findall(f"{{{DDI_NS}}}var"):
        code, top_record, year_record = _parse_var(var_elem)
        year_record["epoch"] = epoch
        # Single-year shape: the top record carries this year inside available_in.
        top_record["available_in"] = {year_str: year_record}
        if code in variables:
            # DANE repeats the same <var> once per file it appears in. We treat
            # them as the same logical variable: keep the first record but
            # accumulate the file_ids in the year-entry's file_id_in_year.
            existing = variables[code]
            existing_year_entry = existing["available_in"][year_str]
            existing_files = existing_year_entry.get("file_id_in_year") or ""
            new_file = year_record.get("file_id_in_year") or ""
            if new_file and new_file not in existing_files.split(","):
                existing_year_entry["file_id_in_year"] = (
                    f"{existing_files},{new_file}" if existing_files else new_file
                )
            continue
        variables[code] = top_record

    return {
        "year": effective_year,
        "ddi_id": root.get("ID"),
        "file_descriptors": file_descriptors,
        "variables": variables,
    }
