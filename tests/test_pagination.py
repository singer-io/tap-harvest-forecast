"""Test tap can replicate multiple pages of data for streams that use pagination."""
from tap_tester.base_suite_tests.pagination_test import PaginationTest
from base import HarvestForecastBaseTest


class HarvestForecastPaginationTest(PaginationTest, HarvestForecastBaseTest):
    """
    Ensure tap can replicate multiple pages of data for streams that use pagination.
    """

    @staticmethod
    def name():
        return "tap_tester_harvest_forecast_pagination_test"

    def streams_to_test(self):
        # Exclude streams that don't have enough data to test pagination
        streams_to_exclude = {
            'clients',
            'people',
            'projects',
            'roles',
        }
        return self.expected_stream_names().difference(streams_to_exclude)

    def get_properties(self, original: bool = True):
        """Configuration with reduced page_size to test pagination logic."""
        # Start from the base test configuration to preserve required defaults.
        properties = HarvestForecastBaseTest.get_properties(self, original=original)

        # Override/add properties specific to pagination testing.
        properties["start_date"] = "2025-09-01T00:00:00Z"
        properties["page_size"] = 20

        return properties

    def expected_page_size(self, stream):
        """
        Return the expected page size for pagination testing.

        Overrides the default API_LIMIT to use the configured page_size.
        This allows pagination testing with smaller datasets by setting
        a lower page limit than the API default (100).
        """
        return self.get_properties().get("page_size", 20)
