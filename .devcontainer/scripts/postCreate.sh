#!/bin/bash
set -e

echo "🚀 Setting up Fastly Cost Tracker Lambda development environment..."

# Fix Docker credential helper issue for SAM local invoke
echo "🔧 Configuring Docker credentials..."
mkdir -p ~/.docker
echo '{"credsStore":""}' > ~/.docker/config.json
echo "✅ Docker credential helper disabled"

# Navigate to workspace
cd /workspaces/lambda-fastly-cost-tracker

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd src
pip install -r requirements.txt
cd ..

# Set executable permissions for Python files
echo "🔧 Setting permissions..."
find . -name "*.py" -type f -exec chmod +x {} \;

# Verify project structure
echo "📂 Verifying project structure..."
echo "  - SAM template: template.yaml"
ls -la template.yaml 2>/dev/null && echo "    ✅ Found" || echo "    ❌ Missing"

echo "  - Lambda function: src/app.py"
ls -la src/app.py 2>/dev/null && echo "    ✅ Found" || echo "    ❌ Missing"

echo "  - Requirements: src/requirements.txt"
ls -la src/requirements.txt 2>/dev/null && echo "    ✅ Found" || echo "    ❌ Missing"

# Check SAM CLI
echo "  - SAM CLI:"
if command -v sam &> /dev/null; then
    echo "    ✅ SAM CLI available"
    sam --version
else
    echo "    ❌ SAM CLI not found - install with 'pip install aws-sam-cli'"
fi

# Check AWS CLI
echo "  - AWS CLI:"
if command -v aws &> /dev/null; then
    echo "    ✅ AWS CLI available"
    aws --version
else
    echo "    ❌ AWS CLI not found - install with 'pip install awscli'"
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Configure AWS credentials: 'aws configure'"
echo "  2. Set your Fastly API token as an environment variable:"
echo "     export FASTLY_API_TOKEN='your_token_here'"
echo "  3. Build the application: 'sam build'"
echo "  4. Deploy locally: 'sam local invoke FastlyCostTrackerFunction'"
echo "  5. Deploy to AWS: 'sam deploy --guided'"
echo ""
echo "📚 Useful commands:"
echo "  - 'sam build' - Build the Lambda function"
echo "  - 'sam local invoke FastlyCostTrackerFunction' - Test locally"
echo "  - 'sam deploy --guided' - Deploy to AWS"
echo "  - 'aws logs tail /aws/lambda/fastly-cost-tracker' - View logs"
