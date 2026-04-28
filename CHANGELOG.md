# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Phase 0 — Scaffolding

- Initial project structure for `pulso`
- JSON schemas for `sources.json`, `variable_map.json`, `epochs.json`
- Public API stubs (raise `NotImplementedError`)
- CI workflow (lint + tests on each PR)
- Branch path enforcement: `feat/code-*` cannot touch data, `feat/data-*` cannot touch core
- Documentation skeleton

[Unreleased]: https://github.com/Stebandido77/pulso/compare/v0.0.0...HEAD
