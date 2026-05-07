"""Test that all fields are replicated for each stream."""
from base import HarvestForecastBaseTest
from tap_tester.base_suite_tests.all_fields_test import AllFieldsTest


class HarvestForecastAllFieldsTest(AllFieldsTest, HarvestForecastBaseTest):
    """Ensure running the tap with all streams and fields selected results in
    the replication of all fields."""
    MISSING_FIELDS = {
        'roles': {'updated_at', 'updated_by_id'}
    }

    @staticmethod
    def name():
        return "tap_tester_harvest_forecast_all_fields_test"

    def streams_to_test(self):
        # Exclude streams where test data is not available
        streams_to_exclude = {}
        return self.expected_stream_names().difference(streams_to_exclude)
