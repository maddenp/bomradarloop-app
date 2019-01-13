SHELL=/bin/bash
TARGETS = devserver

.ONESHELL:

.PHONY: $(TARGETS)

all:
	$(error Valid targets are: $(TARGETS))

devserver: prep
	CLOUDSDK_PYTHON=python2 dev_appserver.py app.yaml

prep:
	python3 -m venv env
	source env/bin/activate
	pip install -t lib -r requirements.txt
