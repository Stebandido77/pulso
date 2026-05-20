# pulso (development version)

* Initial R skeleton. R port under construction.

## Known limitations in v0.1.0

* **Nested-zip layout (DANE 2024-03, 2024-04)**: these two periods ship the
  per-format files inside a second zip wrapper (`CSV.zip`, `DTA.zip`,
  `SAV.zip` as the outer archive contents). `pulso_load()` detects this and
  raises `pulso_parse_error` with a v0.2.0 deferral notice. All other
  periods from 2007 onward work normally.
