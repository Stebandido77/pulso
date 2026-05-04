"""Regression guard: importing the metadata runtime must not pull in lxml.

``lxml`` is in the ``[scraper]`` optional extra. The composer and the
public ``describe_column``/``list_columns_metadata`` helpers run on pure
stdlib + pandas, so a fresh runtime install (without ``[scraper]``)
should keep working.
"""

from __future__ import annotations

import importlib
import sys


def test_metadata_runtime_does_not_import_lxml() -> None:
    """Importing pulso.metadata.composer / .api must not load :mod:`lxml`.

    We can't fully guarantee no other module loaded lxml earlier in the
    test session, so we test by clearing the modules we care about and
    re-importing fresh.
    """
    # Drop any cached metadata modules so the import below truly runs.
    for mod_name in list(sys.modules):
        if mod_name.startswith("pulso.metadata"):
            del sys.modules[mod_name]
    # Snapshot lxml state.
    had_lxml = "lxml" in sys.modules

    # Re-import the runtime entry points.
    importlib.import_module("pulso.metadata.composer")
    importlib.import_module("pulso.metadata.api")

    # If lxml was NOT loaded before, it must still not be loaded.
    if not had_lxml:
        assert "lxml" not in sys.modules, (
            "lxml was pulled in by pulso.metadata.composer/api — it must "
            "stay confined to the [scraper] extra."
        )
