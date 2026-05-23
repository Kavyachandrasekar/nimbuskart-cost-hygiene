"""
Unit tests for Cost Janitor helper functions.
Run with: python -m pytest tests/
"""

import sys
import os

# janitor folder-ல இருக்கற functions import பண்ண
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from janitor import tags_to_dict, is_protected, missing_tags


# ─────────────────────────────────────────────
# tags_to_dict() tests
# ─────────────────────────────────────────────
def test_tags_to_dict_normal():
    """Normal tag list → dict conversion"""
    tag_list = [
        {"Key": "Project", "Value": "NimbusKart"},
        {"Key": "Environment", "Value": "staging"},
        {"Key": "Owner", "Value": "Chandu"},
    ]
    result = tags_to_dict(tag_list)
    assert result == {
        "Project": "NimbusKart",
        "Environment": "staging",
        "Owner": "Chandu",
    }

def test_tags_to_dict_empty():
    """Empty tag list → empty dict"""
    assert tags_to_dict([]) == {}

def test_tags_to_dict_none():
    """None → empty dict"""
    assert tags_to_dict(None) == {}


# ─────────────────────────────────────────────
# is_protected() tests
# ─────────────────────────────────────────────
def test_is_protected_true():
    """Protected=true → should be protected"""
    assert is_protected({"Protected": "true"}) == True

def test_is_protected_false():
    """Protected=false → should not be protected"""
    assert is_protected({"Protected": "false"}) == False

def test_is_protected_missing():
    """No Protected tag → should not be protected"""
    assert is_protected({"Project": "NimbusKart"}) == False

def test_is_protected_uppercase():
    """Protected=True (capital T) → should still be protected"""
    assert is_protected({"Protected": "True"}) == True


# ─────────────────────────────────────────────
# missing_tags() tests
# ─────────────────────────────────────────────
def test_missing_tags_none_missing():
    """All required tags present → empty list"""
    tags = {
        "Project": "NimbusKart",
        "Environment": "staging",
        "Owner": "Chandu",
    }
    assert missing_tags(tags) == []

def test_missing_tags_all_missing():
    """No required tags → all three missing"""
    result = missing_tags({})
    assert "Project" in result
    assert "Environment" in result
    assert "Owner" in result

def test_missing_tags_partial():
    """Only some tags missing"""
    tags = {"Project": "NimbusKart"}
    result = missing_tags(tags)
    assert "Environment" in result
    assert "Owner" in result
    assert "Project" not in result
