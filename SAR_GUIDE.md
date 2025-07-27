# Automated SAR Publishing

This project automatically publishes to the AWS Serverless Application Repository (SAR) when you create a GitHub release.

## How It Works

1. **Create a GitHub Release**: Tag a new version (e.g., `v1.0.0`)
2. **Automated Build & Publish**: GitHub Actions builds and publishes to SAR
3. **Available on SAR**: Users can deploy from the SAR console

**Note**: The workflow builds on every push/PR, but only publishes to SAR on releases.

## Required Secrets

Set these secrets in your GitHub repository:

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS access key with SAR permissions |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |

## Publishing Process

### 1. Create a Release

```bash
# Tag a new version
git tag v1.0.0
git push origin v1.0.0

# Or create via GitHub UI
# Go to Releases → Create a new release
```

### 2. Automated Steps

The workflow automatically:

- ✅ Builds the SAM application
- ✅ Creates SAR package
- ✅ Uploads to GitHub release
- ✅ Publishes to SAR using GitHub URLs
- ✅ Creates new version

### 3. Verify Publication

1. Check [SAR Applications](https://serverlessrepo.aws.amazon.com/applications)
2. Search for "fastly-cost-tracker"
3. Verify the new version is available

## IAM Permissions

The AWS credentials need these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "serverlessrepo:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## Version Management

- Use semantic versioning: `v1.0.0`, `v1.0.1`, `v1.1.0`
- Each release creates a new SAR version
- Previous versions remain available

## Troubleshooting

### Common Issues

1. **Missing Secrets**: Ensure all required secrets are set
2. **S3 Permissions**: Verify S3 bucket is accessible
3. **SAR Permissions**: Check IAM permissions for SAR
4. **Version Conflicts**: Ensure version doesn't already exist

### Debugging

- Check GitHub Actions logs for detailed error messages
- Verify AWS credentials have correct permissions
- Test S3 bucket access manually
- Review SAR console for application status
