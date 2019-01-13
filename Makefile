SHELL   = /bin/bash
TARGETS = deploy devserver

.ONESHELL:

.PHONY: $(TARGETS)

all:
	$(error Valid targets are: $(TARGETS))

deploy: prep
	gcloud app deploy --project bomradar

devserver: prep
	CLOUDSDK_PYTHON=python2 dev_appserver.py app.yaml

prep:
	pip install -t lib -r requirements.txt
