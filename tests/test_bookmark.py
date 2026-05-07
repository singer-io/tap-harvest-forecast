"""Test tap sets a bookmark and respects it for the next sync of a stream."""
from base import HarvestForecastBaseTest
from tap_tester.base_suite_tests.bookmark_test import BookmarkTest


class HarvestForecastBookmarkTest(BookmarkTest, HarvestForecastBaseTest):
    """Test tap sets a bookmark and respects it for the next sync of a stream."""

    start_date = "2026-03-01T00:00:00Z"
    bookmark_format = "%Y-%m-%dT%H:%M:%S.%fZ"

    initial_bookmarks = {
        "bookmarks": {
            "assignments": {"updated_at": "2026-03-20T00:00:00Z"},
            "clients": {"updated_at": "2026-04-25T00:00:00Z"},
        }
    }

    @staticmethod
    def name():
        return "tap_tester_harvest_forecast_bookmark_test"

    def streams_to_test(self):
        # Exclude roles stream as it's missing updated_at field in data.
        # Exclude milestones, people, projects as all records share the same
        # updated_at value, making it impossible for sync 2 to return fewer
        # records than sync 1 (required by test_first_vs_second_records).
        streams_to_exclude = {
            'roles',
            'milestones',
            'people',
            'projects'
        }
        return self.expected_stream_names().difference(streams_to_exclude)

    def calculate_new_bookmarks(self):
        """Calculates new bookmarks that will result in some records being
        synced in sync 2 (plus any necessary look back data)."""
        new_bookmarks = {
            "assignments": {"updated_at": "2026-04-15T00:00:00Z"},
            "clients": {"updated_at": "2026-05-01T00:00:00Z"},
        }
        return new_bookmarks
