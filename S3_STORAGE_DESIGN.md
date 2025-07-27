# S3 Storage Design for Fastly Cost Tracker

## 🏗️ Overview

This document describes the S3 storage architecture for the Fastly Cost Tracker Lambda function, designed for efficient data management and analytics.

## 📊 Data Structure

### S3 Key Pattern

```plaintext
fastly-data/{organization}/{service_id}/{year}/{month}/{date}.json
```

**Example:**

```plaintext
fastly-data/acme-corp/service-123/2025/07/27.json
```

### Individual File Structure

```json
{
  "organization": "acme-corp",
  "service_id": "service-123",
  "service_name": "api.example.com",
  "date": "2025-07-27",
  "data": {
    "bandwidth_gb": 45.2,
    "requests": 45000,
    "hits": 44000,
    "miss": 1000,
    "errors": 50,
    "status_2xx": 44000,
    "status_4xx": 800,
    "status_5xx": 200,
    "last_updated": "2025-07-27T10:30:00Z",
    "data_source": "fastly_api"
  }
}
```

## 🎯 Key Features

### 1. **Incremental Updates**

- Only stores data when it has changed
- Uses MD5 hash comparison for change detection
- Avoids unnecessary S3 writes
- Reduces storage costs and API calls

### 2. **Hierarchical Organization**

- Organized by organization → service → year → month → date
- Easy to query specific date ranges
- Efficient for analytics and reporting
- Natural backup and lifecycle management

### 3. **Daily Granularity**

- One file per service per day
- Perfect for time-series analytics
- Easy to aggregate data for different time periods
- Supports trend analysis and forecasting

### 4. **Change Detection**

```python
# Example change detection logic
existing_hash = calculate_hash(existing_data)
new_hash = calculate_hash(new_data)
if existing_hash != new_hash:
    store_to_s3()  # Only store if changed
```

### 5. **Flexible S3 Configuration**

- S3 storage is **automatically enabled** when `s3_bucket` is provided
- **No S3 storage** when `s3_bucket` is not provided
- Handles **empty buckets** and **previous content** gracefully
- **Bucket validation** on initialization

## 📈 Usage Patterns

### 1. **Daily Data Collection (with S3)**

```json
{
  "from_date": "2025-07-27",
  "to_date": "2025-07-27",
  "s3_bucket": "my-fastly-data-bucket",
  "organization": "acme-corp"
}
```

### 2. **Historical Data Backfill (with S3)**

```json
{
  "from_date": "2025-07-01",
  "to_date": "2025-07-31",
  "s3_bucket": "my-fastly-data-bucket",
  "organization": "acme-corp"
}
```

### 3. **Service-Specific Storage (with S3)**

```json
{
  "from_date": "2025-07-20",
  "to_date": "2025-07-27",
  "services": ["service-123"],
  "s3_bucket": "my-fastly-data-bucket",
  "organization": "acme-corp"
}
```

### 4. **Report Only (no S3 storage)**

```json
{
  "from_date": "2025-07-20",
  "to_date": "2025-07-27",
  "detailed": false
}
```

## 🔧 Configuration Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `s3_bucket` | string | No | - | S3 bucket name (enables S3 storage if provided) |
| `organization` | string | No | "company" | Organization name for hierarchy |
| `from_date` | string | No | 30 days ago | Start date (YYYY-MM-DD) |
| `to_date` | string | No | today | End date (YYYY-MM-DD) |
| `services` | array | No | all services | Specific service IDs to process |
| `detailed` | boolean | No | false | Generate detailed report |
| `include_billing` | boolean | No | false | Include billing data |

## 📊 Storage Summary Response

When S3 storage is enabled (s3_bucket provided), the response includes a storage summary:

```json
{
  "storage_summary": {
    "total_services": 2,
    "total_stored_days": 14,
    "total_unchanged_days": 0,
    "services": [
      {
        "service_id": "service-123",
        "service_name": "api.example.com",
        "total_days": 7,
        "stored_days": 7,
        "unchanged_days": 0
      }
    ]
  }
}
```

## 🗂️ S3 Organization Benefits

### 1. **Easy Querying**

```plaintext
# Query specific service for a month
fastly-data/acme-corp/service-123/2025/07/*.json

# Query all services for a date
fastly-data/acme-corp/*/2025/07/27.json

# Query organization for a date range
fastly-data/acme-corp/*/2025/07/*.json
```

### 2. **Lifecycle Management**

- Easy to set different retention policies
- Archive old data to Glacier
- Delete data older than X days
- Cost optimization strategies

### 3. **Backup and Recovery**

- Natural backup structure
- Easy to restore specific date ranges
- Cross-region replication support
- Version control capabilities

## 💡 Analytics Use Cases

### 1. **Daily Trends**

```python
# Query daily data for trend analysis
daily_data = s3_storage.query_service_data(
    service_id="service-123",
    from_date="2025-07-01",
    to_date="2025-07-31"
)
```

### 2. **Monthly Aggregations**

```python
# Aggregate daily data into monthly summaries
monthly_data = aggregate_daily_to_monthly(daily_data)
```

### 3. **Service Comparisons**

```python
# Compare multiple services
services_data = []
for service_id in service_ids:
    data = s3_storage.query_service_data(service_id, from_date, to_date)
    services_data.append(data)
```

## 🔒 Security Considerations

### 1. **IAM Permissions**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-fastly-data-bucket",
        "arn:aws:s3:::my-fastly-data-bucket/*"
      ]
    }
  ]
}
```

### 2. **Bucket Policy**

- Enable server-side encryption
- Configure access logging
- Set up cross-region replication
- Implement lifecycle policies

## 📈 Cost Optimization

### 1. **Storage Classes**

- **Standard**: Recent data (frequently accessed)
- **IA**: Older data (infrequently accessed)
- **Glacier**: Historical data (rarely accessed)

### 2. **Lifecycle Policies**

```json
{
  "Rules": [
    {
      "ID": "Move to IA after 30 days",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        }
      ]
    },
    {
      "ID": "Move to Glacier after 90 days",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
```

## 🚀 Implementation Example

### 1. **Lambda Function Call (with S3)**

```bash
sam local invoke --event event-s3-storage.json
```

### 2. **Lambda Function Call (report only)**

```bash
sam local invoke --event event-simple.json
```

### 3. **Expected Output (with S3)**

```json
{
  "statusCode": 200,
  "body": {
    "report_generated_at": "2025-07-27T10:30:00Z",
    "date_range": {
      "from": "2025-07-20",
      "to": "2025-07-27"
    },
    "services": [...],
    "summary": {...},
    "storage_summary": {
      "total_services": 2,
      "total_stored_days": 14,
      "total_unchanged_days": 0,
      "services": [...]
    }
  }
}
```

## 🔄 S3 Storage Logic

### **Automatic S3 Detection:**

```python
# S3 storage is automatically enabled when bucket is provided
s3_bucket = event.get("s3_bucket")
store_to_s3 = s3_bucket is not None  # True if bucket provided, False otherwise
```

### **Graceful Handling:**

- **Empty buckets**: Creates files on first write
- **Missing files**: Logs debug messages, continues processing
- **Access errors**: Logs errors, continues with report generation
- **Previous content**: Compares hashes, only updates if changed

This design provides a robust, scalable, and cost-effective solution for storing and managing Fastly usage data for analytics and reporting purposes.
