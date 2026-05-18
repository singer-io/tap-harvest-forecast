"""Test tap can resume from an interrupted sync."""
from base import HarvestForecastBaseTest
from tap_tester.base_suite_tests.interrupted_sync_test import InterruptedSyncTest


class HarvestForecastInterruptedSyncTest(InterruptedSyncTest, HarvestForecastBaseTest):
    """Test tap sets a bookmark and respects it for the next sync of a stream."""

    @staticmethod
    def name():
        return "tap_tester_harvest_forecast_interrupted_sync_test"

    def streams_to_test(self):
        # Exclude roles stream as it's missing updated_at field in data
        # assignments, milestones: API date-range param filters by activity dates
        # independently of updated_at.
        streams_to_exclude = {
            "roles",
            "assignments",
            "milestones"
        }
        return self.expected_stream_names().difference(streams_to_exclude)

    def manipulate_state(self):
        """Manipulate state to simulate an interrupted sync.

        Sets the currently_syncing stream and partial bookmarks to test
        that the tap can resume from where it left off.
        """
        return {
            "currently_syncing": "people",
            "bookmarks": {
                "clients": {"updated_at": "2026-05-06T00:00:00Z"},
                "people": {"updated_at": "2026-05-06T00:00:00Z"},
            }
        }
