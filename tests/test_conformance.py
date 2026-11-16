
"""Conformance cases: the reference models reproduce behaviour stated in provider documentation or RFC 9111."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from cci.conformance import results
CASES = results()
@pytest.mark.parametrize('name,source,passed', CASES, ids=[c[0] for c in CASES])
def test_conformance(name, source, passed):
    assert passed, name
