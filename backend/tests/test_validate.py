"""
Validation tests - add as you build out validate2.py
"""


def test_validate_module_exists():
    """Ensure validate2 module can be imported"""
    from app import validate2
    assert validate2 is not None
