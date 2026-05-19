"""Test tap discovery mode and metadata."""
from base import HarvestForecastBaseTest
from tap_tester.base_suite_tests.discovery_test import DiscoveryTest


class HarvestForecastDiscoveryTest(DiscoveryTest, HarvestForecastBaseTest):
    """Test tap discovery mode and metadata conforms to standards."""

    @staticmethod
    def name():
        return "tap_tester_harvest_forecast_discovery_test"

    def streams_to_test(self):
        return self.expected_stream_names()
