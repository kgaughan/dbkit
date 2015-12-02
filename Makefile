test:
	python setup.py test

upload:
	python setup.py sdist bdist_wheel upload

.PHONY: test upload
