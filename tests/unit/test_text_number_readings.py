"""_readings: the values a digit string can mean."""
import pytest
from vitae.verify.text import _readings


@pytest.mark.parametrize("raw, want", [
    ("12", {12.0}),
    ("1.500", {1.5, 1500.0}),         # ambiguous: DE thousands or decimal
    ("0.500", {0.5}),                 # leading zero: only a decimal
    ("1.5", {1.5}),
    ("3,14", {3.14}),
    ("1,500", {1500.0}),              # EN thousands
    ("1,5000", {1.5}),                # four decimals: not a thousands group
    ("1.500.000", {1500000.0}),
    ("1,500,000", {1500000.0}),
    ("1.500,50", {1500.5}),
    ("1,500.50", {1500.5}),
    ("999.999", {999.999, 999999.0}),  # boundary: widest integer part still read as thousands
    ("1000.500", {1000.5}),            # boundary: four-digit integer part is a decimal only
], ids=str)
def test_number_readings(raw, want):
    assert set(_readings(raw)) == want
