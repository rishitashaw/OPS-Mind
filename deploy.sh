#!/bin/bash

# OpsMind GCP Deployment Script
# This script builds, pushes, and deploys the OpsMind application to Cloud Run

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PROJECT_ID=""
REGION="us-central1"
SERVICE_NAME="opsmind"
IMAGE_NAME="opsmind"
FORCE_REBUILD=false
SKIP_SECRETS=false

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage function
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy OpsMind to Google Cloud Run

OPTIONS:
    -p, --project-id PROJECT_ID    GCP Project ID (required)
    -r, --region REGION           GCP Region (default: us-central1)
    -s, --service-name NAME       Cloud Run service name (default: opsmind)
    -i, --image-name NAME         Docker image name (default: opsmind)
    -f, --force-rebuild          Force rebuild of Docker image
    --skip-secrets               Skip secrets setup (use existing secrets)
    -h, --help                   Show this help message

EXAMPLES:
    $0 -p my-project-id
    $0 -p my-project-id -r us-east1 -f
    $0 -p my-project-id --skip-secrets

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--project-id)
            PROJECT_ID="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -s|--service-name)
            SERVICE_NAME="$2"
            shift 2
            ;;
        -i|--image-name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -f|--force-rebuild)
            FORCE_REBUILD=true
            shift
            ;;
        --skip-secrets)
            SKIP_SECRETS=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$PROJECT_ID" ]]; then
    print_error "Project ID is required. Use -p or --project-id"
    usage
    exit 1
fi

# Check if required tools are installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    local missing_tools=()
    
    if ! command -v gcloud &> /dev/null; then
        missing_tools+=("gcloud")
    fi
    
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    fi
    
    if ! command -v kubectl &> /dev/null; then
        missing_tools+=("kubectl")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_error "Please install them and try again"
        exit 1
    fi
    
    print_success "All dependencies are installed"
}

# Authenticate with GCP
authenticate_gcp() {
    print_status "Authenticating with GCP..."
    
    # Check if already authenticated
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
        print_success "Already authenticated with GCP"
    else
        print_status "Please authenticate with GCP..."
        gcloud auth login
    fi
    
    # Set project
    gcloud config set project "$PROJECT_ID"
    print_success "Project set to: $PROJECT_ID"
}

# Enable required APIs
enable_apis() {
    print_status "Enabling required GCP APIs..."
    
    local apis=(
        "cloudbuild.googleapis.com"
        "run.googleapis.com"
        "containerregistry.googleapis.com"
        "artifactregistry.googleapis.com"
        "aiplatform.googleapis.com"
        "storage.googleapis.com"
        "secretmanager.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        print_status "Enabling $api..."
        gcloud services enable "$api" --project="$PROJECT_ID"
    done
    
    print_success "All required APIs enabled"
}

# Create service account
create_service_account() {
    print_status "Creating service account..."
    
    local sa_name="opsmind-service-account"
    local sa_email="$sa_name@$PROJECT_ID.iam.gserviceaccount.com"
    
    # Check if service account exists
    if gcloud iam service-accounts describe "$sa_email" --project="$PROJECT_ID" &> /dev/null; then
        print_success "Service account already exists: $sa_email"
    else
        gcloud iam service-accounts create "$sa_name" \
            --display-name="OpsMind Service Account" \
            --description="Service account for OpsMind application" \
            --project="$PROJECT_ID"
        print_success "Created service account: $sa_email"
    fi
    
    # Grant necessary roles
    local roles=(
        "roles/aiplatform.user"
        "roles/storage.objectViewer"
        "roles/secretmanager.secretAccessor"
        "roles/cloudsql.client"
    )
    
    for role in "${roles[@]}"; do
        print_status "Granting role $role to service account..."
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$sa_email" \
            --role="$role" \
            --quiet
    done
    
    print_success "Service account configured with necessary permissions"
}

# Create Cloud Storage bucket for datasets
create_storage_bucket() {
    print_status "Creating Cloud Storage bucket for datasets..."
    
    local bucket_name="$PROJECT_ID-opsmind-datasets"
    
    # Check if bucket exists
    if gsutil ls -b "gs://$bucket_name" &> /dev/null; then
        print_success "Bucket already exists: $bucket_name"
    else
        gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://$bucket_name"
        print_success "Created bucket: $bucket_name"
    fi
    
    # Set bucket permissions
    gsutil iam ch serviceAccount:opsmind-service-account@$PROJECT_ID.iam.gserviceaccount.com:objectViewer "gs://$bucket_name"
    
    print_warning "Remember to upload your datasets to gs://$bucket_name"
    print_status "Dataset upload instructions:"
    echo "  1. Download datasets from Kaggle (see README.md)"
    echo "  2. Upload to bucket: gsutil -m cp -r ./opsmind/data/datasets/* gs://$bucket_name/"
}

# Setup secrets
setup_secrets() {
    if [[ "$SKIP_SECRETS" == "true" ]]; then
        print_status "Skipping secrets setup as requested"
        return 0
    fi
    
    print_status "Setting up secrets..."
    
    # Read environment variables or prompt for values
    if [[ -z "$GOOGLE_API_KEY" ]]; then
        read -p "Enter your Google API Key: " -s GOOGLE_API_KEY
        echo
    fi
    
    # Create secrets
    print_status "Creating Google API Key secret..."
    echo -n "$GOOGLE_API_KEY" | gcloud secrets create google-api-key --data-file=- --project="$PROJECT_ID" 2>/dev/null || \
    echo -n "$GOOGLE_API_KEY" | gcloud secrets versions add google-api-key --data-file=- --project="$PROJECT_ID"
    
    # Optional Jira secrets
    if [[ -n "$JIRA_BASE_URL" ]] && [[ -n "$JIRA_USERNAME" ]] && [[ -n "$JIRA_API_TOKEN" ]]; then
        print_status "Creating Jira secrets..."
        echo -n "$JIRA_BASE_URL" | gcloud secrets create jira-base-url --data-file=- --project="$PROJECT_ID" 2>/dev/null || \
        echo -n "$JIRA_BASE_URL" | gcloud secrets versions add jira-base-url --data-file=- --project="$PROJECT_ID"
        
        echo -n "$JIRA_USERNAME" | gcloud secrets create jira-username --data-file=- --project="$PROJECT_ID" 2>/dev/null || \
        echo -n "$JIRA_USERNAME" | gcloud secrets versions add jira-username --data-file=- --project="$PROJECT_ID"
        
        echo -n "$JIRA_API_TOKEN" | gcloud secrets create jira-api-token --data-file=- --project="$PROJECT_ID" 2>/dev/null || \
        echo -n "$JIRA_API_TOKEN" | gcloud secrets versions add jira-api-token --data-file=- --project="$PROJECT_ID"
    fi
    
    print_success "Secrets configured"
}

# Build and push Docker image
build_and_push() {
    print_status "Building and pushing Docker image..."
    
    local image_url="gcr.io/$PROJECT_ID/$IMAGE_NAME:latest"
    
    # Build image
    print_status "Building Docker image..."
    docker build -t "$image_url" .
    
    # Push to Container Registry
    print_status "Pushing image to Container Registry..."
    docker push "$image_url"
    
    print_success "Image pushed: $image_url"
}

# Create ConfigMap and Secrets for Kubernetes
create_k8s_configs() {
    print_status "Creating Kubernetes configurations..."
    
    # Create ConfigMap
    kubectl create configmap opsmind-config \
        --from-literal=project_id="$PROJECT_ID" \
        --from-literal=jira_enabled="FALSE" \
        --from-literal=jira_project_keys="" \
        --from-literal=datasets_bucket="$PROJECT_ID-opsmind-datasets" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Create Secret references
    kubectl create secret generic opsmind-secrets \
        --from-literal=google_api_key="$(gcloud secrets versions access latest --secret=google-api-key --project=$PROJECT_ID)" \
        --from-literal=jira_base_url="" \
        --from-literal=jira_username="" \
        --from-literal=jira_api_token="" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    print_success "Kubernetes configurations created"
}

# Deploy to Cloud Run
deploy_to_cloud_run() {
    print_status "Deploying to Cloud Run..."
    
    local image_url="gcr.io/$PROJECT_ID/$IMAGE_NAME:latest"
    
    # Update the service YAML with the actual project ID
    sed "s/PROJECT_ID/$PROJECT_ID/g" cloud-run-service.yaml > cloud-run-service-deploy.yaml
    
    # Deploy using gcloud
    gcloud run deploy "$SERVICE_NAME" \
        --image "$image_url" \
        --platform managed \
        --region "$REGION" \
        --allow-unauthenticated \
        --port 8080 \
        --cpu 2 \
        --memory 4Gi \
        --timeout 300 \
        --concurrency 10 \
        --max-instances 10 \
        --min-instances 0 \
        --service-account "opsmind-service-account@$PROJECT_ID.iam.gserviceaccount.com" \
        --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_GENAI_USE_VERTEXAI=TRUE,MODEL=gemini-2.0-flash-001,JIRA_ENABLED=FALSE,JIRA_POLL_INTERVAL=300,DATASETS_BUCKET=$PROJECT_ID-opsmind-datasets" \
        --set-secrets "GOOGLE_API_KEY=google-api-key:latest" \
        --project "$PROJECT_ID"
    
    # Get the service URL
    local service_url=$(gcloud run services describe "$SERVICE_NAME" --platform managed --region "$REGION" --format 'value(status.url)' --project "$PROJECT_ID")
    
    print_success "Deployment completed!"
    print_success "Service URL: $service_url"
    
    # Cleanup temporary file
    rm -f cloud-run-service-deploy.yaml
}

# Main deployment function
main() {
    print_status "Starting OpsMind deployment to GCP..."
    print_status "Project: $PROJECT_ID"
    print_status "Region: $REGION"
    print_status "Service: $SERVICE_NAME"
    echo
    
    check_dependencies
    authenticate_gcp
    enable_apis
    create_service_account
    create_storage_bucket
    setup_secrets
    build_and_push
    deploy_to_cloud_run
    
    print_success "🚀 OpsMind has been successfully deployed to GCP!"
    print_status "Next steps:"
    echo "  1. Upload your datasets to the Cloud Storage bucket"
    echo "  2. Configure Jira integration if needed"
    echo "  3. Monitor the application logs: gcloud logs tail --service=$SERVICE_NAME"
    echo "  4. Access your application at the service URL shown above"
}

# Run main function
main "$@" 