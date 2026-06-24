.PHONY: demo run fetch web-install web build

BRAND ?= Fanatics Sportsbook
MARKET ?= GB
SEED ?= 42

run:
	BRAND="$(BRAND)" MARKET="$(MARKET)" SEED="$(SEED)" python3 -m engine.run

fetch:
	BRAND="$(BRAND)" MARKET="$(MARKET)" python3 -m data.fetch --brand "$(BRAND)" --market "$(MARKET)" $(if $(FROM_CSV),--from-csv "$(FROM_CSV)",)

web-install:
	cd web && npm install

web:
	cd web && npm run dev

demo: run
	cd web && test -d node_modules || npm install
	cd web && npm run dev

build: run
	cd web && test -d node_modules || npm install
	cd web && npm run build

