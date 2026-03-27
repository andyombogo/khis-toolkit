"""Smoke tests for the forecasting scaffold."""

import pytest

from khis.forecast import forecast_indicator_series


def test_forecast_scaffold_raises_not_implemented():
    """The forecasting scaffold should signal that implementation is pending."""
    with pytest.raises(NotImplementedError):
        forecast_indicator_series([])
