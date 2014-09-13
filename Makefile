test: testtrace
	nosetests3 -v tests/test_*.py

testtrace:
	python3 -m tests.notest_trace
