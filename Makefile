test: testtrace
	nosetests3 -v tests/test_*.py

testtrace:
	PYTHONPATH=$$PYTHONPATH:../behavior_tests \
	python3 -m tests.notest_trace
