# Makefile for running the Google Shopping scraper


.PHONY: install
install:
	pip install poetry==1.8.2
	poetry install


.PHONY: run
run:
	@echo Starting Google Shopping Scraper API...
	poetry run python run_api.py


.PHONY: stop
stop:
	@echo Stopping Google Shopping Scraper API...
	@for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do taskkill /f /pid %%a 2>nul || echo No API process found on port 8000


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
