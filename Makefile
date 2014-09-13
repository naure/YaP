test: testtrace
	nosetests3 -v tests/test_*.py

testtrace:
	PYTHONPATH=$$PYTHONPATH:../tracetest \
	python3 -m tests.notest_trace
