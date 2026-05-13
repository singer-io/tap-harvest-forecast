"""Mock integration test: start_date — records before the configured start
date are excluded; existing bookmarks override start_date."""
import unittest
from unittest.mock import patch

from singer import utils as singer_utils

import tap_harvest_forecast as thf

from .base import (
    HarvestForecastMockBaseTest,
    STREAM_CONFIG,
    INCREMENTAL_STREAMS,
    FULL_TABLE_STREAMS,
)


class StartDateMockIntegrationTest(HarvestForecastMockBaseTest, unittest.TestCase):

    def test_records_before_start_date_are_excluded(self):
        """Set start_date to mid-range: only records >= start_date are written."""
        # Mock records have updated_at: 04-15, 04-16, 04-17 (all at T10:00:00Z)
        # start_date = 04-16T00:00:00Z -> records on 04-16 and 04-17 survive (2 of 3)
        start_date = '2026-04-16T00:00:00Z'
        config = self.default_config.copy()
        config['start_date'] = start_date

        for stream in INCREMENTAL_STREAMS:
            with self.subTest(stream=stream):
                catalog = self._make_selected_catalog(stream_names=[stream])
                records, _ = self.run_sync(catalog, state={}, config=config)

                stream_records = [r for s, r in records if s == stream]
                self.assertGreater(len(stream_records), 0,
                    f"No records synced for {stream}")
                for rec in stream_records:
                    self.assertGreaterEqual(
                        rec['updated_at'], start_date,
                        f"{stream}: record updated_at={rec['updated_at']} is before start_date={start_date}",
                    )

    def test_all_records_synced_when_start_date_before_all_data(self):
        """A start_date before all mock records should yield all records."""
        config = self.default_config.copy()
        config['start_date'] = '2026-01-01T00:00:00Z'

        for stream in INCREMENTAL_STREAMS:
            with self.subTest(stream=stream):
                catalog = self._make_selected_catalog(stream_names=[stream])
                records, _ = self.run_sync(catalog, state={}, config=config)

                stream_records = [r for s, r in records if s == stream]
                self.assertEqual(
                    len(stream_records), STREAM_CONFIG[stream]['record_count'],
                    f"{stream}: expected {STREAM_CONFIG[stream]['record_count']} records",
                )

    def test_existing_bookmark_takes_priority_over_start_date(self):
        """An existing state bookmark overrides start_date."""
        config = self.default_config.copy()
        config['start_date'] = '2026-01-01T00:00:00Z'

        bookmark = '2026-04-16T10:00:00Z'
        for stream in INCREMENTAL_STREAMS:
            with self.subTest(stream=stream):
                initial_state = {'bookmarks': {stream: {'updated_at': bookmark}}}
                catalog = self._make_selected_catalog(stream_names=[stream])
                records, _ = self.run_sync(catalog, state=initial_state, config=config)

                stream_records = [r for s, r in records if s == stream]
                bookmark_dt = singer_utils.strptime_to_utc(bookmark)
                for rec in stream_records:
                    rec_dt = singer_utils.strptime_to_utc(rec['updated_at'])
                    self.assertGreaterEqual(
                        rec_dt, bookmark_dt,
                        f"{stream}: record before bookmark was not filtered",
                    )

    def test_full_table_streams_ignore_start_date(self):
        """FULL_TABLE streams should return all records regardless of start_date."""
        for future_start in ['2025-01-01T00:00:00Z', '2027-01-01T00:00:00Z']:
            config = self.default_config.copy()
            config['start_date'] = future_start
            config['end_date'] = '2027-12-31'

            for stream in FULL_TABLE_STREAMS:
                with self.subTest(stream=stream, start=future_start):
                    catalog = self._make_selected_catalog(stream_names=[stream])
                    records, _ = self.run_sync(catalog, state={}, config=config)
                    stream_records = [r for s, r in records if s == stream]
                    # All records written regardless of start_date
                    self.assertEqual(
                        len(stream_records), STREAM_CONFIG[stream]['record_count'],
                        f"{stream}: expected all {STREAM_CONFIG[stream]['record_count']} records",
                    )

    def test_different_start_dates_produce_different_record_counts(self):
        """Records synced shrink as start_date moves forward through the data range."""
        stream = 'assignments'
        catalog = self._make_selected_catalog(stream_names=[stream])

        config_early = self.default_config.copy()
        config_early['start_date'] = '2026-01-01T00:00:00Z'
        records_early, _ = self.run_sync(catalog, state={}, config=config_early)
        count_early = len([r for s, r in records_early if s == stream])

        config_late = self.default_config.copy()
        config_late['start_date'] = '2026-04-17T00:00:00Z'
        records_late, _ = self.run_sync(catalog, state={}, config=config_late)
        count_late = len([r for s, r in records_late if s == stream])

        self.assertGreater(count_early, count_late,
            "Earlier start_date should produce more records than later start_date")

    def test_start_date_becomes_initial_bookmark(self):
        """Verify get_start() returns config start_date when no state exists."""

        start_date = '2026-03-01T00:00:00Z'
        config = self.default_config.copy()
        config['start_date'] = start_date

        for stream_name in INCREMENTAL_STREAMS:
            with self.subTest(stream=stream_name):
                with patch.dict(thf.STATE, {}, clear=True), \
                     patch.dict(thf.CONFIG, config, clear=True):
                    result = thf.get_start(stream_name)
                self.assertEqual(result, start_date,
                    f"{stream_name}: get_start should return config start_date when state is empty")

    def test_empty_state_uses_config_start_date(self):
        """Verify get_start() falls back to CONFIG['start_date'] with empty STATE."""

        start_date = '2026-01-01T00:00:00Z'
        config = self.default_config.copy()
        config['start_date'] = start_date

        for stream_name in INCREMENTAL_STREAMS:
            with self.subTest(stream=stream_name):
                with patch.dict(thf.STATE, {}, clear=True), \
                     patch.dict(thf.CONFIG, config, clear=True):
                    result = thf.get_start(stream_name)
                self.assertEqual(result, start_date)

    def test_bookmark_overrides_start_date(self):
        """Verify existing bookmark takes precedence over config start_date."""

        start_date = '2026-01-01T00:00:00Z'
        bookmark_date = '2026-04-15T10:00:00Z'
        config = self.default_config.copy()
        config['start_date'] = start_date

        for stream_name in INCREMENTAL_STREAMS:
            with self.subTest(stream=stream_name):
                nested_state = {
                    'bookmarks': {stream_name: {'updated_at': bookmark_date}}
                }
                with patch.dict(thf.STATE, nested_state, clear=True), \
                     patch.dict(thf.CONFIG, config, clear=True):
                    result = thf.get_start(stream_name)
                self.assertEqual(result, bookmark_date,
                    f"{stream_name}: get_start should return bookmark, not config start_date")
