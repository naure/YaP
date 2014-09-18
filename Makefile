testall: test testtrace

test:
	nosetests3 -vx tests/test_*.py

testtrace:
	PYTHONPATH=$$PYTHONPATH:../behavior_tests \
	python3 -m tests.notest_trace

fix:
	cp examples/basics.yp-test.py examples/basics.yp.py || true
	cp examples/cmd.yp-test.py examples/cmd.yp.py || true
	cp regtests/trace-test.yml regtests/trace.yml || true
	hg diff || true
