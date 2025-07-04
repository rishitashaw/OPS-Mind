# OpsMind GCP Deployment Guide

This guide provides step-by-step instructions for deploying OpsMind on Google Cloud Platform (GCP) using Cloud Run.

## 🏗️ Architecture Overview

OpsMind deploys on GCP with the following components:

- **Cloud Run**: Serverless container hosting for the application
- **Cloud Storage**: Storage for large datasets (8GB+)
- **Secret Manager**: Secure storage for API keys and credentials
- **Vertex AI**: Google's AI platform for Gemini models
- **Container Registry**: Docker image storage
- **Cloud Build**: CI/CD pipeline (optional)

## 📋 Prerequisites

### 1. GCP Account Setup
- Google Cloud Platform account with billing enabled
- GCP Project with appropriate permissions
- Billing account linked to the project

### 2. Required Tools
```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Install Docker
# (Instructions vary by OS - see https://docs.docker.com/get-docker/)

# Install kubectl (for Kubernetes management)
gcloud components install kubectl
```

### 3. Local Setup
```bash
# Clone your OpsMind repository
git clone <your-repo-url>
cd ops

# Make scripts executable
chmod +x *.sh
```

## 🚀 Deployment Steps

### Step 1: Initial GCP Setup

Run the GCP setup script to configure your project:

```bash
# For existing project
./setup-gcp.sh -p your-project-id

# For new project (with billing account)
./setup-gcp.sh -p your-project-id -c -b your-billing-account-id
```

**What this does:**
- Enables required APIs (Cloud Run, Vertex AI, Storage, etc.)
- Creates service accounts with appropriate permissions
- Sets up default configurations
- Creates environment template

### Step 2: Configure Environment

Edit the generated `.env` file with your configuration:

```bash
# Copy template if not already done
cp env.template .env

# Edit with your values
nano .env
```

**Required configurations:**
- `GOOGLE_CLOUD_PROJECT`: Your GCP project ID
- `GOOGLE_API_KEY`: Your Google API key for Gemini
- `GOOGLE_GENAI_USE_VERTEXAI`: Set to `TRUE` for production

**Optional configurations:**
- Jira integration settings
- Performance tuning parameters
- Debug and logging options

### Step 3: Prepare Datasets

Download and upload your datasets to Cloud Storage:

```bash
# First, download datasets from Kaggle (see README.md)
# Then upload to Cloud Storage
./upload-datasets.sh -p your-project-id
```

**Dataset Requirements:**
- Incident Event Log Dataset (44MB)
- Jira Issues Dataset (1.8GB)
- Jira Comments Dataset (3.8GB)
- Jira Changelog Dataset (2.5GB)
- Jira Issue Links Dataset (99MB)

### Step 4: Deploy Application

Run the deployment script:

```bash
# Basic deployment
./deploy.sh -p your-project-id

# Advanced deployment with custom settings
./deploy.sh -p your-project-id -r us-east1 -s my-opsmind-service
```

**What this does:**
- Builds Docker image
- Pushes to Container Registry
- Creates Cloud Run service
- Configures secrets and environment variables
- Sets up service account permissions

### Step 5: Verify Deployment

Check your deployment:

```bash
# Get service URL
gcloud run services describe opsmind --region=us-central1 --format='value(status.url)'

# Check logs
gcloud logs tail --service=opsmind

# Test health endpoint
curl https://your-service-url/health
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GOOGLE_CLOUD_PROJECT` | GCP Project ID | - | ✅ |
| `GOOGLE_API_KEY` | Gemini API Key | - | ✅ |
| `GOOGLE_GENAI_USE_VERTEXAI` | Use Vertex AI | `TRUE` | ✅ |
| `MODEL` | Gemini Model | `gemini-2.0-flash-001` | ✅ |
| `JIRA_ENABLED` | Enable Jira | `FALSE` | ❌ |
| `JIRA_BASE_URL` | Jira Instance URL | - | ❌ |
| `DATASETS_BUCKET` | Storage Bucket | `project-id-opsmind-datasets` | ✅ |

### Resource Limits

Default Cloud Run configuration:
- **CPU**: 2 vCPUs
- **Memory**: 4 GB
- **Timeout**: 300 seconds
- **Concurrency**: 10 requests
- **Max Instances**: 10

### Scaling Configuration

```yaml
# In cloud-run-service.yaml
annotations:
  autoscaling.knative.dev/maxScale: "10"
  autoscaling.knative.dev/minScale: "0"
spec:
  containerConcurrency: 10
```

## 📊 Monitoring and Observability

### Viewing Logs

```bash
# Real-time logs
gcloud logs tail --service=opsmind

# Filter by severity
gcloud logs tail --service=opsmind --filter="severity>=ERROR"

# View specific time range
gcloud logs tail --service=opsmind --since=1h
```

### Metrics and Monitoring

Access metrics in GCP Console:
1. Navigate to Cloud Run > Your Service
2. Click "Metrics" tab
3. Monitor requests, latency, errors

### Health Checks

OpsMind includes health check endpoints:
- `GET /health` - Basic health check
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

## 🔐 Security Considerations

### Service Account Permissions

The deployment creates a service account with minimal required permissions:
- `roles/aiplatform.user` - Vertex AI access
- `roles/storage.objectViewer` - Dataset access
- `roles/secretmanager.secretAccessor` - Secret access

### Network Security

- Cloud Run service allows public access by default
- Consider using Cloud Run with VPC for private access
- Implement authentication/authorization as needed

### Secrets Management

All sensitive data is stored in Secret Manager:
- Google API keys
- Jira credentials
- Database passwords

## 💰 Cost Management

### Estimated Monthly Costs

**Cloud Run (minimal usage):**
- Free tier: 2 million requests/month
- CPU: $0.00002400 per vCPU-second
- Memory: $0.00000250 per GB-second
- **Estimated**: $10-50/month for moderate usage

**Cloud Storage:**
- Standard Storage: $0.020 per GB/month
- Dataset storage (~8GB): $0.16/month
- **Estimated**: $1-5/month depending on access patterns

**Vertex AI:**
- Gemini Pro: $0.0010 per 1K input tokens
- $0.0020 per 1K output tokens
- **Estimated**: $20-100/month depending on usage

### Cost Optimization

```bash
# Monitor costs
gcloud billing accounts list
gcloud billing budgets list

# Set up billing alerts
gcloud billing budgets create \
    --billing-account=BILLING_ACCOUNT_ID \
    --display-name="OpsMind Budget" \
    --budget-amount=100 \
    --threshold-rules=percent=90,basis=CURRENT_SPEND
```

## 🛠️ Troubleshooting

### Common Issues

**1. Authentication Errors**
```bash
# Re-authenticate
gcloud auth login
gcloud auth application-default login

# Check current authentication
gcloud auth list
```

**2. Permission Denied**
```bash
# Check project permissions
gcloud projects get-iam-policy YOUR_PROJECT_ID

# Add necessary roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="user:your-email@domain.com" \
    --role="roles/run.admin"
```

**3. Container Build Failures**
```bash
# Check build logs
gcloud builds log $(gcloud builds list --limit=1 --format='value(id)')

# Test Docker build locally
docker build -t opsmind-test .
docker run -p 8080:8080 opsmind-test
```

**4. Service Deployment Issues**
```bash
# Check service status
gcloud run services describe opsmind --region=us-central1

# View deployment logs
gcloud run services logs tail opsmind --region=us-central1
```

**5. Dataset Access Problems**
```bash
# Test bucket access
gsutil ls gs://your-project-id-opsmind-datasets

# Check service account permissions
gcloud projects get-iam-policy YOUR_PROJECT_ID \
    --flatten="bindings[].members" \
    --format='value(bindings.role)' \
    --filter="bindings.members:opsmind-service-account@*"
```

### Debug Mode

Enable debug logging:
```bash
# Update service with debug environment
gcloud run services update opsmind \
    --set-env-vars DEBUG=TRUE,LOG_LEVEL=DEBUG \
    --region=us-central1
```

## 🔄 Updates and Maintenance

### Updating the Application

```bash
# Rebuild and redeploy
./deploy.sh -p your-project-id -f

# Or update specific components
gcloud run deploy opsmind \
    --image gcr.io/your-project-id/opsmind:latest \
    --region=us-central1
```

### Updating Datasets

```bash
# Upload new datasets
./upload-datasets.sh -p your-project-id

# The application will automatically use updated datasets
```

### Backup and Recovery

```bash
# Backup secrets
gcloud secrets list --format="value(name)" | \
    xargs -I {} gcloud secrets versions access latest --secret={}

# Backup bucket
gsutil -m cp -r gs://your-project-id-opsmind-datasets gs://backup-bucket
```

## 📚 Additional Resources

### Documentation
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Google Cloud Storage](https://cloud.google.com/storage/docs)

### Monitoring
- [Cloud Monitoring](https://cloud.google.com/monitoring)
- [Cloud Logging](https://cloud.google.com/logging)
- [Error Reporting](https://cloud.google.com/error-reporting)

### Support
- [Google Cloud Support](https://cloud.google.com/support)
- [Community Forums](https://googlecloudplatform.slack.com)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/google-cloud-platform)

## 🎯 Next Steps

After successful deployment:

1. **Test the Application**
   - Access the web interface
   - Run sample queries
   - Test incident processing

2. **Configure Jira Integration** (if needed)
   - Set up Jira API credentials
   - Configure project monitoring
   - Test real-time updates

3. **Set Up Monitoring**
   - Configure alerts for errors
   - Set up performance monitoring
   - Create dashboards

4. **Optimize Performance**
   - Tune resource limits
   - Optimize dataset access
   - Configure caching

5. **Security Hardening**
   - Review permissions
   - Set up authentication
   - Configure network security

---

**Need help?** Check the troubleshooting section above or refer to the main README.md for application-specific guidance. 