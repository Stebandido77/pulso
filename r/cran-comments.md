## Update

This is an update from pulso 0.1.1 to 0.2.1.

* Extends the bundled catalog of 'DANE' releases through 2026-09.
* Fixes failures when reading recent 'DANE' archives (mixed CP437/UTF-8
  member names, non-breaking spaces, renamed files, nested archives) and
  makes downloads atomic so an interrupted transfer cannot corrupt the cache.
* Unvalidated periods now load with a warning by default, matching the
  'Python' companion package; `allow_unvalidated` is deprecated in favour
  of `strict`.

## R CMD check results

0 errors | 0 warnings | 0 notes (local, R 4.3.3, Ubuntu 24.04).
To be confirmed on win-builder R-release and R-devel before submission.

## Notes for the reviewer

All examples that download data are wrapped in `\donttest{}` plus
`if (interactive())`. Tests that need the network are skipped on CRAN;
the new filename-handling tests use small bundled zip fixtures and run
offline. The cache lives in `tools::R_user_dir("pulso", "cache")`.
