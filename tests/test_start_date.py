"""Test tap respects start date for incremental streams."""
from base import HarvestForecastBaseTest
from tap_tester.base_suite_tests.start_date_test import StartDateTest


class HarvestForecastStartDateTest(StartDateTest, HarvestForecastBaseTest):
    """Instantiate start date according to the desired data set and run the test."""

    @staticmethod
    def name():
        return "tap_tester_harvest_forecast_start_date_test"

    def streams_to_test(self):
        # Exclude roles stream as it's missing updated_at field in data
        streams_to_exclude = {'roles'}
        return self.expected_stream_names().difference(streams_to_exclude)

    @property
    def start_date_1(self):
        """Start date before all test data."""
        return "2026-03-01T00:00:00Z"

    @property
    def start_date_2(self):
        """Start date in the middle of test data range."""
        return "2026-04-21T00:00:00Z"
