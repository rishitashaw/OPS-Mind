# OpsMind ADK Deployment Guide

Deploy your OpsMind AI agent to Google Cloud Run in minutes using ADK's built-in deployment commands.

## 🚀 Simple ADK Deployment

### Prerequisites

1. **Google Cloud SDK** installed and authenticated
2. **Google API Key** for Gemini
3. **ADK** installed (already in requirements.txt)

### Step 1: Authenticate with Google Cloud

```bash
# Login to Google Cloud
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

### Step 2: Configure Environment

Create or update your `.env` file:

```bash
# Copy the template
cp env.template .env

# Edit with your settings
cat > .env << EOF
# Core Configuration
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your_google_api_key_here
MODEL=gemini-2.0-flash-001

# Optional: Enable Vertex AI for production
# GOOGLE_GENAI_USE_VERTEXAI=TRUE
# GOOGLE_CLOUD_PROJECT=your-project-id

# Jira Integration (Optional)
JIRA_ENABLED=FALSE
JIRA_BASE_URL=https://your-company.atlassian.net
JIRA_USERNAME=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECT_KEYS=PROJ1,PROJ2
JIRA_POLL_INTERVAL=300
EOF
```

### Step 3: Test Locally (Optional)

```bash
# Run in CLI mode
adk run opsmind

# Run with web UI
adk web opsmind
```

### Step 4: Deploy to Cloud Run

```bash
# Deploy with web UI
adk deploy cloud_run --with_ui opsmind

# Or deploy without UI (API only)
adk deploy cloud_run opsmind
```

**That's it!** ADK handles all the complex deployment tasks automatically:
- ✅ Generating deployment files
- ✅ Building and pushing Docker containers
- ✅ Setting up Cloud Run services
- ✅ Providing a URL for accessing your agent

### Step 5: Make Your Service Public (Optional)

```bash
# Get your service name from deployment output
SERVICE_NAME="your-service-name"
REGION="us-central1"

# Make it publicly accessible
gcloud run services add-iam-policy-binding $SERVICE_NAME \
  --region=$REGION \
  --member="allUsers" \
  --role="roles/run.invoker"
```

## 📋 Example Deployment Output

```bash
$ adk deploy cloud_run --with_ui opsmind

Building using Dockerfile and deploying container to Cloud Run service [opsmind-service]...
✓ Building container image...
✓ Pushing to Container Registry...
✓ Deploying to Cloud Run...
✓ Deployed to https://opsmind-service-abc123456.us-central1.run.app

This service is not public. To make it public, run:
gcloud run services add-iam-policy-binding opsmind-service --region=us-central1 --member="allUsers" --role="roles/run.invoker"
```

## 🎯 Testing Your Deployment

Once deployed, you can:

1. **Web Interface**: Visit the provided URL to access the chat interface
2. **API Calls**: Send POST requests to `/chat` endpoint
3. **Health Check**: GET `/health` for service status

### Example API Usage

```bash
# Test the deployed service
curl -X POST "https://your-service-url/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Process recent incidents"}'
```

## 🔧 Advanced Configuration

### Environment Variables

You can set additional environment variables during deployment:

```bash
# Deploy with custom environment variables
adk deploy cloud_run --with_ui opsmind \
  --env GOOGLE_GENAI_USE_VERTEXAI=TRUE \
  --env GOOGLE_CLOUD_PROJECT=your-project-id
```

### Custom Resource Limits

```bash
# Deploy with custom resource limits
adk deploy cloud_run --with_ui opsmind \
  --cpu 2 \
  --memory 4Gi \
  --timeout 300
```

## 📊 Monitoring and Logs

```bash
# View service logs
gcloud run services logs tail opsmind-service

# Check service status
gcloud run services describe opsmind-service --region=us-central1
```

## 🔄 Updates and Redeployment

```bash
# Redeploy after making changes
adk deploy cloud_run --with_ui opsmind

# Or with force rebuild
adk deploy cloud_run --with_ui opsmind --force
```

## 🛠️ Troubleshooting

### Common Issues

1. **Authentication Error**: Run `gcloud auth login` again
2. **Project Not Set**: Run `gcloud config set project YOUR_PROJECT_ID`
3. **API Not Enabled**: Enable Cloud Run API in GCP Console
4. **Permission Denied**: Ensure you have Cloud Run Admin role

### Enable Required APIs

```bash
# Enable necessary APIs
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

## 💰 Cost Optimization

- **Free Tier**: 2 million requests/month
- **Auto-scaling**: Scales to zero when not in use
- **Pay-per-use**: Only pay for actual usage

## 🌐 Integration with Other Services

Your deployed OpsMind agent can integrate with:
- **Jira**: Real-time incident monitoring
- **Slack**: Notifications and alerts
- **Webhooks**: External system integration
- **APIs**: RESTful API access

---

**Resources:**
- [ADK Documentation](https://cloud.google.com/agent-development-kit)
- [Original Tutorial](https://timtech4u.medium.com/building-and-deploying-ai-agents-in-minutes-with-googles-adk-part-1-abbf2ed43486)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)

This simplified deployment approach leverages ADK's built-in capabilities, making deployment much faster and more reliable than custom scripts. 