# Makefile for running the Google Shopping scraper


.PHONY: install
install:
	pip install poetry==1.8.2
	poetry install


.PHONY: scrape
scrape:
ifndef QUERY
	@echo Error: A query string for which to search Google Shopping is required. Use make scrape QUERY="<query>"
	@exit 1
else
	poetry run python scrape_to_json.py "$(QUERY)"
endif

.PHONY: clean
clean:
	@if exist debug rmdir /s /q debug
	@if exist shopping_results_*.json del /q shopping_results_*.json
