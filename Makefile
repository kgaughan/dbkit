test:
	python setup.py test

upload:
	python setup.py sdist bdist_wheel upload

tag:
	@git tag v$$(python setup.py --version)
	@echo Tagged with version in setup.py: v$$(python setup.py --version)
	@echo Remember to run: git push --tags

.PHONY: test upload tag
