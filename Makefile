YEAR ?= 2025

.PHONY: all $(YEAR) fetch classify normalize stats render lint test clean

$(YEAR): fetch classify normalize stats render

fetch:
	uv run python -m scripts.fetch --year $(YEAR)

classify:
	uv run python -m scripts.classify --year $(YEAR)

normalize:
	uv run python -m scripts.normalize --year $(YEAR)

stats:
	uv run python -m scripts.stats --year $(YEAR)

render:
	uv run python -m scripts.render --year $(YEAR)

lint:
	uv run --extra dev ruff check .

test:
	uv run --extra dev pytest -q

clean:
	rm -rf data/$(YEAR)/raw/*.json data/$(YEAR)/classified.yaml data/$(YEAR)/papers.yaml output/$(YEAR)/*.md
