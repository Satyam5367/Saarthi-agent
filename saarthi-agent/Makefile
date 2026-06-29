.PHONY: demo test clean help

help:
	@echo ""
	@echo "  make demo    — run the pipeline on all 8 sample accounts"
	@echo "  make test    — run the full test suite"
	@echo "  make clean   — remove generated output files"
	@echo ""

demo:
	python -m agent.pipeline --limit 8 --seed 7

test:
	pytest tests/ -v

clean:
	rm -f data/outcomes.jsonl
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
