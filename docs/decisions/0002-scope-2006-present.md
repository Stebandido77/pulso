# ADR 0002: Scope limited to GEIH 2006-present (excludes ECH 2000-2005)

- **Status:** Accepted
- **Date:** 2026-04-27

## Context

The DANE has run successive household surveys with overlapping but distinct designs:

- **ECH (2000-2005)**: Encuesta Continua de Hogares — covered 13 metropolitan areas, different sampling frame, different operational definitions of employment status, different module structure.
- **GEIH 2006-2020**: Gran Encuesta Integrada de Hogares with 2005 Census frame — national coverage including rural (resto), continuous monthly operation.
- **GEIH 2021-present**: Redesigned post-ILO 19th ICLS, 2018 Census frame.

A purely temporal "we'll cover everything since 2000" framing tempts us to include ECH for the appearance of a longer time series. We reject this.

## Decision

The package covers **2006-01 to present**. ECH is explicitly out of scope.

## Rationale

1. **Comparability is the product.** The value proposition of `pulso` is harmonized data across epochs. ECH and GEIH are not the same survey; presenting a unified API across them would imply a comparability we cannot honestly deliver.
2. **Coverage gap is real.** ECH covered 13 cities; GEIH covers 23 cities + rural. Concatenating series across 2005-2006 changes the population definition.
3. **Definitional changes are deep.** ECH and GEIH classify employment, unemployment, and inactivity using subtly different operational rules. A single `ocupado` variable across 2000-2025 would mean different things at different times without a loud warning.
4. **Researchers who need ECH already have tools** for it; they don't need this package to silently include it.
5. **Within-GEIH harmonization (2006↔2021 transition) is hard enough.** That work is documented and survives careful scrutiny because the DANE itself published an empalme document. No equivalent exists for ECH↔GEIH.

## Alternatives considered

- **Include ECH with loud warnings.** Rejected: warnings get ignored. The default behavior of a package is the contract.
- **Separate `ech` package.** Out of scope here, but a reasonable independent project for someone interested.
- **`pulso.legacy.load_ech(...)` namespace.** Rejected: same problem as #1, plus increases maintenance burden.

## Consequences

- README and `docs/caveats.md` state the boundary clearly.
- Users who try `pulso.load(year=2003, ...)` get `DataNotAvailableError` with a helpful message pointing them to ECH resources elsewhere.
- The two-epoch design (`geih_2006_2020`, `geih_2021_present`) is final. No third epoch will be added retroactively for ECH.
