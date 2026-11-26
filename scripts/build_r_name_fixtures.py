"""Build tiny DANE-like zip fixtures for pulso R tests (filename encoding quirks)."""
import io, sys, zipfile
out = sys.argv[1]
hdr = "PERIODO;MES;DIRECTORIO;SECUENCIA_P;ORDEN;HOGAR;FEX_C18;P6430;NOMBRE\n"
rows = "202608;8;1;1;1;1;100,5;1;Bogot\xe1\n202608;8;1;1;2;1;90,25;2;Medell\xedn\n"
data = (hdr + rows).encode("latin-1")
SSE = "seguridad social en salud y educaci"

def write(path, entries, cp437=()):
    buf = io.BytesIO()
    placeholders = {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in entries:
            if name in cp437:
                raw = name.encode("cp437")
                ph = "".join(c if ord(c) < 128 else "X" for c in name)
                placeholders[ph.encode("ascii")] = raw
                z.writestr(ph, data)
            else:
                z.writestr(name, data)
    b = buf.getvalue()
    for ph, raw in placeholders.items():
        assert len(ph) == len(raw)
        b = b.replace(ph, raw)
    open(path, "wb").write(b)

cg_cp437 = f"CSV/Características generales, {SSE}ón.CSV"
write(f"{out}/dane_mixed_names.zip", [
    cg_cp437,
    "CSV/Datos del hogar y la vivienda.CSV",
    "CSV/Migración.CSV",
    "CSV/No ocupados.CSV",
    "CSV/Ocupados.CSV",
    "CSV/Otras formas de trabajo.CSV",
    "CSV/Otros ingresos e impuestos.CSV",
], cp437={cg_cp437})

write(f"{out}/dane_renamed.zip", [
    f"CSV/Capítulos de características generales, {SSE}ón.csv",
    "CSV/Ocupados.csv",
    "CSV/No ocupados.csv",
])

inner = io.BytesIO()
with zipfile.ZipFile(inner, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("Ocupados.CSV", data)
    z.writestr("No ocupados.CSV", data)
with zipfile.ZipFile(f"{out}/dane_nested.zip", "w") as z:
    z.writestr("CSV.zip", inner.getvalue())
    z.writestr("DTA.zip", b"placeholder")

# Real 2018-frame layout (2026-09): ';' separator with POINT decimals, DTA/
# listed before CSV/, NBSP in names (pulso #77, #78).
point = (
    "PERIODO;MES;DIRECTORIO;SECUENCIA_P;ORDEN;HOGAR;DPTO;FEX_C18\n"
    "20260939;09;8713327;1;1;1;08;43.55418099\n"
    "20260939;09;8713328;1;1;1;08;34.68595437\n"
).encode("latin-1")
with zipfile.ZipFile(f"{out}/dane_point_decimal.zip", "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("DTA/Datos del hogar y la\u00a0vivienda.dta", b"\x75\x00binary-not-csv;;\n1;2;3\n")
    z.writestr("CSV/Datos del hogar y la\u00a0vivienda.csv", point)
    z.writestr("CSV/Ocupados.csv", point)
