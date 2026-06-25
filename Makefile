.PHONY: run test lint appimage windows-exe clean

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

windows-exe:
	pwsh -NoProfile -File ./scripts/build_windows.ps1

clean:
	rm -rf build dist AppDir
