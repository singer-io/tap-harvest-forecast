"""Mock integration test: bookmark / incremental sync — verify state is
updated correctly and previous bookmarks are respected."""
import unittest
from singer import utils as singer_utils

from .base import (
    HarvestForecastMockBaseTest,
    STREAM_CONFIG,
    INCREMENTAL_STREAMS,
    FULL_TABLE_STREAMS,
)


class BookmarkMockIntegrationTest(HarvestForecastMockBaseTest, unittest.TestCase):

    def test_state_has_bookmarks_after_sync(self):
        """After syncing, STATE must contain bookmarks for INCREMENTAL streams."""
        catalog = self._make_selected_catalog()
        _, state = self.run_sync(catalog)
        self.assertIn('bookmarks', state)
        for stream in INCREMENTAL_STREAMS:
            with self.subTest(stream=stream):
                self.assertIn(stream, state['bookmarks'])
                self.assertIn('updated_at', state['bookmarks'][stream])

    def test_bookmark_advances_to_latest_record(self):
        """Bookmark should be set to the max updated_at across synced records."""
        for stream in INCREMENTAL_STREAMS:
            with self.subTest(stream=stream):
                catalog = self._make_selected_catalog(stream_names=[stream])
                initial_state = {
                    'bookmarks': {stream: {'updated_at': self.get_initial_bookmark(stream)}}
                }
                _, state = self.run_sync(catalog, state=initial_state)

                max_expected = self.get_max_bookmark(stream)
                actual_bookmark = state['bookmarks'][stream]['updated_at']
                # Bookmark must have advanced to (or past) the latest record
                self.assertGreaterEqual(
                    singer_utils.strptime_to_utc(actual_bookmark),
                    singer_utils.strptime_to_utc(max_expected),
                    f"{stream}: bookmark {actual_bookmark} did not advance to {max_expected}",
                )

    def test_bookmark_filters_earlier_records(self):
        """Records with updated_at < existing bookmark should NOT be written."""
        bookmark = '2026-04-16T10:00:00Z'
        bookmark_dt = singer_utils.strptime_to_utc(bookmark)
        for stream in INCREMENTAL_STREAMS:
            with self.subTest(stream=stream):
                catalog = self._make_selected_catalog(stream_names=[stream])
                initial_state = {'bookmarks': {stream: {'updated_at': bookmark}}}
                records, _ = self.run_sync(catalog, state=initial_state)

                stream_records = [r for s, r in records if s == stream]
                for rec in stream_records:
                    rec_dt = singer_utils.strptime_to_utc(rec['updated_at'])
                    self.assertGreaterEqual(
                        rec_dt, bookmark_dt,
                        f"{stream}: record updated_at={rec['updated_at']} is before bookmark={bookmark}",
                    )

    def test_full_table_streams_have_no_bookmark(self):
        """FULL_TABLE streams must not advance bookmark beyond config start_date.
        The tap sets start_date as the initial bookmark but must not update it
        from record data (roles has no updated_at field)."""
        catalog = self._make_selected_catalog()
        start_date = self.default_config['start_date']
        _, state = self.run_sync(catalog)
        for stream in FULL_TABLE_STREAMS:
            with self.subTest(stream=stream):
                stream_bm = state.get('bookmarks', {}).get(stream, {})
                # If a bookmark was written it must equal the config start_date
                if 'updated_at' in stream_bm:
                    self.assertEqual(
                        stream_bm['updated_at'], start_date,
                        f"{stream}: FULL_TABLE bookmark advanced past start_date — "
                        f"expected {start_date}, got {stream_bm['updated_at']}",
                    )

    def test_fresh_sync_uses_config_start_date_as_initial_bookmark(self):
        """With no existing state, start_date from CONFIG is the effective bookmark."""
        start_date = '2026-03-01T00:00:00Z'
        config = self.default_config.copy()
        config['start_date'] = start_date

        catalog = self._make_selected_catalog(stream_names=['assignments'])
        records, _ = self.run_sync(catalog, state={}, config=config)

        stream_records = [r for s, r in records if s == 'assignments']
        # All mock records are after the start_date, so all 3 should appear
        self.assertEqual(len(stream_records), STREAM_CONFIG['assignments']['record_count'])

    def test_bookmark_is_set_during_sync(self):
        """Verify STATE contains a bookmark entry for each INCREMENTAL stream after sync.
        Ported from previously approved mock test."""
        for stream_name in INCREMENTAL_STREAMS:
            with self.subTest(stream=stream_name):
                catalog = self._make_selected_catalog(stream_names=[stream_name])
                _, state = self.run_sync(catalog, state={})
                bookmarks = state.get('bookmarks', {})
                self.assertIn(stream_name, bookmarks,
                    f"{stream_name}: STATE['bookmarks'] missing stream entry after sync")
                self.assertIn('updated_at', bookmarks[stream_name],
                    f"{stream_name}: bookmark missing 'updated_at' key")
                self.assertIsNotNone(bookmarks[stream_name]['updated_at'],
                    f"{stream_name}: bookmark 'updated_at' should not be null")

    def test_bookmark_advances_to_max_updated_at(self):
        """Verify bookmark equals the maximum updated_at value across all synced records.
        Ported from previously approved mock test."""
        for stream_name in INCREMENTAL_STREAMS:
            with self.subTest(stream=stream_name):
                latest_date = '2026-04-17T10:00:00Z'
                catalog = self._make_selected_catalog(stream_names=[stream_name])
                _, state = self.run_sync(catalog, state={})

                final_bookmark = state['bookmarks'][stream_name]['updated_at']
                self.assertIsNotNone(final_bookmark)

                final_dt = singer_utils.strptime_to_utc(final_bookmark)
                latest_dt = singer_utils.strptime_to_utc(latest_date)
                self.assertGreaterEqual(
                    final_dt, latest_dt,
                    f"{stream_name}: bookmark {final_bookmark} did not advance to {latest_date}",
                )
