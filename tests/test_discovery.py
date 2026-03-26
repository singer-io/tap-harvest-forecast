"""Integration tests for tap-harvest-forecast stream discovery with mocked data."""
import io
import json
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from singer import metadata

try:
    from .base import HarvestForecastBaseTest
except ImportError:
    from base import HarvestForecastBaseTest

import tap_harvest_forecast


class HarvestForecastDiscoveryTest(HarvestForecastBaseTest, unittest.TestCase):
    """Test discovery mode returns valid catalog with proper metadata."""

    def test_discovery_returns_expected_streams(self):
        """Verify all expected streams are discovered."""
        # Patch CONFIG to avoid auth requirement
        with patch.object(tap_harvest_forecast, 'CONFIG', self.MOCK_CONFIG):
            # Call do_discover which writes to stdout
            import sys
            output = io.StringIO()
            with redirect_stdout(output):
                tap_harvest_forecast.do_discover()

            # Parse the output
            catalog = json.loads(output.getvalue())

            # Verify catalog structure
            self.assertIn("streams", catalog)
            self.assertIsInstance(catalog["streams"], list)

            # Get stream names from catalog
            stream_names = {stream["stream"] for stream in catalog["streams"]}

            # Verify all expected streams are present
            self.assertEqual(self.EXPECTED_STREAMS, stream_names)

    def test_discovery_metadata_includes_keys(self):
        """Verify each stream has proper metadata for keys and replication."""
        with patch.object(tap_harvest_forecast, 'CONFIG', self.MOCK_CONFIG):
            output = io.StringIO()
            with redirect_stdout(output):
                tap_harvest_forecast.do_discover()

            catalog = json.loads(output.getvalue())

            for stream_entry in catalog["streams"]:
                stream_name = stream_entry["stream"]
                stream_metadata = metadata.to_map(stream_entry["metadata"])

                # Verify table-key-properties exist
                table_keys = metadata.get(stream_metadata, (), "table-key-properties")
                self.assertIsNotNone(table_keys, f"Stream {stream_name} missing table-key-properties")
                self.assertEqual(
                    set(table_keys),
                    self.EXPECTED_METADATA[stream_name]["primary_keys"],
                    f"Stream {stream_name} has incorrect primary keys"
                )

                # Verify valid-replication-keys exist
                replication_keys = metadata.get(stream_metadata, (), "valid-replication-keys")
                self.assertIsNotNone(replication_keys, f"Stream {stream_name} missing replication keys")
                self.assertEqual(
                    set(replication_keys),
                    self.EXPECTED_METADATA[stream_name]["replication_keys"],
                    f"Stream {stream_name} has incorrect replication keys"
                )

    def test_discovery_automatic_fields(self):
        """Verify primary and replication keys are marked as automatic."""
        with patch.object(tap_harvest_forecast, 'CONFIG', self.MOCK_CONFIG):
            output = io.StringIO()
            with redirect_stdout(output):
                tap_harvest_forecast.do_discover()

            catalog = json.loads(output.getvalue())

            for stream_entry in catalog["streams"]:
                stream_name = stream_entry["stream"]
                stream_metadata = metadata.to_map(stream_entry["metadata"])

                # Get automatic fields (primary + replication keys)
                expected_automatic = (
                    self.EXPECTED_METADATA[stream_name]["primary_keys"] |
                    self.EXPECTED_METADATA[stream_name]["replication_keys"]
                )

                # Verify each automatic field has inclusion=automatic
                for field_name in expected_automatic:
                    inclusion = metadata.get(
                        stream_metadata,
                        ("properties", field_name),
                        "inclusion"
                    )
                    self.assertEqual(
                        inclusion,
                        "automatic",
                        f"Field {field_name} in {stream_name} should be automatic"
                    )

    def test_discovery_schemas_are_valid(self):
        """Verify each stream's schema is a valid JSON schema."""
        with patch.object(tap_harvest_forecast, 'CONFIG', self.MOCK_CONFIG):
            output = io.StringIO()
            with redirect_stdout(output):
                tap_harvest_forecast.do_discover()

            catalog = json.loads(output.getvalue())

            for stream_entry in catalog["streams"]:
                stream_name = stream_entry["stream"]
                schema = stream_entry["schema"]

                # Verify basic schema structure
                self.assertIn("type", schema, f"{stream_name} schema missing 'type'")
                self.assertIn("properties", schema, f"{stream_name} schema missing 'properties'")
                self.assertIsInstance(schema["properties"], dict)

                # Verify id and updated_at are in schema
                self.assertIn("id", schema["properties"], f"{stream_name} missing 'id' in schema")
                self.assertIn("updated_at", schema["properties"], f"{stream_name} missing 'updated_at' in schema")
