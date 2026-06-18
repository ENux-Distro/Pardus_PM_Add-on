# Pardus Package Manager Add-On Tool
#
# The GUI needs system GTK 4 (PyGObject), so every venv is created with
# --system-site-packages; Textual is installed into it for the TUI.
#
#   make dev        set up a local venv for development (in ./.venv)
#   make install    install system-wide (payload in /usr/share, launcher in /usr/bin)

PYTHON ?= python3
VENV   := .venv
BIN    := $(VENV)/bin

# System install locations. PREFIX/DESTDIR follow the usual conventions so this
# can also stage into a packaging root, e.g. `make install DESTDIR=/tmp/pkg`.
PREFIX   ?= /usr
DESTDIR  ?=
SHAREDIR := $(DESTDIR)$(PREFIX)/share/pardus-pm
BINDIR   := $(DESTDIR)$(PREFIX)/bin
# Link target as seen at runtime (without the staging DESTDIR prefix).
LINKSRC  := $(PREFIX)/share/pardus-pm/bin/pardus-pm

# Privilege used for writing to system paths. Override for unprivileged staging:
# `make install DESTDIR=/tmp/pkg SUDO=`.
SUDO ?= sudo

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "} {printf "  \033[1m%-14s\033[0m %s\n", $$1, $$2}'

# --- local development venv (./.venv) ---------------------------------------

# Built only when missing; depending on $(BIN)/python lets dev targets require
# the environment without rebuilding it every time.
$(BIN)/python:
	$(PYTHON) -m venv --system-site-packages $(VENV)
	$(BIN)/pip install --upgrade pip

.PHONY: deps
deps: $(BIN)/python ## Install runtime deps into the local dev venv
	$(BIN)/pip install -r requirements.txt

.PHONY: dev
dev: deps ## Install runtime + test deps into the local dev venv
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

# --- system install ---------------------------------------------------------

.PHONY: install
install: ## Install to $(SHAREDIR) and link the launcher into $(BINDIR)
	$(SUDO) rm -rf "$(SHAREDIR)"
	$(SUDO) mkdir -p "$(SHAREDIR)" "$(BINDIR)"
	# Copy the project (minus the dev venv, VCS, and caches) into place.
	tar --exclude='./.venv' --exclude='./.git' --exclude='__pycache__' \
	    --exclude='./.pytest_cache' --exclude='*.pyc' -cf - . \
	    | $(SUDO) tar -xf - -C "$(SHAREDIR)"
	# Build a fresh venv at the install location (a copied venv would have
	# hardcoded paths to the source tree and break).
	$(SUDO) $(PYTHON) -m venv --system-site-packages "$(SHAREDIR)/.venv"
	$(SUDO) "$(SHAREDIR)/.venv/bin/pip" install --upgrade pip
	$(SUDO) "$(SHAREDIR)/.venv/bin/pip" install -r "$(SHAREDIR)/requirements.txt"
	$(SUDO) ln -sf "$(LINKSRC)" "$(BINDIR)/pardus-pm"
	@echo "Installed to $(SHAREDIR); 'pardus-pm' linked into $(BINDIR)"

.PHONY: uninstall
uninstall: ## Remove the system install and the launcher symlink
	$(SUDO) rm -f "$(BINDIR)/pardus-pm"
	$(SUDO) rm -rf "$(SHAREDIR)"
	@echo "Removed $(SHAREDIR) and $(BINDIR)/pardus-pm"

.PHONY: install-user
install-user: ## Install the icon + desktop entry for the current user
	./packaging/install-user.sh

# --- cleanup ----------------------------------------------------------------

.PHONY: clean
clean: ## Remove caches and build artifacts (keeps the venv)
	find . -path ./$(VENV) -prune -o -type d \
		\( -name __pycache__ -o -name .pytest_cache -o -name '*.egg-info' \) \
		-print -exec rm -rf {} + 2>/dev/null || true

.PHONY: distclean
distclean: clean ## Remove everything generated, including the venv
	rm -rf $(VENV)
