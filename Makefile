test:
	python3 setup.py test

upload:
	python3 setup.py sdist bdist_wheel upload

tag:
	@git tag v$$(python3 setup.py --version)
	@echo Tagged with version in setup.py: v$$(python3 setup.py --version)
	@echo Remember to run: git push --tags

docs:
	@python3 setup.py build_sphinx

dev:
	@pip3 install -e .
	@pip3 install Sphinx

clean:
	@mkdir -p docs/_static
	@rm -rf docs/_build

.PHONY: docs test upload tag dev clean
