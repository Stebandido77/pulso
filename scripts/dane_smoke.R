# Weekly smoke test of pulso (R) against the live DANE portal.
#
# Smoke test semanal: descarga del DANE real un periodo y verifica que los
# modulos se lean bien. Lo usa .github/workflows/dane_smoke.yml.
#
# Checks per (period, module): more than 1000 rows; FEX_C18 (any case) present and
# numeric; no mojibake ("Ã" or U+FFFD) in column names nor in a sample of
# text values. Failures are written literally to the file given in
# --failures (Markdown) so the workflow can paste them into an issue.
#
# Usage:
#   Rscript scripts/dane_smoke.R --period 2024-03 --modules ocupados vivienda_hogares
#   Rscript scripts/dane_smoke.R --period latest

args <- commandArgs(trailingOnly = TRUE)

arg_value <- function(flag, default) {
  i <- match(flag, args)
  if (is.na(i)) return(default)
  rest <- args[-seq_len(i)]
  stop_at <- which(startsWith(rest, "--"))
  if (length(stop_at)) rest <- rest[seq_len(stop_at[1] - 1)]
  if (!length(rest)) default else rest
}

period <- arg_value("--period", "latest")[1]
modules <- arg_value("--modules", c("ocupados", "vivienda_hogares"))
failures_path <- arg_value("--failures", "smoke_failures.md")[1]

suppressPackageStartupMessages(library(pulso))

if (identical(period, "latest")) {
  src <- jsonlite::fromJSON(
    system.file("extdata", "sources.json", package = "pulso"),
    simplifyVector = FALSE
  )
  period <- max(names(src$data))
}
year <- as.integer(substr(period, 1, 4))
month <- as.integer(substr(period, 6, 7))

min_rows <- 1000L
mojibake <- "Ã|�"

check_frame <- function(df) {
  problems <- character()
  if (nrow(df) <= min_rows) {
    problems <- c(problems, sprintf("expected more than %d rows, got %d", min_rows, nrow(df)))
  }
  # pulso_load(harmonize = TRUE) lowercases column names by design, so the
  # weight arrives as `fex_c18`: match the name case-insensitively.
  fex <- names(df)[tolower(names(df)) == "fex_c18"]
  if (!length(fex)) {
    problems <- c(problems, paste0(
      "FEX_C18 column missing; first columns: ",
      paste(utils::head(names(df), 10), collapse = ", ")
    ))
  } else if (!is.numeric(df[[fex[1]]])) {
    problems <- c(problems, sprintf(
      "%s is not numeric (class=%s; first values: %s)", fex[1],
      paste(class(df[[fex[1]]]), collapse = "/"),
      paste(utils::head(df[[fex[1]]], 3), collapse = ", ")
    ))
  }
  bad_cols <- names(df)[grepl(mojibake, names(df))]
  if (length(bad_cols)) {
    problems <- c(problems, paste0("mojibake in column names: ", paste(bad_cols, collapse = ", ")))
  }
  sample <- utils::head(df, 500L)
  for (col in names(sample)) {
    v <- sample[[col]]
    if (!is.character(v) && !is.factor(v)) next
    v <- as.character(v)
    hit <- v[!is.na(v) & grepl(mojibake, v)]
    if (length(hit)) {
      problems <- c(problems, sprintf("mojibake in values of '%s': %s", col, hit[1]))
    }
  }
  problems
}

failures <- character()
for (module in modules) {
  problems <- tryCatch(
    {
      df <- pulso_load(year, month, module)
      check_frame(df)
    },
    error = function(e) paste0(class(e)[1], ": ", conditionMessage(e))
  )
  status <- if (length(problems)) "FAIL" else "OK"
  cat(sprintf("[r] %s %s: %s\n", period, module, status))
  for (p in problems) {
    cat("    ", p, "\n", sep = "")
    failures <- c(failures, sprintf("- **r** `%s` `%s`:\n\n  ```\n  %s\n  ```", period, module, p))
  }
}

if (length(failures)) {
  header <- sprintf(
    "Smoke test (R, pulso %s) failed for %s.\n\n",
    as.character(utils::packageVersion("pulso")), period
  )
  writeLines(c(header, failures), failures_path, useBytes = TRUE)
  quit(status = 1L)
}
