"""
Base class for mock integration tests for tap-harvest-forecast.

Runs the real tap code against mocked HTTP responses — no external
tap-tester dependency and no actual API credentials required.
Mock data is generated dynamically from the JSON schema files.
"""
import os
from unittest.mock import MagicMock, patch

from singer import metadata, Catalog, CatalogEntry
from singer.schema import Schema

import tap_harvest_forecast as thf

from .mock_data_generator import MockDataGenerator


SCHEMAS_DIR = os.path.join(
    os.path.dirname(os.path.realpath(thf.__file__)),
    'schemas',
)

STREAM_CONFIG = {
    'assignments': {
        'replication_method': 'INCREMENTAL',
        'replication_key': 'updated_at',
        'record_count': 3,
        'date_fields': ['start_date', 'end_date'],
    },
    'clients': {
        'replication_method': 'INCREMENTAL',
        'replication_key': 'updated_at',
        'record_count': 3,
        'date_fields': [],
    },
    'milestones': {
        'replication_method': 'INCREMENTAL',
        'replication_key': 'updated_at',
        'record_count': 3,
        'date_fields': [],
    },
    'people': {
        'replication_method': 'INCREMENTAL',
        'replication_key': 'updated_at',
        'record_count': 3,
        'date_fields': [],
    },
    'projects': {
        'replication_method': 'INCREMENTAL',
        'replication_key': 'updated_at',
        'record_count': 3,
        'date_fields': ['start_date', 'end_date'],
    },
    'roles': {
        'replication_method': 'FULL_TABLE',
        'replication_key': None,
        'record_count': 2,
        'date_fields': [],
    },
}

ALL_STREAM_IDS = set(STREAM_CONFIG.keys())

INCREMENTAL_STREAMS = {
    name for name, cfg in STREAM_CONFIG.items()
    if cfg['replication_method'] == 'INCREMENTAL'
}

FULL_TABLE_STREAMS = {
    name for name, cfg in STREAM_CONFIG.items()
    if cfg['replication_method'] == 'FULL_TABLE'
}

DEFAULT_CONFIG = {
    'start_date': '2026-03-01T00:00:00Z',
    'end_date': '2026-06-01',
    'account_id': 'test_account_123',
    'client_id': 'test_client_id',
    'client_secret': 'test_client_secret',
    'refresh_token': 'test_refresh_token',
}


class HarvestForecastMockBaseTest:
    """Shared helpers for mock integration tests."""

    default_config = DEFAULT_CONFIG.copy()

    _generator = MockDataGenerator(SCHEMAS_DIR)

    @classmethod
    def _get_mock_records(cls, stream_name, updated_at_base='2026-04-15T10:00:00Z'):
        """Return dynamically generated mock records with deterministic updated_at values."""
        cfg = STREAM_CONFIG[stream_name]
        count = cfg['record_count']
        rep_key = cfg['replication_key']

        records = []
        for i in range(count):
            rec = cls._generator.generate_record(stream_name, seed=i)
            if rep_key:
                # Set deterministic, increasing updated_at values
                rec[rep_key] = f"2026-04-{15 + i:02d}T10:00:00Z"
            records.append(rec)
        return records

    @classmethod
    def _make_mock_auth(cls):
        """Create a mock AUTH object."""
        auth = MagicMock()
        auth.get_access_token.return_value = 'mock_access_token'
        auth.get_account_id.return_value = 'mock_account_123'
        return auth

    @classmethod
    def _make_mock_request(cls):
        """Return a side_effect function for patching tap_harvest_forecast.request.

        Extracts the stream name from the URL path and returns
        ``{stream_name: [records]}``.
        """
        def mock_request(url, params=None):
            stream_name = url.rstrip('/').split('/')[-1]
            records = cls._get_mock_records(stream_name) if stream_name in STREAM_CONFIG else []
            return {stream_name: records}
        return mock_request

    @classmethod
    def _build_catalog(cls):
        """Build a Catalog object from the tap's discover logic without stdout."""
        streams = []
        for endpoint in thf.ENDPOINTS:
            schema_dict = thf.load_schema(endpoint)
            schema_obj = Schema.from_dict(schema_dict)
            mdata = metadata.new()
            has_rep_key = thf.REPLICATION_KEY in schema_dict.get('properties', {})

            mdata = metadata.write(mdata, (), 'table-key-properties', [thf.PRIMARY_KEY])
            if has_rep_key:
                mdata = metadata.write(mdata, (), 'valid-replication-keys', [thf.REPLICATION_KEY])
                mdata = metadata.write(mdata, (), 'forced-replication-method', 'INCREMENTAL')
            else:
                mdata = metadata.write(mdata, (), 'forced-replication-method', 'FULL_TABLE')

            for field_name in schema_dict['properties']:
                if field_name == thf.PRIMARY_KEY or (has_rep_key and field_name == thf.REPLICATION_KEY):
                    mdata = metadata.write(mdata, ('properties', field_name), 'inclusion', 'automatic')
                else:
                    mdata = metadata.write(mdata, ('properties', field_name), 'inclusion', 'available')

            entry = CatalogEntry(
                stream=endpoint,
                tap_stream_id=endpoint,
                key_properties=[thf.PRIMARY_KEY],
                schema=schema_obj,
                metadata=metadata.to_list(mdata),
            )
            streams.append(entry)
        return Catalog(streams)

    @classmethod
    def _make_selected_catalog(cls, stream_names=None):
        """Return a catalog with *stream_names* selected (None = select all)."""
        catalog = cls._build_catalog()
        for entry in catalog.streams:
            is_selected = stream_names is None or entry.tap_stream_id in stream_names
            mdata = metadata.to_map(entry.metadata)
            mdata = metadata.write(mdata, (), 'selected', is_selected)
            entry.metadata = metadata.to_list(mdata)
        return catalog

    def run_sync(self, catalog, state=None, config=None):
        """Run do_sync and return (written_records, final_state).

        Uses patch.dict on the module-level STATE and CONFIG dicts so that
        in-place mutations made by sync_endpoint are visible during the call
        and captured before the patch is torn down.
        """
        test_state = state if state is not None else {}
        test_config = config if config is not None else self.default_config.copy()
        written_records = []

        def capture_message(msg):
            if hasattr(msg, 'record'):
                written_records.append((msg.stream, msg.record))

        with patch.dict(thf.STATE, test_state, clear=True), \
             patch.dict(thf.CONFIG, test_config, clear=True), \
             patch.object(thf, 'AUTH', self._make_mock_auth()), \
             patch.object(thf, 'request', side_effect=self._make_mock_request()), \
             patch('singer.write_state'), \
             patch('singer.write_schema'), \
             patch('singer.write_message', side_effect=capture_message):
            thf.do_sync(catalog)
            # Capture state snapshot _inside_ the patch context, before teardown.
            final_state = {k: v for k, v in thf.STATE.items()}

        return written_records, final_state

    @classmethod
    def get_max_bookmark(cls, stream_name):
        """Return the max replication_key value from mock records."""
        rep_key = STREAM_CONFIG[stream_name]['replication_key']
        if not rep_key:
            return None
        return max(r[rep_key] for r in cls._get_mock_records(stream_name))

    @classmethod
    def get_initial_bookmark(cls, stream_name):
        """Return a bookmark date before all mock records for *stream_name*."""
        return '2026-04-01T00:00:00Z'
