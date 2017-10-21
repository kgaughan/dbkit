test:
	python setup.py test

upload:
	python setup.py sdist bdist_wheel upload

tag:
	@git tag v$$(python setup.py --version)
	@echo Tagged with version in setup.py: v$$(python setup.py --version)
	@echo Remember to run: git push --tags

docs:
	@python setup.py build_sphinx

dev:
	@pip install -e .
	@pip install Sphinx

clean:
	@mkdir -p docs/_static
	@rm -rf docs/_build

.PHONY: docs test upload tag dev clean
