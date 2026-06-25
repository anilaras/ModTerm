.PHONY: run test lint appimage clean

PYTHON ?= .venv/bin/python

run:
	$(PYTHON) -m modterm

test:
	QT_QPA_PLATFORM=offscreen $(PYTHON) -m pytest

lint:
	.venv/bin/ruff check src tests packaging/render_icon.py
	.venv/bin/ruff format --check src tests packaging/render_icon.py

appimage:
	./scripts/build_appimage.sh

clean:
	rm -rf build dist AppDir

