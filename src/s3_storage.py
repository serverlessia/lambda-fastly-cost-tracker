"""
S3 Storage Module for Fastly Cost Tracker

This module handles efficient storage of Fastly usage data to S3 with:
- Incremental updates (only store changed data)
- Hierarchical organization by org/service/date
- Change detection to avoid unnecessary writes
- Easy querying and management
- Handles empty buckets and previous content gracefully
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import boto3

logger = logging.getLogger(__name__)


class S3StorageManager:
    """Manages S3 storage for Fastly usage data with incremental updates."""

    def __init__(self, bucket_name: str, organization: str = "company"):
        """
        Initialize S3 storage manager.

        Args:
            bucket_name: S3 bucket name
            organization: Organization name for data hierarchy (defaults to "company")
        """
        self.bucket_name = bucket_name
        self.organization = organization
        self.s3_client = boto3.client("s3")

        # Validate bucket exists and is accessible
        self._validate_bucket_access()

    def _validate_bucket_access(self):
        """Validate that the S3 bucket exists and is accessible."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 bucket '{self.bucket_name}' is accessible")
        except self.s3_client.exceptions.NoSuchBucket:
            logger.warning(
                f"S3 bucket '{self.bucket_name}' does not exist - will be created on first write"
            )
        except Exception as e:
            logger.error(f"Error accessing S3 bucket '{self.bucket_name}': {e}")
            raise

    def _generate_s3_key(self, service_id: str, date: str) -> str:
        """
        Generate S3 key for a specific service and date.

        Args:
            service_id: Fastly service ID
            date: Date in YYYY-MM-DD format

        Returns:
            S3 key path
        """
        year, month, day = date.split("-")
        return f"fastly-data/{self.organization}/{service_id}/{year}/{month}/{day}.json"

    def _calculate_data_hash(self, data: Dict[str, Any]) -> str:
        """
        Calculate hash of data for change detection.

        Args:
            data: Data dictionary

        Returns:
            MD5 hash of data
        """
        # Create a stable representation for hashing
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()

    def _get_existing_data(
        self, service_id: str, date: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get existing data from S3 for change detection.
        Handles cases where bucket is empty or file doesn't exist.

        Args:
            service_id: Fastly service ID
            date: Date in YYYY-MM-DD format

        Returns:
            Existing data or None if not found
        """
        try:
            s3_key = self._generate_s3_key(service_id, date)
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return json.loads(response["Body"].read().decode("utf-8"))
        except self.s3_client.exceptions.NoSuchKey:
            logger.debug(f"No existing data found for {service_id} on {date}")
            return None
        except self.s3_client.exceptions.NoSuchBucket:
            logger.debug(f"Bucket '{self.bucket_name}' does not exist yet")
            return None
        except Exception as e:
            logger.error(f"Error reading existing data from S3: {e}")
            return None

    def store_daily_data(
        self, service_id: str, service_name: str, date: str, daily_data: Dict[str, Any]
    ) -> bool:
        """
        Store daily data to S3 with change detection.
        Handles empty buckets and previous content gracefully.

        Args:
            service_id: Fastly service ID
            service_name: Fastly service name
            date: Date in YYYY-MM-DD format
            daily_data: Daily usage data

        Returns:
            True if data was stored (changed), False if no change
        """
        try:
            # Prepare data structure
            data_to_store = {
                "organization": self.organization,
                "service_id": service_id,
                "service_name": service_name,
                "date": date,
                "data": {
                    **daily_data,
                    "last_updated": datetime.now().isoformat(),
                    "data_source": "fastly_api",
                },
            }

            # Check if data already exists
            existing_data = self._get_existing_data(service_id, date)

            if existing_data:
                # Compare data hashes
                existing_hash = self._calculate_data_hash(existing_data["data"])
                new_hash = self._calculate_data_hash(data_to_store["data"])

                if existing_hash == new_hash:
                    logger.info(f"No change detected for {service_id} on {date}")
                    return False
                else:
                    logger.info(f"Data changed for {service_id} on {date}, updating...")
            else:
                logger.info(f"New data for {service_id} on {date}, storing...")

            # Store to S3
            s3_key = self._generate_s3_key(service_id, date)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(data_to_store, indent=2),
                ContentType="application/json",
            )

            logger.info(f"Successfully stored data for {service_id} on {date}")
            return True

        except Exception as e:
            logger.error(f"Error storing data to S3: {e}")
            return False

    def store_service_data(
        self, service_data: Dict[str, Any], date_range: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Store all daily data for a service.
        Handles empty buckets and previous content gracefully.

        Args:
            service_data: Service data with daily_data array
            date_range: Date range used for the report

        Returns:
            Storage summary
        """
        service_id = service_data["id"]
        service_name = service_data["name"]
        daily_data_list = service_data.get("daily_data", [])

        storage_summary = {
            "service_id": service_id,
            "service_name": service_name,
            "total_days": len(daily_data_list),
            "stored_days": 0,
            "unchanged_days": 0,
            "errors": 0,
        }

        for daily_entry in daily_data_list:
            date = daily_entry["date"]

            # Remove date from daily_entry as it's stored separately
            data_to_store = {k: v for k, v in daily_entry.items() if k != "date"}

            if self.store_daily_data(service_id, service_name, date, data_to_store):
                storage_summary["stored_days"] += 1
            else:
                storage_summary["unchanged_days"] += 1

        return storage_summary

    def query_service_data(
        self, service_id: str, from_date: str, to_date: str
    ) -> List[Dict[str, Any]]:
        """
        Query stored data for a service within a date range.
        Handles empty buckets and missing data gracefully.

        Args:
            service_id: Fastly service ID
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)

        Returns:
            List of daily data entries
        """
        try:
            # Generate S3 keys for the date range
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            to_dt = datetime.strptime(to_date, "%Y-%m-%d")

            results = []
            current_dt = from_dt

            while current_dt <= to_dt:
                date_str = current_dt.strftime("%Y-%m-%d")
                s3_key = self._generate_s3_key(service_id, date_str)

                try:
                    response = self.s3_client.get_object(
                        Bucket=self.bucket_name, Key=s3_key
                    )
                    data = json.loads(response["Body"].read().decode("utf-8"))
                    results.append(data)
                except self.s3_client.exceptions.NoSuchKey:
                    logger.debug(f"No data found for {service_id} on {date_str}")
                except self.s3_client.exceptions.NoSuchBucket:
                    logger.debug(f"Bucket '{self.bucket_name}' does not exist")
                    break
                except Exception as e:
                    logger.error(
                        f"Error reading data for {service_id} on {date_str}: {e}"
                    )

                current_dt += timedelta(days=1)

            return results

        except Exception as e:
            logger.error(f"Error querying service data: {e}")
            return []

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics for the organization.
        Handles empty buckets gracefully.

        Returns:
            Storage statistics
        """
        try:
            # List objects with prefix
            prefix = f"fastly-data/{self.organization}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=prefix
            )

            stats = {
                "total_files": 0,
                "total_size_bytes": 0,
                "services": set(),
                "date_range": {"earliest": None, "latest": None},
            }

            if "Contents" in response:
                for obj in response["Contents"]:
                    stats["total_files"] += 1
                    stats["total_size_bytes"] += obj["Size"]

                    # Extract service ID from key
                    key_parts = obj["Key"].split("/")
                    if len(key_parts) >= 4:
                        stats["services"].add(key_parts[3])

                    # Track date range
                    if len(key_parts) >= 7:
                        date_str = f"{key_parts[4]}-{key_parts[5]}-{key_parts[6].replace('.json', '')}"
                        if (
                            not stats["date_range"]["earliest"]
                            or date_str < stats["date_range"]["earliest"]
                        ):
                            stats["date_range"]["earliest"] = date_str
                        if (
                            not stats["date_range"]["latest"]
                            or date_str > stats["date_range"]["latest"]
                        ):
                            stats["date_range"]["latest"] = date_str
            else:
                logger.info(
                    f"No data found in bucket '{self.bucket_name}' with prefix '{prefix}'"
                )

            # Convert set to list for JSON serialization
            stats["services"] = list(stats["services"])
            stats["total_size_mb"] = round(stats["total_size_bytes"] / (1024 * 1024), 2)

            return stats

        except self.s3_client.exceptions.NoSuchBucket:
            logger.info(f"Bucket '{self.bucket_name}' does not exist")
            return {
                "total_files": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0,
                "services": [],
                "date_range": {"earliest": None, "latest": None},
            }
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {}
