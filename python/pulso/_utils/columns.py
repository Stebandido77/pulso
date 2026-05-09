"""Shared column-normalization utilities for DANE GEIH data."""

from __future__ import annotations

import re
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

_FEX_C_PATTERN: re.Pattern[str] = re.compile(r"^FEX_C(?:_\d{4})?$")


def _normalize_dane_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Uppercase all column names and normalize FEX_C year-variants to canonical FEX_C.

    DANE GEIH CSVs deliver mixed-case columns for some years/shapes (e.g. 'Hogar',
    'Area', 'Fex_c_2011').  The merger and harmonizer expect uppercase names; the
    weight column must be FEX_C so the rest of the pipeline treats it consistently.

    Step 1: uppercase all columns.
    Step 2: rename FEX_C_XXXX → FEX_C (covers FEX_C_2011, FEX_C_2018, …).
    If >1 FEX_C-pattern column is found (unexpected), warn and keep the first.
    """
    import logging

    logger = logging.getLogger(__name__)

    df = df.copy()
    df.columns = df.columns.str.upper()

    # Detect columns that collided after uppercasing (e.g. 'Clase' + 'CLASE').
    if df.columns.duplicated().any():
        dupes = [c for c in df.columns if (df.columns == c).sum() > 1]
        warnings.warn(
            f"Columns {dupes} collide post-uppercase. Keeping first occurrence.",
            UserWarning,
            stacklevel=3,
        )
        df = df.loc[:, ~df.columns.duplicated()]

    fex_matches = [c for c in df.columns if _FEX_C_PATTERN.match(c)]

    if len(fex_matches) > 1:
        warnings.warn(
            f"Multiple FEX_C-pattern columns found: {fex_matches}. "
            f"Keeping {fex_matches[0]!r} as 'FEX_C'; dropping the rest.",
            UserWarning,
            stacklevel=3,
        )
        df = df.drop(columns=fex_matches[1:])
        if fex_matches[0] != "FEX_C":
            df = df.rename(columns={fex_matches[0]: "FEX_C"})
            logger.debug("Normalized %r → 'FEX_C' (multi-match path)", fex_matches[0])
    elif len(fex_matches) == 1 and fex_matches[0] != "FEX_C":
        df = df.rename(columns={fex_matches[0]: "FEX_C"})
        logger.debug("Normalized column %r → 'FEX_C'", fex_matches[0])

    return df
