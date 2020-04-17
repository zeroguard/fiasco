SHELL := bash
MAKEFLAGS += --warn-undefined-variables
.SHELLFLAGS := -euo pipefail -c
SUBMAKE_OPTS := -s
ENV_FILE=.env

###############################################################################
# Configurable constants block
###############################################################################
DC := docker-compose
PACKAGE_NAME := pytaskpool
PIPENV_CMD_RUN := pipenv run

DOCKER_PROJECT := zeroguard
DOCKER_IMAGE := fiasco
DOCKER_VERSION := 0.0.1

DOCKER_TAG := $(DOCKER_PROJECT)/$(DOCKER_IMAGE):$(DOCKER_VERSION)
DOCKER_RUN_OPTS := -it --rm -v `pwd`:/app
DC_RUN_OPTS := --rm -v `pwd`:/app

###############################################################################
# Inferred constants block
###############################################################################
export $(shell test -f $(ENV_FILE) && sed 's/=.*//' $(ENV_FILE))
-include $(ENV_FILE)

###############################################################################
# Host targets
###############################################################################
.PHONY: all
all:
	$(MAKE) $(SUBMAKE_OPTS) dtest

.PHONY: dbuild
dbuild:
	docker build . -t $(DOCKER_TAG) -f Dockerfile

.PHONY: dcbuild
dcbuild:
	$(DC) build

.PHONY: dtest
dtest: dbuild
	$(MAKE) $(SUBMAKE_OPTS) CMD='make test' internal-drun

.PHONY: dctest
dctest: dcbuild
	$(MAKE) $(SUBMAKE_OPTS) CMD='make test' internal-dcrun

.PHONY: dpypi
dpypi: dbuild
	$(MAKE) $(SUBMAKE_OPTS) CMD='make pypi' internal-drun

.PHONY: dcpypi
dcpypi: dcbuild
	$(MAKE) $(SUBMAKE_OPTS) CMD='make pypi' internal-dcrun

.PHONY: dshell
dshell: dbuild
	$(MAKE) $(SUBMAKE_OPTS) CMD='/bin/bash -i' internal-drun

.PHONY: dcshell
dcshell: dcbuild
	$(MAKE) $(SUBMAKE_OPTS) CMD='/bin/bash -i' internal-dcrun

.PHONY: dsafeshell
dsafeshell: dbuild
	$(MAKE) $(SUBMAKE_OPTS) CMD='--shell' internal-drun

.PHONY: dcsafeshell
dcsafeshell: dcbuild
	$(MAKE) $(SUBMAKE_OPTS) CMD='--shell' internal-dcrun

.PHONY: dkill
dkill:
	docker kill $(DOCKER_TAG)

.PHONY: dcdown
dcdown:
	$(DC) down

###############################################################################
# Guest targets
###############################################################################
.PHONY: init
init:
	pip3 install pipenv --upgrade
	pipenv install --dev

.PHONY: test
test:
	$(PIPENV_CMD_RUN) python3 -m pytest

.PHONY: testmark
testmark:
	@echo '---(i) INFO: Running all tests marked with @pytest.mark.testit'
	$(PIPENV_CMD_RUN) python3 -m pytest -m testit

.PHONY: pypi
pypi:
	python3 setup.py sdist bdist_wheel
	$(PIPENV_CMD_RUN) twine upload dist/* || :
	rm -rf build/ dist/ .egg $(PACKAGE_NAME).egg-info

###############################################################################
# Internal host targets
###############################################################################
.PHONY: internal-drun
internal-drun:
	docker run $(DOCKER_RUN_OPTS) $(DOCKER_TAG) $(CMD)

.PHONY: internal-dcrun
internal-dcrun:
	$(DC) run $(DC_RUN_OPTS) $(DOCKER_IMAGE) $(CMD)

.PHONY: internal-dexec
internal-dexec:
	docker exec -it $(DOCKER_TAG) $(CMD)
