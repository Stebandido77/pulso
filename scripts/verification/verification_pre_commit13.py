"""Pre-Commit-13 verification: which (year, month) input combos does
``pulso.load`` accept TODAY?

We classify each combo by what happens at the validation layer (signature
+ validate_year_month), not by whether the download succeeds. The
parser/downloader are monkey-patched so the test is offline and fast.

Output is printed to stdout AND written to verification_pre_commit13.txt
in the same directory.
"""

from __future__ import annotations

import inspect
import io
import sys
import warnings
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd

import pulso
import pulso._config.registry as reg
import pulso._core.downloader as dl_mod
import pulso._core.parser as parser_mod


def _setup_offline_pipeline() -> None:
    """Patch HTTP, parser, registry so any (year, month) combo with the right
    signature succeeds without touching the network."""
    sources = {
        "metadata": {"schema_version": "1.0.0", "data_version": "2024.06"},
        "modules": {
            "ocupados": {
                "level": "persona",
                "description_es": "Ocu",
                "description_en": "Ocu",
                "available_in": ["geih_2021_present", "geih_2006_2020"],
            }
        },
        "data": {
            f"{y}-{m:02d}": {
                "epoch": "geih_2021_present" if y >= 2022 else "geih_2006_2020",
                "download_url": f"https://example.com/{y}-{m:02d}.zip",
                "checksum_sha256": "a" * 64,
                "modules": {"ocupados": {"cabecera": f"{y}-{m:02d}.CSV"}},
                "validated": True,
            }
            for y in range(2007, 2027)
            for m in range(1, 13)
        },
    }
    reg._SOURCES = sources

    # Stub the downloader so it never opens a socket; just returns a Path
    # the parser will accept.
    fake_zip = (
        Path("/tmp/fake.zip") if sys.platform != "win32" else Path("C:/Windows/Temp/fake.zip")
    )

    def fake_download_zip(*_a, **_kw):
        return fake_zip

    dl_mod.download_zip = fake_download_zip  # type: ignore[assignment]

    sentinel = pd.DataFrame({"DIRECTORIO": ["1"], "SECUENCIA_P": ["1"], "ORDEN": ["1"]})
    parser_mod.parse_module = lambda *_a, **_kw: sentinel.copy()  # type: ignore[assignment]


def _run_matrix() -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        print("=== Signature actual de pulso.load ===")
        sig = inspect.signature(pulso.load)
        print(sig)
        print(f"  type hint de month: {sig.parameters['month'].annotation}")
        print(f"  type hint de year:  {sig.parameters['year'].annotation}")

        print()
        print("=== Smoke tests de qué soporta (offline, sin red) ===")

        cases = [
            (
                "year=int, month=int",
                lambda: pulso.load(year=2024, month=6, module="ocupados", strict=False),
            ),
            (
                "year=range, month=int",
                lambda: pulso.load(
                    year=range(2023, 2025), month=6, module="ocupados", strict=False
                ),
            ),
            (
                "year=int, month=range",
                lambda: pulso.load(year=2024, month=range(1, 4), module="ocupados", strict=False),
            ),
            (
                "year=range, month=range",
                lambda: pulso.load(
                    year=range(2023, 2025),
                    month=range(1, 4),
                    module="ocupados",
                    strict=False,
                ),
            ),
            (
                "year=int, month=list",
                lambda: pulso.load(year=2024, month=[1, 6, 12], module="ocupados", strict=False),
            ),
            (
                "year=list, month=list",
                lambda: pulso.load(
                    year=[2023, 2024], month=[6, 12], module="ocupados", strict=False
                ),
            ),
            (
                "year=int, month=tuple",
                lambda: pulso.load(year=2024, month=(1, 6, 12), module="ocupados", strict=False),
            ),
        ]

        for name, fn in cases:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    df = fn()
                print(f"  {name:40s} -> SOPORTADO (shape={df.shape})")
            except TypeError as e:
                print(f"  {name:40s} -> NO SOPORTADO (TypeError): {e}")
            except Exception as e:
                print(
                    f"  {name:40s} -> SIGNATURE OK pero error en runtime: {type(e).__name__}: {e}"
                )

    return buf.getvalue()


if __name__ == "__main__":
    _setup_offline_pipeline()
    output = _run_matrix()
    print(output)
    Path(__file__).with_name("verification_pre_commit13.txt").write_text(output, encoding="utf-8")
    print("\n(Saved to verification_pre_commit13.txt)")
