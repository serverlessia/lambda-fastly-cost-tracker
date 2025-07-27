# Fastly Cost Tracker Lambda

A serverless AWS Lambda function that fetches Fastly usage data and provides comprehensive analytics with optional S3 storage. Perfect for monitoring, analyzing, and storing your Fastly CDN usage data for cost optimization and trend analysis.

## Features

- **📊 Daily Analytics**: Provides daily granular data for trend analysis
- **🗂️ S3 Storage**: Optional S3 storage with incremental updates and change detection
- **🎛️ Configurable Parameters**: Flexible date ranges, service filtering, and storage options
- **📈 Comprehensive Reporting**: Detailed usage breakdowns for all services
- **🔄 Incremental Updates**: Only stores data when it has changed (cost efficient)
- **🔍 Query Capabilities**: Easy data retrieval for analytics and reporting
- **REST API**: Manual invocation endpoint for on-demand reports
- **CloudWatch Integration**: Full logging and monitoring capabilities
- **SAR Compatible**: Ready for AWS Serverless Application Repository deployment

## Architecture

```plaintext
┌──────────────────┐    ┌─────────────────┐
│   Lambda         │───▶│   Fastly API    │
│   Function       │    │   (External)    │
└──────────────────┘    └─────────────────┘
         │
         ▼
┌──────────────────┐
│   S3 Storage     │
│   (Optional)     │
└──────────────────┘
         │
         ▼
┌──────────────────┐
│   CloudWatch     │
│   Logs           │
└──────────────────┘
```

The Lambda function can be invoked manually or integrated with other AWS services as needed.

## Prerequisites

1. **AWS Account**: Active AWS account with appropriate permissions
2. **Fastly API Token**: Valid Fastly API token with read permissions
3. **AWS CLI & SAM CLI**: For local development and deployment
4. **S3 Bucket** (Optional): For data storage and analytics

## Installation

### Option 1: Deploy via AWS Serverless Application Repository (Recommended)

1. Navigate to the [AWS Serverless Application Repository](https://serverlessrepo.aws.amazon.com/applications)
2. Search for "Fastly Cost Tracker"
3. Click "Deploy" and provide your Fastly API token
4. The application will be deployed with all necessary resources

### Option 2: Deploy via SAM CLI

1. **Clone the repository**:

   ```bash
   git clone https://github.com/serverlessia/lambda-fastly-cost-tracker.git
   cd lambda-fastly-cost-tracker
   ```

2. **Build the application**:

   ```bash
   sam build
   ```

3. **Deploy the application**:

   ```bash
   sam deploy --guided
   ```

   During deployment, you'll be prompted for:
   - Stack name
   - AWS Region
   - FastlyApiToken parameter

### Option 3: Deploy via CloudFormation

1. **Package the application**:

   ```bash
   sam package --output-template-file packaged.yaml --s3-bucket YOUR-S3-BUCKET
   ```

2. **Deploy using CloudFormation**:

   ```bash
   aws cloudformation deploy \
     --template-file packaged.yaml \
     --stack-name fastly-cost-tracker \
     --parameter-overrides FastlyApiToken=YOUR_FASTLY_TOKEN \
     --capabilities CAPABILITY_IAM
   ```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `FASTLY_API_TOKEN` | Fastly API token for authentication | Yes |

### Fastly API Token Setup

1. Log into your Fastly account
2. Navigate to Account → API Tokens
3. Create a new token with the following permissions:
   - `global:read` - For service listing
   - `stats:read` - For usage statistics
   - `billing:read` - For billing information (optional)

### S3 Permissions (Required for S3 Storage)

If you plan to use S3 storage, ensure your Lambda function has the following IAM permissions:

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
        "arn:aws:s3:::YOUR-S3-BUCKET-NAME",
        "arn:aws:s3:::YOUR-S3-BUCKET-NAME/*"
      ]
    }
  ]
}
```

## Usage

### Invocation Parameters

The Lambda function accepts the following parameters:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `s3_bucket` | string | No | - | S3 bucket name (enables S3 storage if provided) |
| `organization` | string | No | "company" | Organization name for S3 hierarchy |
| `from_date` | string | No | 30 days ago | Start date (YYYY-MM-DD) |
| `to_date` | string | No | today | End date (YYYY-MM-DD) |
| `services` | array | No | all services | Specific service IDs to process |
| `detailed` | boolean | No | false | Generate detailed report |
| `include_billing` | boolean | No | false | Include billing data |

### Invocation Examples

#### Basic Report (No S3 Storage)

```bash
aws lambda invoke \
  --function-name fastly-cost-tracker \
  --payload '{"from_date": "2025-07-20", "to_date": "2025-07-27"}' \
  response.json
```

#### Report with S3 Storage

```bash
aws lambda invoke \
  --function-name fastly-cost-tracker \
  --payload '{
    "from_date": "2025-07-20",
    "to_date": "2025-07-27",
    "s3_bucket": "my-fastly-data-bucket",
    "organization": "acme-corp"
  }' \
  response.json
```

#### Service-Specific Report

```bash
aws lambda invoke \
  --function-name fastly-cost-tracker \
  --payload '{
    "from_date": "2025-07-20",
    "to_date": "2025-07-27",
    "services": ["service-123", "service-456"],
    "s3_bucket": "my-fastly-data-bucket"
  }' \
  response.json
```

### Local Testing

```bash
# Test basic report
sam local invoke --event event-simple.json

# Test with S3 storage
sam local invoke --event event-s3-storage.json
```

## Output Format

The function returns a comprehensive JSON report with daily analytics data:

```json
{
  "report_generated_at": "2025-07-27T10:30:00Z",
  "date_range": {
    "from": "2025-07-20",
    "to": "2025-07-27"
  },
  "services": [
    {
      "id": "service-123",
      "name": "api.example.com",
      "bandwidth_gb": 1024.5,
      "requests": 1000000,
      "daily_data": [
        {
          "date": "2025-07-20",
          "bandwidth_gb": 145.2,
          "requests": 145000,
          "hits": 140000,
          "miss": 5000,
          "errors": 50,
          "status_2xx": 140000,
          "status_4xx": 4000,
          "status_5xx": 1000
        }
      ]
    }
  ],
  "summary": {
    "total_services": 3,
    "total_bandwidth_gb": 2048.5,
    "total_requests": 2000000
  },
  "storage_summary": {
    "total_services": 2,
    "total_stored_days": 14,
    "total_unchanged_days": 0,
    "services": [...]
  }
}
```

## S3 Storage Structure

When S3 storage is enabled, data is organized hierarchically:

```plaintext
fastly-data/{organization}/{service_id}/{year}/{month}/{date}.json
```

**Example:**

```plaintext
fastly-data/acme-corp/service-123/2025/07/27.json
```

### S3 Storage Features

- **Incremental Updates**: Only stores data when it has changed
- **Change Detection**: Uses MD5 hash comparison to avoid unnecessary writes
- **Daily Granularity**: One file per service per day for analytics
- **Hierarchical Organization**: Easy to query specific date ranges
- **Graceful Handling**: Works with empty buckets and previous content

## Cost Estimation

The function retrieves actual usage data from Fastly and provides comprehensive reporting. For accurate cost information, the function:

- **Fetches real usage data** from Fastly API
- **Provides daily analytics** for trend analysis
- **Stores data incrementally** to S3 (when enabled)
- **Reports bandwidth, requests, and other metrics** without cost estimates

*Note: For precise cost calculations, refer to your Fastly billing dashboard and pricing documentation. This tool focuses on usage data collection and reporting.*

## Development

### Local Development

1. **Install dependencies**:

   ```bash
   cd src
   pip install -r requirements.txt
   ```

2. **Set environment variable**:

   ```bash
   export FASTLY_API_TOKEN=your_token_here
   ```

3. **Test locally**:

   ```bash
   python -c "from app import lambda_handler; print(lambda_handler({}, {}))"
   ```

### Testing

```bash
# Run SAM local invoke
sam local invoke FastlyCostTrackerFunction --event event-simple.json

# Test S3 storage (requires valid S3 bucket)
sam local invoke FastlyCostTrackerFunction --event event-s3-storage.json

# Run SAM local start-api (for API Gateway testing)
sam local start-api
```

## Monitoring and Troubleshooting

### CloudWatch Metrics

Monitor the following metrics:

- **Duration**: Function execution time
- **Errors**: Failed invocations
- **Throttles**: Rate limiting issues
- **Memory Usage**: Resource utilization

### Common Issues

1. **Authentication Errors**: Verify your Fastly API token has correct permissions
2. **S3 Access Errors**: Check IAM permissions for S3 bucket access
3. **Timeout Errors**: Increase the Lambda timeout for large service portfolios
4. **Memory Errors**: Increase memory allocation for complex reports

## Security

- API tokens are stored as encrypted environment variables
- All API calls use HTTPS
- S3 data is encrypted at rest (when enabled)
- CloudWatch logs are encrypted at rest
- IAM roles follow the principle of least privilege

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:

- Create an issue on GitHub
- Check CloudWatch logs for detailed error information
- Verify Fastly API token permissions
- Check S3 bucket permissions if using storage features

## Changelog

### v1.0.0

- Initial release with S3 storage functionality and incremental updates
- Implemented daily analytics data for trend analysis
- Added configurable parameters (date ranges, service filtering)
- Enhanced error handling for empty buckets and previous content
- Comprehensive reporting with detailed usage breakdowns
- REST API endpoint for on-demand reports
- CloudWatch integration for monitoring
- SAR compatibility for easy deployment
