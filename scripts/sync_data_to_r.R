#!/usr/bin/env Rscript
# scripts/sync_data_to_r.R
#
# Sync canonical data files from data/ (monorepo root) to r/inst/extdata/
# so the R package bundles them when installed.
#
# Used by .github/workflows/r-ci.yml before R CMD check.
# Can also be run manually during development:
#   Rscript scripts/sync_data_to_r.R
#
# CRAN compliance:
# - 4 small JSONs (~135 KB total) bundled into the package
# - dane_codebook.json (6.7 MB) explicitly EXCLUDED (lazy-downloaded at runtime)

if (!requireNamespace("fs", quietly = TRUE)) {
  stop("Package 'fs' is required. Install with: install.packages('fs')")
}

# Files to sync (CRAN-bundleable, total ~135 KB)
sync_files <- c(
  "sources.json",
  "variable_map.json",
  "variable_module_map.json",
  "epochs.json",
  "codebook_release.json"
)

# Files explicitly NOT synced (exceed CRAN 5 MB package size limit)
excluded <- c("dane_codebook.json")

source_dir <- "data"
target_dir <- "r/inst/extdata"

# Validate paths
if (!fs::dir_exists(source_dir)) {
  stop(sprintf("Source directory missing: %s (run from monorepo root)",
               source_dir))
}

# Ensure target exists
fs::dir_create(target_dir, recurse = TRUE)

# Sync each file
synced <- character(0)
missing <- character(0)

for (f in sync_files) {
  src <- fs::path(source_dir, f)
  dst <- fs::path(target_dir, f)

  if (!fs::file_exists(src)) {
    missing <- c(missing, f)
    next
  }

  fs::file_copy(src, dst, overwrite = TRUE)
  synced <- c(synced, f)
  cat(sprintf("Copied: %s -> %s\n", src, dst))
}

# Warn on missing source files (not fatal, may be expected during dev)
if (length(missing) > 0) {
  warning(sprintf("Source files missing (skipped): %s",
                  paste(missing, collapse = ", ")))
}

# Verify excluded files are NOT in target
for (f in excluded) {
  dst <- fs::path(target_dir, f)
  if (fs::file_exists(dst)) {
    stop(sprintf(
      "Excluded file present in r/inst/extdata/: %s (must NOT be bundled to comply with CRAN size limit)",
      f
    ))
  }
}

cat(sprintf("\nSync complete. %d files copied to %s.\n",
            length(synced), target_dir))
cat(sprintf("Excluded (lazy-downloaded at runtime): %s\n",
            paste(excluded, collapse = ", ")))
