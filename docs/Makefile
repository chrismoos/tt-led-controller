# Makefile for LED Controller Datasheet
# Compiles LaTeX document to PDF

# Configuration
LATEX = pdflatex
LATEXFLAGS = -interaction=nonstopmode -halt-on-error
DOCUMENT = m6502_datasheet
OUTPUT_DIR = build

# Source files
TEX_SOURCE = $(DOCUMENT).tex

# Output files
PDF = $(OUTPUT_DIR)/$(DOCUMENT).pdf

# Default target
.PHONY: all
all: $(PDF)

# Create output directory
$(OUTPUT_DIR):
	mkdir -p $(OUTPUT_DIR)

# Build PDF (run twice for TOC and references)
$(PDF): $(TEX_SOURCE) | $(OUTPUT_DIR)
	$(LATEX) $(LATEXFLAGS) -output-directory=$(OUTPUT_DIR) $(TEX_SOURCE)
	$(LATEX) $(LATEXFLAGS) -output-directory=$(OUTPUT_DIR) $(TEX_SOURCE)

# Quick build (single pass, for drafts)
.PHONY: quick
quick: | $(OUTPUT_DIR)
	$(LATEX) $(LATEXFLAGS) -output-directory=$(OUTPUT_DIR) $(TEX_SOURCE)

# View PDF (macOS)
.PHONY: view
view: $(PDF)
	open $(PDF)

# View PDF (Linux)
.PHONY: view-linux
view-linux: $(PDF)
	xdg-open $(PDF)

# Clean auxiliary files but keep PDF
.PHONY: clean
clean:
	rm -f $(OUTPUT_DIR)/*.aux $(OUTPUT_DIR)/*.log $(OUTPUT_DIR)/*.out \
	      $(OUTPUT_DIR)/*.toc $(OUTPUT_DIR)/*.lof $(OUTPUT_DIR)/*.lot \
	      $(OUTPUT_DIR)/*.fls $(OUTPUT_DIR)/*.fdb_latexmk $(OUTPUT_DIR)/*.synctex.gz

# Clean everything including PDF
.PHONY: distclean
distclean: clean
	rm -f $(PDF)
	rmdir $(OUTPUT_DIR) 2>/dev/null || true

# Continuous build (requires latexmk)
.PHONY: watch
watch:
	latexmk -pdf -pvc -output-directory=$(OUTPUT_DIR) $(TEX_SOURCE)

# Help
.PHONY: help
help:
	@echo "LED Controller Datasheet Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all        - Build PDF (default)"
	@echo "  quick      - Quick single-pass build"
	@echo "  view       - Build and open PDF (macOS)"
	@echo "  view-linux - Build and open PDF (Linux)"
	@echo "  watch      - Continuous build with latexmk"
	@echo "  clean      - Remove auxiliary files"
	@echo "  distclean  - Remove all generated files"
	@echo "  help       - Show this help message"
	@echo ""
	@echo "Requirements:"
	@echo "  - pdflatex (texlive or mactex)"
	@echo "  - latexmk (optional, for watch mode)"
