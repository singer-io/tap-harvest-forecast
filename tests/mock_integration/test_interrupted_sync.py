"""Mock integration test: interrupted sync — tap resumes from the stream
stored in currently_syncing and clears it after a full successful sync."""
import unittest
from unittest.mock import patch
from singer import utils as singer_utils

import tap_harvest_forecast as thf

from .base import (
    HarvestForecastMockBaseTest,
    ALL_STREAM_IDS,
    INCREMENTAL_STREAMS,
)


class InterruptedSyncMockIntegrationTest(HarvestForecastMockBaseTest, unittest.TestCase):

    def test_currently_syncing_cleared_after_full_sync(self):
        """STATE['currently_syncing'] must be removed after a complete sync."""
        catalog = self._make_selected_catalog()
        initial_state = {
            'currently_syncing': 'milestones',
            'bookmarks': {
                'assignments': {'updated_at': '2026-04-16T10:00:00Z'},
                'clients': {'updated_at': '2026-04-16T10:00:00Z'},
            },
        }
        _, state = self.run_sync(catalog, state=initial_state)
        self.assertNotIn('currently_syncing', state,
            "currently_syncing should be cleared after a successful full sync")

    def test_all_streams_processed_after_resume(self):
        """Resuming a mid-sync interruption should still write records for all streams."""
        catalog = self._make_selected_catalog()
        # Interrupt mid-way at 'milestones' (alphabetical order: assignments, clients, milestones, ...)
        initial_state = {
            'currently_syncing': 'milestones',
            'bookmarks': {
                'assignments': {'updated_at': '2026-04-16T10:00:00Z'},
                'clients': {'updated_at': '2026-04-16T10:00:00Z'},
            },
        }
        records, _ = self.run_sync(catalog, state=initial_state)
        written_streams = {s for s, _ in records}
        for stream in ALL_STREAM_IDS:
            with self.subTest(stream=stream):
                self.assertIn(stream, written_streams,
                    f"Stream '{stream}' should have been synced on resume")

    def test_interrupted_stream_synced_before_previous_streams(self):
        """The interrupted stream must be the FIRST stream processed on resume."""
        synced_order = []
        original = thf.sync_endpoint

        def tracking_sync_endpoint(catalog_entry, schema, mdata, date_fields=None):
            synced_order.append(catalog_entry.tap_stream_id)
            return original(catalog_entry, schema, mdata, date_fields)

        catalog = self._make_selected_catalog()
        initial_state = {
            'currently_syncing': 'people',
            'bookmarks': {
                'assignments': {'updated_at': '2026-04-17T00:00:00Z'},
                'clients': {'updated_at': '2026-04-17T00:00:00Z'},
                'milestones': {'updated_at': '2026-04-17T00:00:00Z'},
            },
        }

        with patch.object(thf, 'sync_endpoint', side_effect=tracking_sync_endpoint):
            self.run_sync(catalog, state=initial_state)

        self.assertGreater(len(synced_order), 0, "sync_endpoint was never called")
        self.assertEqual(synced_order[0], 'people',
            f"Expected 'people' to be synced first on resume, got '{synced_order[0]}'")

    def test_bookmarks_preserved_for_already_completed_streams(self):
        """Bookmarks for streams already completed before the interruption are preserved."""
        catalog = self._make_selected_catalog()
        completed_bookmark = '2026-04-16T10:00:00Z'
        initial_state = {
            'currently_syncing': 'milestones',
            'bookmarks': {
                'assignments': {'updated_at': completed_bookmark},
                'clients': {'updated_at': completed_bookmark},
            },
        }
        _, state = self.run_sync(catalog, state=initial_state)

        # Completed streams' bookmarks must not be erased
        for stream in ('assignments', 'clients'):
            self.assertIn(stream, state.get('bookmarks', {}),
                f"Bookmark for '{stream}' was lost after interrupted sync resume")

    def test_clean_sync_without_interruption_sets_no_currently_syncing(self):
        """A fresh sync with no prior state must not leave currently_syncing behind."""
        catalog = self._make_selected_catalog()
        _, state = self.run_sync(catalog, state={})
        self.assertNotIn('currently_syncing', state)

    def test_sync_resumes_from_last_bookmark_on_interruption(self):
        """Two-sync scenario: second sync only processes records >= bookmark from
        first sync. Ported from previously approved mock test."""
        for stream_name in INCREMENTAL_STREAMS:
            with self.subTest(stream=stream_name):
                # --- First sync: 3 records ---
                batch_1 = [
                    {'id': 1, 'updated_at': '2026-04-10T12:00:00Z'},
                    {'id': 2, 'updated_at': '2026-04-12T12:00:00Z'},
                    {'id': 3, 'updated_at': '2026-04-15T12:00:00Z'},
                ]

                def request_batch_1(url, params=None):
                    sn = url.rstrip('/').split('/')[-1]
                    return {sn: batch_1 if sn == stream_name else []}

                catalog = self._make_selected_catalog(stream_names=[stream_name])

                with patch.dict(thf.STATE, {}, clear=True), \
                     patch.dict(thf.CONFIG, self.default_config.copy(), clear=True), \
                     patch.object(thf, 'AUTH', self._make_mock_auth()), \
                     patch.object(thf, 'request', side_effect=request_batch_1), \
                     patch('singer.write_state'), \
                     patch('singer.write_schema'), \
                     patch('singer.write_message'):
                    thf.do_sync(catalog)
                    state_after_first = {k: v for k, v in thf.STATE.items()}

                self.assertIn(stream_name, state_after_first.get('bookmarks', {}),
                    f"{stream_name}: STATE missing bookmark after first sync")

                bookmark_after_first = state_after_first['bookmarks'][stream_name]['updated_at']
                bookmark_dt = singer_utils.strptime_to_utc(bookmark_after_first)

                # --- Second sync: new records starting from overlap ---
                batch_2 = [
                    {'id': 3, 'updated_at': '2026-04-15T12:00:00Z'},  # overlap
                    {'id': 4, 'updated_at': '2026-04-20T12:00:00Z'},
                    {'id': 5, 'updated_at': '2026-04-25T12:00:00Z'},
                ]

                def request_batch_2(url, params=None):
                    sn = url.rstrip('/').split('/')[-1]
                    return {sn: batch_2 if sn == stream_name else []}

                written_second = []

                with patch.dict(thf.STATE, state_after_first, clear=True), \
                     patch.dict(thf.CONFIG, self.default_config.copy(), clear=True), \
                     patch.object(thf, 'AUTH', self._make_mock_auth()), \
                     patch.object(thf, 'request', side_effect=request_batch_2), \
                     patch('singer.write_state'), \
                     patch('singer.write_schema'), \
                     patch('singer.write_message',
                           side_effect=lambda m: written_second.append(m.record)
                           if hasattr(m, 'record') else None):
                    thf.do_sync(catalog)

                # All records written in second sync must be >= bookmark
                for rec in written_second:
                    rec_dt = singer_utils.strptime_to_utc(rec['updated_at'])
                    self.assertGreaterEqual(
                        rec_dt, bookmark_dt,
                        f"{stream_name}: second sync wrote record with updated_at={rec['updated_at']} "
                        f"which is before bookmark={bookmark_after_first}",
                    )
