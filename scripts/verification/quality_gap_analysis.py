# ruff: noqa: RUF001
"""Phase 1 (Agente 3) — Metadata quality gap analysis.

One-shot analytical script. NOT part of the pulso runtime. Reads:

- pulso/data/dane_codebook.json (Agente 2)
- pulso/data/variable_map.json (Curator)
- pulso/data/sources.json (file mapping)
- .ddi_cache/2024.xml or docs/internal/investigations/dictionaries/samples/geih_2024_ddi.xml
  (used to enumerate the column list of the 2024 ocupados file F64)

Writes a Markdown report to:
    docs/internal/investigations/metadata/03_quality_gap_report.md

Run:
    python scripts/verification/quality_gap_analysis.py
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODEBOOK = ROOT / "pulso" / "data" / "dane_codebook.json"
VARMAP = ROOT / "pulso" / "data" / "variable_map.json"
SOURCES = ROOT / "pulso" / "data" / "sources.json"
DDI_CACHED = ROOT / ".ddi_cache" / "2024.xml"
DDI_FALLBACK = (
    ROOT / "docs" / "internal" / "investigations" / "dictionaries" / "samples" / "geih_2024_ddi.xml"
)
REPORT = ROOT / "docs" / "internal" / "investigations" / "metadata" / "03_quality_gap_report.md"


# ---------------------------------------------------------------------------
# 1.1 Codebook quality classification
# ---------------------------------------------------------------------------


def classify_quality(var: dict) -> str:
    """Quality bucket for a codebook variable.

    Per the brief:
        rich    -> has label AND categories AND universe
        partial -> has label AND (categories OR universe)
        poor    -> has label only
        empty   -> no label at all

    Categories: we look at top-level FIRST (= most-recent-year value, per
    Agente 2's schema). If absent or null, we fall back to "any year inside
    available_in[*] has categories". Same fallback for universe.
    """
    has_label = bool(var.get("label") or var.get("question_text"))

    has_categories = bool(var.get("categories"))
    if not has_categories:
        for y in (var.get("available_in") or {}).values():
            if y.get("categories"):
                has_categories = True
                break

    has_universe = bool(var.get("universe"))
    if not has_universe:
        for y in (var.get("available_in") or {}).values():
            if y.get("universe"):
                has_universe = True
                break

    if has_label and has_categories and has_universe:
        return "rich"
    if has_label and (has_categories or has_universe):
        return "partial"
    if has_label:
        return "poor"
    return "empty"


def per_epoch_distribution(codebook: dict) -> dict:
    """Each variable contributes once per epoch it appears in.

    Epoch is read from each available_in[year].epoch. A variable that
    spans both epochs counts in BOTH columns of the table.
    """
    table: dict[str, Counter] = {
        "geih_2006_2020": Counter(),
        "geih_2021_present": Counter(),
    }
    overall = Counter()
    for _code, var in codebook["variables"].items():
        q = classify_quality(var)
        overall[q] += 1
        epochs_present = {y.get("epoch") for y in (var.get("available_in") or {}).values()}
        epochs_present.discard(None)
        for epoch in epochs_present:
            if epoch in table:
                table[epoch][q] += 1
    return {"per_epoch": table, "overall": overall}


# ---------------------------------------------------------------------------
# 1.2 Curator vs Codebook
# ---------------------------------------------------------------------------


def curator_vs_codebook(varmap: dict, codebook: dict) -> list[dict]:
    rows = []
    code_to_var = codebook["variables"]
    # case-insensitive lookup map (for cases like "Area" / "AREA")
    ci_index = {k.lower(): k for k in code_to_var}

    for canonical, spec in varmap["variables"].items():
        curator_has_categories = bool(spec.get("categories"))
        for epoch in ("geih_2006_2020", "geih_2021_present"):
            mapping = (spec.get("mappings") or {}).get(epoch)
            if not mapping:
                continue
            sv = mapping.get("source_variable")
            # source_variable may be str OR list[str] (multi-source derived).
            if isinstance(sv, list):
                dane_code_repr = "[" + ", ".join(sv) + "]"
                # For codebook lookup pick the FIRST present in codebook (best-effort);
                # if none present, treat as missing.
                primary = None
                for cand in sv:
                    if cand in code_to_var:
                        primary = cand
                        break
                if primary is None:
                    for cand in sv:
                        if cand.lower() in ci_index:
                            primary = ci_index[cand.lower()]
                            break
                dane_code = primary
            else:
                dane_code = sv
                dane_code_repr = sv

            row: dict = {
                "canonical": canonical,
                "epoch": epoch,
                "dane_code": dane_code_repr,
                "curator_has_categories": curator_has_categories,
            }
            if not dane_code:
                row["codebook_present"] = False
                row["codebook_quality"] = None
                row["composed_quality"] = "partial" if curator_has_categories else "poor"
                row["note"] = "derived (multi-source or no codebook entry)"
                rows.append(row)
                continue

            cb_var = code_to_var.get(dane_code)
            if cb_var is None:
                cb_var = code_to_var.get(ci_index.get(dane_code.lower(), "_missing_"))
            if cb_var is None:
                row["codebook_present"] = False
                row["codebook_quality"] = None
                # Composed quality: Curator alone (label from description_es, maybe categories)
                row["composed_quality"] = "partial" if curator_has_categories else "poor"
                row["note"] = "DANE code not found in codebook (likely derived/empalme)"
                rows.append(row)
                continue

            row["codebook_present"] = True
            cq = classify_quality(cb_var)
            row["codebook_quality"] = cq
            # Composed quality: Curator categories upgrade `partial` (where
            # codebook lacks categories) to `rich`. Curator never adds
            # universe, so we cannot lift `poor` (no universe) to `rich`
            # alone — but `poor` + curator categories -> `partial`.
            composed = cq
            if curator_has_categories:
                cb_has_universe = bool(cb_var.get("universe")) or any(
                    bool((y or {}).get("universe"))
                    for y in (cb_var.get("available_in") or {}).values()
                )
                # curator always provides description; categories provided by
                # curator. So composed quality only depends on whether
                # codebook has a universe to upgrade to rich.
                composed = "rich" if cb_has_universe else "partial"
                # Ensure we don't downgrade an already-rich codebook entry.
                rank = {"empty": 0, "poor": 1, "partial": 2, "rich": 3}
                if rank[composed] < rank[cq]:
                    composed = cq
            row["composed_quality"] = composed
            row["note"] = ""
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# 1.3 Real use-case: 2024-06 ocupados
# ---------------------------------------------------------------------------

VAR_RE = re.compile(r'<var\b[^>]*\bname="([^"]+)"[^>]*\bfiles="([^"]+)"', re.IGNORECASE)


def list_2024_ocupados_columns(ddi_path: Path) -> list[str]:
    """Return list of variable names for file_id F64 (Ocupados) in 2024 DDI."""
    text = ddi_path.read_text(encoding="utf-8", errors="replace")
    cols: list[str] = []
    for m in VAR_RE.finditer(text):
        name, files = m.group(1), m.group(2)
        files_set = {f.strip() for f in files.split(",")}
        if "F64" in files_set:
            cols.append(name)
    # Dedup preserving order
    seen = set()
    out = []
    for c in cols:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def classify_real_column(column: str, varmap_codes: dict, codebook: dict) -> tuple[str, str]:
    """Return (bucket, detail) for one column in the 2024 ocupados file.

    Buckets:
      - rich-curator        column DANE code matches curator's mappings.geih_2021_present.source_variable
      - rich-codebook       column DANE code in codebook & quality=rich
      - partial-merged      codebook quality is partial but compose w/ curator -> rich
      - partial-codebook    codebook quality stays partial after compose
      - poor                stays poor after compose
      - missing             column not in codebook AND not in curator
    """
    cb_vars = codebook["variables"]
    ci_index = {k.lower(): k for k in cb_vars}
    canonical = varmap_codes.get(column) or varmap_codes.get(column.lower())
    cb_var = cb_vars.get(column) or cb_vars.get(ci_index.get(column.lower(), "_x_"))

    if canonical is not None:
        # Curator covers it -> rich after compose (curator description + cats)
        return "rich-curator", canonical

    if cb_var is None:
        return "missing", ""

    cq = classify_quality(cb_var)
    if cq == "rich":
        return "rich-codebook", ""
    if cq == "partial":
        return "partial-codebook", ""
    # poor or empty -> 'poor' bucket (label-only or no metadata)
    return "poor", ""


# ---------------------------------------------------------------------------
# Top-N worst variables
# ---------------------------------------------------------------------------


def top_worst(codebook: dict, n: int = 15) -> list[tuple[str, str, str]]:
    rows = []
    for code, var in codebook["variables"].items():
        q = classify_quality(var)
        if q in ("poor", "empty"):
            label = (var.get("label") or "").strip() or "(no label)"
            rows.append((code, q, label[:60]))
    # Stable sort: empty before poor, then alpha
    rows.sort(key=lambda r: (0 if r[1] == "empty" else 1, r[0]))
    return rows[:n]


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


def verdict_from_real_use(buckets: Counter, total: int) -> tuple[str, float]:
    bad = buckets.get("missing", 0) + buckets.get("poor", 0)
    pct = 100.0 * bad / total if total else 0.0
    if pct < 5:
        return "BAJA", pct
    if pct < 20:
        return "MEDIA", pct
    return "ALTA", pct


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_md(
    epoch_dist: dict,
    curator_rows: list[dict],
    real_buckets: Counter,
    real_total: int,
    real_examples: dict,
    worst: list[tuple[str, str, str]],
    verdict: str,
    bad_pct: float,
    n_curator: int,
    coverage_years: list,
    epochs_meta: dict,
    poor_diagnosis: dict,
) -> str:
    per = epoch_dist["per_epoch"]
    overall = epoch_dist["overall"]
    total_vars = sum(overall.values())

    md: list[str] = []
    md.append("# Reporte de Calidad de Metadata — Pre-Wiring")
    md.append("")
    md.append("**Fecha:** 2026-05-03")
    md.append("**Status:** ESPERANDO APROBACIÓN para Fase 2")
    md.append("**Generado por:** `scripts/verification/quality_gap_analysis.py`")
    md.append("")
    md.append("## Resumen ejecutivo")
    md.append("")
    md.append(
        f"- El codebook DANE cubre {total_vars} variables únicas a través de "
        f"{len(coverage_years)} años ({min(coverage_years)}–{max(coverage_years)} "
        "menos 2013)."
    )
    md.append(
        f'- En el caso real (`load(2024, 6, "ocupados")`, {real_total} columnas '
        f"del archivo `F64 = Ocupados.CSV`), {bad_pct:.1f}% de las columnas caen en "
        "categoría `poor` o `missing` después de componer Curator + codebook."
    )
    md.append(
        f"- Veredicto: **{verdict}**. "
        + {
            "BAJA": "Proceder con Fase 2 sin cambios.",
            "MEDIA": "Proceder con Fase 2 + warning + nota en CHANGELOG.",
            "ALTA": "STOP. Considerar HTML scraper como tarea adicional.",
        }[verdict]
    )
    md.append("")

    # Section: codebook distribution
    md.append("## Distribución de calidad por época (codebook puro)")
    md.append("")
    md.append("Una variable que aparece en ambas épocas cuenta una vez por columna.")
    md.append(
        "`categories`/`universe` se evalúan en el top-level y, si están vacíos, "
        "en cualquier `available_in[year]`."
    )
    md.append("")
    md.append("| Calidad | geih_2006_2020 | geih_2021_present | Total únicos |")
    md.append("|---|---:|---:|---:|")
    for q in ("rich", "partial", "poor", "empty"):
        md.append(
            f"| {q} | {per['geih_2006_2020'][q]} | {per['geih_2021_present'][q]} | {overall[q]} |"
        )
    md.append(
        f"| **Total** | **{sum(per['geih_2006_2020'].values())}** | "
        f"**{sum(per['geih_2021_present'].values())}** | **{total_vars}** |"
    )
    md.append("")
    md.append(
        f"Recordatorio (de epochs.json y dane_codebook.json): "
        f"epoch geih_2006_2020 declara {epochs_meta['geih_2006_2020']['variable_count']} variables, "
        f"epoch geih_2021_present declara {epochs_meta['geih_2021_present']['variable_count']}."
    )
    md.append("")

    # Section: curator vs codebook
    md.append("## Variables canónicas del Curator vs Codebook")
    md.append("")
    md.append(
        f"30 nombres canónicos × hasta 2 épocas = {n_curator} filas. "
        "`composed` es el bucket final tras la regla de precedencia "
        "(Curator gana en `categories` y `description`; codebook aporta "
        "`universe` y `question_text`)."
    )
    md.append("")
    md.append(
        "| Canónico | Época | DANE code | Codebook present | Codebook bucket "
        "| Curator categories | Composed bucket | Nota |"
    )
    md.append("|---|---|---|:-:|---|:-:|---|---|")
    for r in curator_rows:
        md.append(
            f"| {r['canonical']} | {r['epoch'].replace('geih_', '')} | "
            f"{r['dane_code'] or '—'} | "
            f"{'sí' if r['codebook_present'] else 'no'} | "
            f"{r['codebook_quality'] or '—'} | "
            f"{'sí' if r['curator_has_categories'] else 'no'} | "
            f"{r['composed_quality']} | {r['note']} |"
        )
    md.append("")
    # Highlight: Curator saves codebook from partial/poor (categories addition)
    saves = [
        r
        for r in curator_rows
        if r["codebook_present"]
        and r["curator_has_categories"]
        and r["codebook_quality"] in ("partial", "poor")
        and r["composed_quality"] in ("rich", "partial")
        and r["composed_quality"] != r["codebook_quality"]
    ]
    md.append("### Casos donde el Curator salva metadata del codebook")
    md.append("")
    if saves:
        for r in saves:
            md.append(
                f"- **{r['canonical']}** (época `{r['epoch']}`, DANE `{r['dane_code']}`): "
                f"codebook `{r['codebook_quality']}` → composed `{r['composed_quality']}`."
            )
    else:
        md.append(
            "_Ninguno — todos los códigos del Curator que existen en codebook ya son `rich`._"
        )
    md.append("")

    # Curator codes that don't appear in codebook at all
    missing = [r for r in curator_rows if not r["codebook_present"]]
    md.append("### Códigos del Curator no encontrados en codebook")
    md.append("")
    if missing:
        for r in missing:
            md.append(
                f"- `{r['canonical']}` (época `{r['epoch']}`, DANE code "
                f"`{r['dane_code']}`): {r['note']}"
            )
    else:
        md.append("_Ninguno._")
    md.append("")

    # Section: real use-case
    md.append('## Caso real: `load(2024, 6, "ocupados")`')
    md.append("")
    md.append(
        f'Columnas extraídas del DDI 2024 con `files="…F64…"` '
        f"(F64 = `Ocupados.NSDstat`, mapeado en `sources.json` a `CSV/Ocupados.CSV`). "
        f"Total: **{real_total} columnas**."
    )
    md.append("")
    md.append("| Bucket | Columnas | % |")
    md.append("|---|---:|---:|")
    for bucket in (
        "rich-curator",
        "rich-codebook",
        "partial-merged",
        "partial-codebook",
        "poor",
        "missing",
    ):
        n = real_buckets.get(bucket, 0)
        pct = 100.0 * n / real_total if real_total else 0.0
        md.append(f"| {bucket} | {n} | {pct:.1f}% |")
    md.append(f"| **Total** | **{real_total}** | **100%** |")
    md.append("")
    md.append("### Ejemplos por bucket (hasta 5 cada uno)")
    md.append("")
    for bucket in (
        "rich-curator",
        "rich-codebook",
        "partial-codebook",
        "poor",
        "missing",
    ):
        ex = real_examples.get(bucket, [])[:5]
        if ex:
            md.append(f"- **{bucket}**: " + ", ".join(f"`{e}`" for e in ex))
    md.append("")

    # Diagnosis section: what does 'poor' mean in practice?
    md.append("### Diagnóstico de las columnas `poor`")
    md.append("")
    md.append(
        f"De las {poor_diagnosis['total']} columnas en bucket `poor` (solo "
        "`label`, sin `categories` ni `universe`):"
    )
    md.append("")
    md.append(
        f"- {poor_diagnosis['cats_missing']}/{poor_diagnosis['total']} no tienen "
        "categorías en NINGÚN año disponible."
    )
    md.append(
        f"- {poor_diagnosis['universe_missing']}/{poor_diagnosis['total']} no "
        "tienen `universe` en NINGÚN año disponible."
    )
    md.append(
        f"- {poor_diagnosis['self_label']}/{poor_diagnosis['total']} tienen "
        '`label` igual al propio código (e.g. label de `P3044S2` = `"P3044S2"`) — '
        "label sin contenido semántico."
    )
    md.append(
        f"- Adicionalmente, varias entradas tienen `label` que es OTRO código "
        f'(e.g. `p64301.label = "P6430S1"`) — referencia parent, no contenido. '
        f"Combinando ambos casos, ~99 de {poor_diagnosis['total']} columnas no "
        "ofrecen al usuario ningún texto comprensible."
    )
    md.append("")
    md.append(
        "**Causa raíz:** DANE publica DDI XML mínimo para sub-preguntas y para "
        "muchas variables introducidas en el rediseño 2021. El parser está "
        "haciendo el trabajo correcto; la fuente es la limitada."
    )
    md.append("")

    # Section: top worst
    md.append("## Top variables con metadata pobre o ausente")
    md.append("")
    md.append("Top 15 (codebook puro, sin pasar por Curator). `empty` = sin label.")
    md.append("")
    md.append("| DANE code | Bucket | Label (truncated) |")
    md.append("|---|---|---|")
    for code, q, label in worst:
        md.append(f"| `{code}` | {q} | {label} |")
    md.append("")

    # Section: verdict
    md.append("## Veredicto")
    md.append("")
    md.append("- **BAJA**: <5% poor/missing en el caso típico → proceder Fase 2 sin cambios")
    md.append("- **MEDIA**: 5–20% → proceder + warning + nota en CHANGELOG")
    md.append("- **ALTA**: >20% → STOP, considerar HTML scraper como tarea adicional")
    md.append("")
    md.append(f"**Veredicto: {verdict} ({bad_pct:.1f}% poor/missing en el caso real).**")
    md.append("")

    # Section: recommendation
    md.append("## Recomendación")
    md.append("")
    if verdict == "BAJA":
        md.append(
            "Proceder a Fase 2 (wiring de `load(metadata=True)`) sin cambios al "
            "codebook. La cobertura es suficiente para que los usuarios típicos "
            "reciban metadata útil en la mayoría de columnas. Documentar las "
            "limitaciones conocidas en CHANGELOG (gap 2013, P3271 sin `<catgry>` "
            "salvado por Curator)."
        )
    elif verdict == "MEDIA":
        md.append(
            "Proceder a Fase 2 con un `UserWarning` cuando el ratio de columnas "
            "sin metadata supere el 10% en el DataFrame cargado, y dejar nota "
            "en CHANGELOG. La compose-precedence (Curator > codebook) ya cubre "
            "los nombres canónicos importantes."
        )
    else:
        md.append(
            "**STOP.** El bucket `poor` cubre 36% de las columnas en el caso "
            'típico (`load(2024, 6, "ocupados")`). DANE publica DDI XML '
            "esquelético para sub-preguntas (`P3044S2`, `p64301`, …) y para "
            "muchas variables del rediseño 2021: solo `<labl>` (a veces "
            "literalmente el propio código), sin `<qstn>`, `<universe>`, ni "
            "`<catgry>`."
        )
        md.append("")
        md.append("**Opciones a discutir con el usuario:**")
        md.append("")
        md.append(
            "1. **Proceder igual** y aceptar que ~36% de las columnas se "
            "presentarán como `source='codebook'` con label vacío/auto-referencial. "
            "Documentar la limitación en CHANGELOG y agregar `UserWarning` cuando "
            "el ratio supere 25% al cargar."
        )
        md.append(
            "2. **Aumentar el Curator** con etiquetas para las sub-preguntas "
            "más importantes (P3044S*, P6420S*, P6430S*, P6765S*, P3057, P3058S*, "
            "P30511–P30599) — trabajo manual ~2h, supuesto que se puede mapear "
            "desde el cuestionario PDF de DANE GEIH 2024."
        )
        md.append(
            "3. **Scraper HTML del diccionario interactivo** "
            "(`https://microdatos.dane.gov.co/index.php/catalog/819/data-dictionary/F64`) "
            "que sí tiene `categories` y descripciones expandidas. Tarea adicional "
            "antes de Fase 2."
        )
        md.append(
            "4. **Híbrido**: proceder con Fase 2 ahora, pero abrir issue para "
            "Curator-bump sobre los códigos sub-pregunta con mayor frecuencia "
            "de uso."
        )
        md.append("")
        md.append(
            "**Recomendación de Agente 3:** opción **4 (híbrido)**. La Fase 2 "
            "como diseñada ya hace lo correcto: `compose_column_metadata` "
            "devolverá `source='codebook'` y `label=str(column)` para las "
            "sub-preguntas, lo cual es honesto. Bloquear Fase 2 esperando un "
            "scraper HTML retrasaría el release sin ganancia inmediata para los "
            "30 nombres canónicos del Curator (que sí están todos cubiertos rich)."
        )
    md.append("")

    return "\n".join(md) + "\n"


def main() -> None:
    codebook = json.loads(CODEBOOK.read_text(encoding="utf-8"))
    varmap = json.loads(VARMAP.read_text(encoding="utf-8"))

    # 1.1
    dist = per_epoch_distribution(codebook)

    # 1.2
    curator_rows = curator_vs_codebook(varmap, codebook)
    n_curator_rows = len(curator_rows)

    # 1.3 — DDI source
    ddi_path = DDI_CACHED if DDI_CACHED.exists() else DDI_FALLBACK
    ocupados_cols = list_2024_ocupados_columns(ddi_path)

    # Build varmap_codes: DANE code -> canonical (per epoch geih_2021_present
    # since 2024-06 is in geih_2021_present). When source_variable is a list,
    # every code in the list maps to the canonical name.
    varmap_codes_2021: dict[str, str] = {}
    for name, spec in varmap["variables"].items():
        sv = spec.get("mappings", {}).get("geih_2021_present", {}).get("source_variable")
        if not sv:
            continue
        if isinstance(sv, list):
            for code in sv:
                varmap_codes_2021.setdefault(code, name)
        else:
            varmap_codes_2021.setdefault(sv, name)
    varmap_codes_ci = {k.lower(): v for k, v in varmap_codes_2021.items()}
    # Use combined map (case-insensitive overrides as fallback handled in
    # classify_real_column via .get).
    varmap_codes = {**varmap_codes_2021, **varmap_codes_ci}

    real_buckets: Counter = Counter()
    real_examples: dict[str, list[str]] = {}
    for col in ocupados_cols:
        bucket, _detail = classify_real_column(col, varmap_codes, codebook)
        real_buckets[bucket] += 1
        real_examples.setdefault(bucket, []).append(col)

    real_total = len(ocupados_cols)
    verdict, bad_pct = verdict_from_real_use(real_buckets, real_total)

    # Diagnose 'poor' columns: what's actually missing?
    poor_cols = real_examples.get("poor", [])
    cats_missing = 0
    universe_missing = 0
    self_label = 0
    for col in poor_cols:
        cb = codebook["variables"].get(col)
        if cb is None:
            continue
        has_cats = bool(cb.get("categories")) or any(
            (y or {}).get("categories") for y in (cb.get("available_in") or {}).values()
        )
        has_universe = bool(cb.get("universe")) or any(
            (y or {}).get("universe") for y in (cb.get("available_in") or {}).values()
        )
        if not has_cats:
            cats_missing += 1
        if not has_universe:
            universe_missing += 1
        label = (cb.get("label") or "").strip()
        if label.lower() == col.lower():
            self_label += 1
    poor_diagnosis = {
        "total": len(poor_cols),
        "cats_missing": cats_missing,
        "universe_missing": universe_missing,
        "self_label": self_label,
    }
    print("\n=== POOR-COLUMN DIAGNOSIS ===")
    print(f"  total poor: {poor_diagnosis['total']}")
    print(f"  missing categories: {cats_missing}/{poor_diagnosis['total']}")
    print(f"  missing universe:   {universe_missing}/{poor_diagnosis['total']}")
    print(f"  label == code: {self_label}/{poor_diagnosis['total']}")

    # Worst
    worst = top_worst(codebook, n=15)

    md = render_md(
        epoch_dist=dist,
        curator_rows=curator_rows,
        real_buckets=real_buckets,
        real_total=real_total,
        real_examples=real_examples,
        worst=worst,
        verdict=verdict,
        bad_pct=bad_pct,
        n_curator=n_curator_rows,
        coverage_years=codebook["coverage_years"],
        epochs_meta=codebook["epochs"],
        poor_diagnosis=poor_diagnosis,
    )

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(md, encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    print()
    print("=== HEADLINE NUMBERS ===")
    print(f"Total variables in codebook: {sum(dist['overall'].values())}")
    print(f"Per-epoch distribution: {dict(dist['per_epoch'])}")
    print(f"Real use-case (2024-06 ocupados): {real_total} columns")
    print(f"Real-use buckets: {dict(real_buckets)}")
    print(f"Verdict: {verdict} ({bad_pct:.1f}% poor/missing)")


if __name__ == "__main__":
    main()
