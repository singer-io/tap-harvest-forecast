"""Test that with no fields selected for a stream automatic fields are still replicated."""
from base import HarvestForecastBaseTest
from tap_tester.base_suite_tests.automatic_fields_test import MinimumSelectionTest


class HarvestForecastAutomaticFieldsTest(MinimumSelectionTest, HarvestForecastBaseTest):
    """Test that with no fields selected for a stream automatic fields are
    still replicated."""

    @staticmethod
    def name():
        return "tap_tester_harvest_forecast_automatic_fields_test"

    def streams_to_test(self):
        # Exclude streams where test data is not available
        streams_to_exclude = {
            'roles',
        }
        return self.expected_stream_names().difference(streams_to_exclude)
