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
        streams_to_exclude = {'roles'}
        return self.expected_stream_names().difference(streams_to_exclude)

    def manipulate_state(self):
        """Manipulate state to simulate an interrupted sync.

        Sets the currently_syncing stream and partial bookmarks to test
        that the tap can resume from where it left off.
        """
        return {
            "currently_syncing": "milestones",
            "bookmarks": {
                "assignments": {"updated_at": "2026-04-15T00:00:00Z"},
                "clients": {"updated_at": "2026-05-01T00:00:00Z"},
                # milestones is "currently_syncing" - partial bookmark
                "milestones": {"updated_at": "2026-05-10T00:00:00Z"},
                # Streams after milestones should not have bookmarks from this sync
            }
        }
