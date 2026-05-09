.PHONY: help sync-data dev-install test test-r lint format build clean

help:
	@echo "Targets: sync-data, dev-install, test, test-r, lint, format, build, clean"

sync-data:
	python scripts/sync_data.py

dev-install: sync-data
	cd python && pip install -e ".[dev]"

test: sync-data
	cd python && pytest -v

test-r:
	Rscript scripts/sync_data_to_r.R
	cd r && Rscript -e 'devtools::test()'

lint:
	cd python && ruff check pulso tests scripts

format:
	cd python && ruff format pulso tests scripts

build: sync-data
	cd python && python -m build

clean:
	rm -rf python/dist python/build python/*.egg-info
	rm -rf python/pulso/data r/inst/extdata
	rm -rf r/.Rcheck r/*.tar.gz
