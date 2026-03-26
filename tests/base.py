"""
Base test class for tap-harvest-forecast mock integration tests.
"""
import json
import os
from singer.catalog import CatalogEntry
from singer.schema import Schema


class HarvestForecastBaseTest:
    """Base test class providing common mock data and utilities."""

    # Mock configuration
    MOCK_CONFIG = {
        "start_date": "2024-01-01T00:00:00Z",
        "account_id": "test_account_123",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "refresh_token": "test_refresh_token",
    }

    EXPECTED_STREAMS = {
        "assignments",
        "clients",
        "milestones",
        "people",
        "projects",
        "roles",
    }

    EXPECTED_METADATA = {
        "assignments": {
            "primary_keys": {"id"},
            "replication_method": "INCREMENTAL",
            "replication_keys": {"updated_at"},
        },
        "clients": {
            "primary_keys": {"id"},
            "replication_method": "INCREMENTAL",
            "replication_keys": {"updated_at"},
        },
        "milestones": {
            "primary_keys": {"id"},
            "replication_method": "INCREMENTAL",
            "replication_keys": {"updated_at"},
        },
        "people": {
            "primary_keys": {"id"},
            "replication_method": "INCREMENTAL",
            "replication_keys": {"updated_at"},
        },
        "projects": {
            "primary_keys": {"id"},
            "replication_method": "INCREMENTAL",
            "replication_keys": {"updated_at"},
        },
        "roles": {
            "primary_keys": {"id"},
            "replication_method": "INCREMENTAL",
            "replication_keys": {"updated_at"},
        },
    }

    @classmethod
    def _generate_stream_record(cls, stream_name, record_id=1, updated_at=None):
        """Generate a mock record for the given stream."""
        if updated_at is None:
            updated_at = "2024-03-15T12:00:00Z"

        base_record = {
            "id": record_id,
            "updated_at": updated_at,
        }

        # Add stream-specific fields
        stream_fields = {
            "assignments": {
                "start_date": "2024-03-01",
                "end_date": "2024-03-31",
                "allocation": 40,
                "notes": "Test assignment",
                "updated_by_id": 100,
                "project_id": 1,
                "person_id": 50,
                "placeholder_id": None,
                "repeated_assignment_set_id": None,
                "active_on_days_off": False,
            },
            "clients": {
                "name": f"Client {record_id}",
                "harvest_id": record_id * 100,
                "archived": False,
                "updated_by_id": 100,
            },
            "milestones": {
                "name": f"Milestone {record_id}",
                "date": "2024-04-01T00:00:00Z",
                "updated_by_id": 100,
                "project_id": 1,
            },
            "people": {
                "first_name": "Test",
                "last_name": f"Person {record_id}",
                "email": f"test{record_id}@example.com",
                "login": f"test{record_id}",
                "admin": False,
                "archived": False,
                "subscribed": True,
                "avatar_url": None,
                "roles": ["Developer"],
                "updated_by_id": "100",
                "harvest_user_id": record_id * 100,
                "weekly_capacity": 40,
                "working_days": {
                    "monday": True,
                    "tuesday": True,
                    "wednesday": True,
                    "thursday": True,
                    "friday": True,
                    "saturday": False,
                    "sunday": False,
                },
                "color_blind": None,
                "personal_feed_token_id": None,
            },
            "projects": {
                "name": f"Project {record_id}",
                "color": "blue",
                "code": f"PROJ{record_id}",
                "notes": "Test project notes",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T00:00:00Z",
                "harvest_id": record_id * 100,
                "archived": False,
                "updated_by_id": 100,
                "client_id": 1,
                "tags": ["development", "internal"],
            },
            "roles": {
                "name": f"Role {record_id}",
                "harvest_role_id": record_id * 100,
                "person_ids": [50, 51],
                "updated_by_id": 100,
                "placeholder_ids": [10, 11],
            },
        }

        base_record.update(stream_fields.get(stream_name, {}))
        return base_record

    @classmethod
    def load_schema(cls, stream_name):
        """Load the JSON schema for a given stream."""
        schema_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "tap_harvest_forecast",
            "schemas",
            f"{stream_name}.json"
        )
        with open(schema_path) as f:
            return json.load(f)

    @classmethod
    def create_catalog_entry(cls, stream_name, selected=True):
        """
        Create a CatalogEntry for testing with proper schema wrapper.

        Args:
            stream_name: Name of the stream
            selected: Whether the stream should be marked as selected

        Returns:
            A CatalogEntry object ready for use in tests
        """

        schema_dict = cls.load_schema(stream_name)
        schema_obj = Schema.from_dict(schema_dict)

        catalog_entry = CatalogEntry(
            tap_stream_id=stream_name,
            stream=stream_name,
            schema=schema_obj,
            metadata=[{"breadcrumb": [], "metadata": {"selected": selected}}]
        )
        return catalog_entry
