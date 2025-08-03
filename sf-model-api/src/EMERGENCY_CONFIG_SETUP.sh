#!/bin/bash
# EMERGENCY CONFIGURATION SETUP SCRIPT
# Incident Response: 404 Errors from Salesforce API
# Date: 2025-08-03

echo "🚨 EMERGENCY CONFIGURATION SETUP FOR MODELS-API"
echo "================================================"

# Change to project root
cd /Users/Dev/models-api/models-api-github

# Check if config.json already exists
if [ -f "config.json" ]; then
    echo "⚠️  config.json already exists. Backing up to config.json.backup"
    cp config.json config.json.backup
fi

# Copy template
echo "📋 Creating config.json from template..."
cp config/config.json.example config.json

echo "✅ config.json created successfully"
echo ""
echo "🔧 NEXT STEPS:"
echo "1. Edit config.json with your Salesforce credentials:"
echo "   - consumer_key: Your Salesforce Connected App Consumer Key"
echo "   - consumer_secret: Your Salesforce Connected App Consumer Secret"
echo "   - instance_url: Your Salesforce instance URL (e.g., https://yourorg.my.salesforce.com)"
echo ""
echo "2. Required Salesforce Setup:"
echo "   - Create Connected App in Salesforce Setup → App Manager"
echo "   - Enable OAuth Settings with 'Client Credentials Flow'"
echo "   - Grant Einstein Platform Models API permissions"
echo ""
echo "3. Test Configuration:"
echo "   cd src"
echo "   python -c \"from salesforce_models_client import SalesforceModelsClient; client = SalesforceModelsClient(); print('Token test:', len(client.get_access_token()) > 0)\""
echo ""
echo "4. Restart the models-api server after configuration"
echo ""
echo "📊 INCIDENT STATUS: Configuration template ready - awaiting credentials"