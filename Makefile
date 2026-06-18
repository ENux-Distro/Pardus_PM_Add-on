# Pardus Package Manager Add-On Tool
#
# The GUI needs system GTK 4 (PyGObject), so the venv is created with
# --system-site-packages; Textual is installed into it for the TUI.

PYTHON ?= python3
VENV   := .venv
BIN    := $(VENV)/bin

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "} {printf "  \033[1m%-14s\033[0m %s\n", $$1, $$2}'

# Create the venv only when it is missing. Depending on $(BIN)/python lets other
# targets require the environment without rebuilding it every time.
$(BIN)/python:
	$(PYTHON) -m venv --system-site-packages $(VENV)
	$(BIN)/pip install --upgrade pip

.PHONY: install
install: $(BIN)/python ## Create the venv and install runtime dependencies
	$(BIN)/pip install -r requirements.txt

.PHONY: dev
dev: install ## Install runtime + development (test) dependencies
	$(BIN)/pip install -r requirements-dev.txt

.PHONY: run
run: ## Launch the default UI (TUI)
	./bin/pardus-pm

.PHONY: tui
tui: ## Launch the text UI
	./bin/pardus-pm tui

.PHONY: gui
gui: ## Launch the graphical UI
	./bin/pardus-pm gui

.PHONY: test
test: dev ## Run the test suite
	$(BIN)/python -m pytest tests/ -q

.PHONY: install-user
install-user: ## Install the icon + desktop entry for the current user
	./packaging/install-user.sh

.PHONY: clean
clean: ## Remove caches and build artifacts (keeps the venv)
	find . -path ./$(VENV) -prune -o -type d \
		\( -name __pycache__ -o -name .pytest_cache -o -name '*.egg-info' \) \
		-print -exec rm -rf {} + 2>/dev/null || true

.PHONY: distclean
distclean: clean ## Remove everything generated, including the venv
	rm -rf $(VENV)
