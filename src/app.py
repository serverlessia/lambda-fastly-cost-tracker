import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

# Import S3 storage module
from s3_storage import S3StorageManager

# Optional boto3 import for AWS services
try:
    import boto3

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class FastlyCostTracker:
    """Fastly Cost Tracker Lambda function to fetch usage and billing data."""

    def __init__(self):
        self.fastly_api_token = os.environ.get("FASTLY_API_TOKEN")
        self.fastly_api_base = "https://api.fastly.com"

        if not self.fastly_api_token:
            raise ValueError("FASTLY_API_TOKEN environment variable is required")

    def get_headers(self) -> Dict[str, str]:
        """Get headers for Fastly API requests."""
        return {
            "Fastly-Key": self.fastly_api_token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get_service_list(self) -> List[Dict[str, Any]]:
        """Fetch list of all Fastly services."""
        try:
            response = requests.get(
                f"{self.fastly_api_base}/service", headers=self.get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching service list: {e}")
            return []

    def get_service_details(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information about a specific service."""
        try:
            response = requests.get(
                f"{self.fastly_api_base}/service/{service_id}",
                headers=self.get_headers(),
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching service details for {service_id}: {e}")
            return None

    def get_usage_data(
        self, service_id: str, from_date: str, to_date: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch usage data for a service within a date range."""
        try:
            params = {"from": from_date, "to": to_date}
            response = requests.get(
                f"{self.fastly_api_base}/stats/service/{service_id}",
                headers=self.get_headers(),
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching usage data for {service_id}: {e}")
            return None

    def get_billing_data(self) -> Optional[Dict[str, Any]]:
        """Fetch billing information from Fastly."""
        try:
            # Note: This endpoint may require specific permissions
            response = requests.get(
                f"{self.fastly_api_base}/billing", headers=self.get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching billing data: {e}")
            return None

    def calculate_usage_metrics(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate usage metrics from Fastly API data."""
        metrics = {
            "total_bandwidth_gb": 0.0,
            "total_requests": 0,
            "datacenter_breakdown": [],
        }

        if "data" in usage_data:
            for entry in usage_data["data"]:
                if "datacenter" in entry:
                    for dc in entry["datacenter"]:
                        dc_metrics = {
                            "datacenter": dc.get("name", "Unknown"),
                            "bandwidth_gb": dc.get("bandwidth", 0)
                            / (1024**3),  # Convert bytes to GB
                            "requests": dc.get("requests", 0),
                        }
                        metrics["datacenter_breakdown"].append(dc_metrics)
                        metrics["total_bandwidth_gb"] += dc.get("bandwidth", 0) / (
                            1024**3
                        )  # Convert bytes to GB
                        metrics["total_requests"] += dc.get("requests", 0)

        return metrics

    def generate_report(
        self, from_date: str = None, to_date: str = None
    ) -> Dict[str, Any]:
        """Generate a comprehensive usage report from Fastly data."""
        logger.info("Starting Fastly usage report generation")

        # Get date range - allow override or default to last 30 days
        if from_date and to_date:
            logger.info(f"Using custom date range: {from_date} to {to_date}")
        else:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            from_date = start_date.strftime("%Y-%m-%d")
            to_date = end_date.strftime("%Y-%m-%d")
            logger.info(f"Using default date range: {from_date} to {to_date}")

        report = {
            "report_generated_at": datetime.now().isoformat(),
            "date_range": {"from": from_date, "to": to_date},
            "services": [],
            "summary": {
                "total_services": 0,
                "total_bandwidth_gb": 0,
                "total_requests": 0,
            },
        }

        # Fetch all services
        services = self.get_service_list()
        logger.info(f"Found {len(services)} services")

        for service in services:
            service_id = service.get("id")
            service_name = service.get("name", "Unknown")

            logger.info(f"Processing service: {service_name} ({service_id})")

            service_report = {
                "id": service_id,
                "name": service_name,
                "usage_data": None,
                "usage_metrics": None,
                "daily_data": [],  # New: daily breakdown
            }

            # Get usage data for this service
            usage_data = self.get_usage_data(service_id, from_date, to_date)
            if usage_data:
                service_report["usage_data"] = usage_data

                # Calculate usage metrics
                metrics = self.calculate_usage_metrics(usage_data)
                service_report["usage_metrics"] = metrics

                # Generate daily data for analytics
                daily_data = self.calculate_daily_metrics(usage_data)
                service_report["daily_data"] = daily_data

                # Update summary
                report["summary"]["total_bandwidth_gb"] += metrics["total_bandwidth_gb"]
                report["summary"]["total_requests"] += metrics["total_requests"]

            report["services"].append(service_report)
            report["summary"]["total_services"] += 1

        # Try to get billing data
        billing_data = self.get_billing_data()
        if billing_data:
            report["billing_data"] = billing_data

        logger.info(
            f"Report generated successfully. Total bandwidth: {report['summary']['total_bandwidth_gb']:.2f} GB, Total requests: {report['summary']['total_requests']:,}"
        )
        return report

    def calculate_daily_metrics(
        self, usage_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calculate daily metrics for analytics."""
        daily_data = []

        if "data" in usage_data:
            for entry in usage_data["data"]:
                # Convert timestamp to date
                start_time = entry.get("start_time", 0)
                if start_time > 0:
                    date = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d")

                    # Convert bandwidth from bytes to GB
                    bandwidth_bytes = entry.get("bandwidth", 0)
                    bandwidth_gb = bandwidth_bytes / (1024**3)

                    daily_entry = {
                        "date": date,
                        "bandwidth_gb": round(bandwidth_gb, 4),
                        "requests": entry.get("requests", 0),
                        "hits": entry.get("hits", 0),
                        "miss": entry.get("miss", 0),
                        "errors": entry.get("errors", 0),
                        "status_2xx": entry.get("status_2xx", 0),
                        "status_4xx": entry.get("status_4xx", 0),
                        "status_5xx": entry.get("status_5xx", 0),
                    }
                    daily_data.append(daily_entry)

        return daily_data

    def generate_simplified_report(
        self, from_date: str = None, to_date: str = None
    ) -> Dict[str, Any]:
        """Generate a simplified usage report with only essential metrics."""
        logger.info("Starting simplified Fastly usage report generation")

        # Get date range - allow override or default to last 30 days
        if from_date and to_date:
            logger.info(f"Using custom date range: {from_date} to {to_date}")
        else:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            from_date = start_date.strftime("%Y-%m-%d")
            to_date = end_date.strftime("%Y-%m-%d")
            logger.info(f"Using default date range: {from_date} to {to_date}")

        report = {
            "report_generated_at": datetime.now().isoformat(),
            "date_range": {"from": from_date, "to": to_date},
            "services": [],
            "summary": {
                "total_services": 0,
                "total_bandwidth_gb": 0,
                "total_requests": 0,
            },
        }

        # Fetch all services
        services = self.get_service_list()
        logger.info(f"Found {len(services)} services")

        for service in services:
            service_id = service.get("id")
            service_name = service.get("name", "Unknown")

            logger.info(f"Processing service: {service_name} ({service_id})")

            # Get usage data for this service
            usage_data = self.get_usage_data(service_id, from_date, to_date)

            service_summary = {
                "id": service_id,
                "name": service_name,
                "bandwidth_gb": 0,
                "requests": 0,
                "daily_data": [],  # New: daily breakdown
            }

            if usage_data and "data" in usage_data:
                # Calculate totals from all data entries
                total_bandwidth_bytes = 0
                total_requests = 0

                for entry in usage_data["data"]:
                    total_bandwidth_bytes += entry.get("bandwidth", 0)
                    total_requests += entry.get("requests", 0)

                # Convert bytes to GB (1 GB = 1024^3 bytes)
                total_bandwidth_gb = total_bandwidth_bytes / (1024**3)

                service_summary["bandwidth_gb"] = round(total_bandwidth_gb, 2)
                service_summary["requests"] = total_requests

                # Generate daily data for analytics
                daily_data = self.calculate_daily_metrics(usage_data)
                service_summary["daily_data"] = daily_data

                # Update summary
                report["summary"]["total_bandwidth_gb"] += total_bandwidth_gb
                report["summary"]["total_requests"] += total_requests

            report["services"].append(service_summary)
            report["summary"]["total_services"] += 1

        # Round summary totals
        report["summary"]["total_bandwidth_gb"] = round(
            report["summary"]["total_bandwidth_gb"], 2
        )

        logger.info(
            f"Simplified report generated. Total bandwidth: {report['summary']['total_bandwidth_gb']:.2f} GB, Total requests: {report['summary']['total_requests']:,}"
        )
        return report


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function for Fastly Cost Tracker.

    Args:
        event: Lambda event object with configurable parameters:
            - from_date (str): Start date in YYYY-MM-DD format (optional, defaults to 30 days ago)
            - to_date (str): End date in YYYY-MM-DD format (optional, defaults to today)
            - detailed (bool): Generate detailed report with full usage data (optional, defaults to False)
            - include_billing (bool): Include billing data if available (optional, defaults to False)
            - services (list): List of specific service IDs to include (optional, defaults to all services)
            - s3_bucket (str): S3 bucket name for storage (optional, if not provided S3 storage is disabled)
            - organization (str): Organization name for S3 hierarchy (optional, defaults to "company")
        context: Lambda context object

    Returns:
        Dict containing the usage report with daily analytics data and storage summary (if S3 enabled)
    """
    try:
        logger.info("Fastly Cost Tracker Lambda function started")

        # Initialize the cost tracker
        tracker = FastlyCostTracker()

        # Get configurable parameters from event
        from_date = event.get("from_date")
        to_date = event.get("to_date")
        detailed = event.get("detailed", False)
        include_billing = event.get("include_billing", False)
        specific_services = event.get("services", None)

        # S3 storage parameters - only enable if bucket is provided
        s3_bucket = event.get("s3_bucket")
        organization = event.get("organization", "company")
        store_to_s3 = s3_bucket is not None  # Only enable if bucket is provided

        # Log configuration
        logger.info("Configuration:")
        logger.info(
            f"  - Date range: {from_date or 'default'} to {to_date or 'default'}"
        )
        logger.info(f"  - Detailed report: {detailed}")
        logger.info(f"  - Include billing: {include_billing}")
        logger.info(f"  - Specific services: {specific_services or 'all'}")
        logger.info(f"  - S3 storage: {'enabled' if store_to_s3 else 'disabled'}")
        if store_to_s3:
            logger.info(f"  - S3 bucket: {s3_bucket}")
            logger.info(f"  - Organization: {organization}")

        # Initialize S3 storage if bucket is provided
        s3_storage = None
        if store_to_s3:
            s3_storage = S3StorageManager(s3_bucket, organization)
            logger.info("S3 storage initialized")

        if detailed:
            # Generate the detailed report
            report = tracker.generate_report(from_date, to_date)
            logger.info("Detailed report requested")
        else:
            # Generate the simplified report (default)
            report = tracker.generate_simplified_report(from_date, to_date)
            logger.info("Simplified report generated")

        # Filter services if specific services requested
        if specific_services and isinstance(specific_services, list):
            logger.info(f"Filtering to {len(specific_services)} specific services")
            filtered_services = []
            for service in report["services"]:
                if service["id"] in specific_services:
                    filtered_services.append(service)
            report["services"] = filtered_services
            report["summary"]["total_services"] = len(filtered_services)

        # Remove billing data if not requested
        if not include_billing and "billing_data" in report:
            del report["billing_data"]
            logger.info("Billing data excluded as requested")

        # Store to S3 if bucket is provided
        storage_summary = None
        if store_to_s3 and s3_storage:
            logger.info("Starting S3 storage process...")
            storage_summary = {
                "total_services": 0,
                "total_stored_days": 0,
                "total_unchanged_days": 0,
                "services": [],
            }

            for service in report["services"]:
                if service.get("daily_data"):  # Only store services with daily data
                    service_storage = s3_storage.store_service_data(
                        service, report["date_range"]
                    )
                    storage_summary["services"].append(service_storage)
                    storage_summary["total_services"] += 1
                    storage_summary["total_stored_days"] += service_storage[
                        "stored_days"
                    ]
                    storage_summary["total_unchanged_days"] += service_storage[
                        "unchanged_days"
                    ]

            report["storage_summary"] = storage_summary
            logger.info(
                f"S3 storage completed: {storage_summary['total_stored_days']} days stored, {storage_summary['total_unchanged_days']} unchanged"
            )

        # Log the report summary
        logger.info("Report Summary:")
        logger.info(f"  - Total Services: {report['summary']['total_services']}")
        logger.info(
            f"  - Total Bandwidth: {report['summary']['total_bandwidth_gb']:.2f} GB"
        )
        logger.info(f"  - Total Requests: {report['summary']['total_requests']:,}")

        # Log daily data availability
        services_with_daily_data = sum(
            1 for service in report["services"] if service.get("daily_data")
        )
        logger.info(f"  - Services with daily data: {services_with_daily_data}")

        if "billing_data" in report:
            logger.info("  - Billing data retrieved successfully")

        if storage_summary:
            logger.info(
                f"  - S3 storage: {storage_summary['total_stored_days']} days stored"
            )

        return {
            "statusCode": 200,
            "body": json.dumps(report, indent=2),
            "headers": {"Content-Type": "application/json"},
        }

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error", "message": str(e)}),
            "headers": {"Content-Type": "application/json"},
        }
