# Hearthmere build commands. See docs/ASSET_PIPELINE.md.
V ?=

.PHONY: setup assets textures shots validate serve clean help

help:
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-14s %s\n", $$1, $$2}'

setup:  ## install python + node dependencies
	pip3 install --quiet numpy Pillow
	npm install

textures:  ## regenerate all PBR texture sets (slow; incremental by default)
	python3 tools/assetgen/build.py --textures-only $(if $(FORCE),--force-textures,)

assets:  ## build venue meshes (V=<venue> for one)
	python3 tools/assetgen/build.py $(if $(V),--venue $(V),) --skip-textures

shots:  ## render review screenshots (V=<venue> for one)
	@if [ -n "$(V)" ]; then \
	  node tools/render/shoot.mjs --asset assets/meshes/$(V).gltf \
	    --out review/shots/$(V) --label $(V) --views approach,gameplay,detail,orbit; \
	else \
	  for f in assets/meshes/*.gltf; do n=$$(basename $$f .gltf); \
	    node tools/render/shoot.mjs --asset $$f --out review/shots/$$n --label $$n \
	      --views approach,gameplay,detail; done; \
	fi

validate:  ## schema + scale + palette + anachronism checks
	python3 tools/validate.py

serve:  ## run the playable client at :8080
	node client/serve.mjs

clean:
	rm -rf assets/meshes/*.gltf assets/meshes/*.bin review/shots/*
