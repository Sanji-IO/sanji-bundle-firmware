all: pylint test

pylint:
	flake8 -v .
test:
	nosetests --with-coverage --cover-erase --cover-package=firmware

.PHONY: pylint test
