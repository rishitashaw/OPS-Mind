#!/bin/bash

# GCP Project Setup Script for OpsMind
# This script sets up the initial GCP project configuration

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
BILLING_ACCOUNT=""
CREATE_PROJECT=false

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

Set up GCP project for OpsMind deployment

OPTIONS:
    -p, --project-id PROJECT_ID    GCP Project ID (required)
    -r, --region REGION           GCP Region (default: us-central1)
    -b, --billing-account ACCOUNT Billing account ID (required for new projects)
    -c, --create-project          Create new project
    -h, --help                   Show this help message

EXAMPLES:
    $0 -p my-opsmind-project
    $0 -p my-opsmind-project -c -b 123456-789ABC-DEF012
    $0 -p my-opsmind-project -r us-east1

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
        -b|--billing-account)
            BILLING_ACCOUNT="$2"
            shift 2
            ;;
        -c|--create-project)
            CREATE_PROJECT=true
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

if [[ "$CREATE_PROJECT" == "true" ]] && [[ -z "$BILLING_ACCOUNT" ]]; then
    print_error "Billing account is required when creating a new project. Use -b or --billing-account"
    usage
    exit 1
fi

# Check if gcloud is installed
check_gcloud() {
    print_status "Checking gcloud installation..."
    
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed"
        print_error "Please install it from: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    print_success "gcloud CLI is installed"
}

# Authenticate with GCP
authenticate_gcp() {
    print_status "Authenticating with GCP..."
    
    # Check if already authenticated
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
        print_success "Already authenticated with GCP"
        current_account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
        print_status "Current account: $current_account"
    else
        print_status "Please authenticate with GCP..."
        gcloud auth login
        gcloud auth application-default login
    fi
}

# List available billing accounts
list_billing_accounts() {
    print_status "Available billing accounts:"
    gcloud billing accounts list --format="table(displayName,name,open)" || {
        print_warning "Could not list billing accounts. Please ensure you have billing permissions."
        return 1
    }
}

# Create new project if requested
create_project() {
    if [[ "$CREATE_PROJECT" != "true" ]]; then
        return 0
    fi
    
    print_status "Creating new project: $PROJECT_ID"
    
    # Check if project already exists
    if gcloud projects describe "$PROJECT_ID" &> /dev/null; then
        print_warning "Project $PROJECT_ID already exists. Skipping creation."
        return 0
    fi
    
    # Create project
    gcloud projects create "$PROJECT_ID" --name="OpsMind Project"
    
    # Link billing account
    if [[ -n "$BILLING_ACCOUNT" ]]; then
        print_status "Linking billing account: $BILLING_ACCOUNT"
        gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT"
    fi
    
    print_success "Project created: $PROJECT_ID"
}

# Set current project
set_project() {
    print_status "Setting current project to: $PROJECT_ID"
    gcloud config set project "$PROJECT_ID"
    print_success "Current project set to: $PROJECT_ID"
}

# Check project permissions
check_permissions() {
    print_status "Checking project permissions..."
    
    local required_permissions=(
        "cloudbuild.builds.create"
        "run.services.create"
        "storage.buckets.create"
        "secretmanager.secrets.create"
        "iam.serviceAccounts.create"
        "serviceusage.services.enable"
    )
    
    local missing_permissions=()
    
    for permission in "${required_permissions[@]}"; do
        if ! gcloud projects get-iam-policy "$PROJECT_ID" --flatten="bindings[].members" --format="value(bindings.role)" | grep -q "$(gcloud iam roles describe roles/owner --format="value(name)")" 2>/dev/null; then
            # Check specific permission
            if ! gcloud projects test-iam-permissions "$PROJECT_ID" --permissions="$permission" --format="value(permissions)" | grep -q "$permission" 2>/dev/null; then
                missing_permissions+=("$permission")
            fi
        fi
    done
    
    if [[ ${#missing_permissions[@]} -gt 0 ]]; then
        print_warning "Missing some permissions. You may need to request these from your GCP administrator:"
        for permission in "${missing_permissions[@]}"; do
            echo "  - $permission"
        done
        print_warning "Deployment may fail if you don't have sufficient permissions."
    else
        print_success "All required permissions are available"
    fi
}

# Enable required APIs
enable_apis() {
    print_status "Enabling required APIs..."
    
    local apis=(
        "cloudbuild.googleapis.com"
        "run.googleapis.com"
        "containerregistry.googleapis.com"
        "artifactregistry.googleapis.com"
        "aiplatform.googleapis.com"
        "storage.googleapis.com"
        "secretmanager.googleapis.com"
        "logging.googleapis.com"
        "monitoring.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        print_status "Enabling $api..."
        gcloud services enable "$api" --project="$PROJECT_ID" || {
            print_error "Failed to enable $api"
            exit 1
        }
    done
    
    print_success "All required APIs enabled"
}

# Set up default configuration
setup_defaults() {
    print_status "Setting up default configuration..."
    
    # Set default region
    gcloud config set compute/region "$REGION"
    gcloud config set run/region "$REGION"
    
    # Set default format
    gcloud config set core/format json
    
    print_success "Default configuration set"
}

# Create initial environment file
create_env_file() {
    print_status "Creating environment configuration..."
    
    if [[ ! -f ".env" ]]; then
        cp .env.template .env
        
        # Update with project-specific values
        sed -i.bak "s/your-gcp-project-id/$PROJECT_ID/g" .env
        sed -i.bak "s/your-project-id-opsmind-datasets/$PROJECT_ID-opsmind-datasets/g" .env
        rm .env.bak
        
        print_success "Environment file created: .env"
        print_warning "Please edit .env file with your actual values before deployment"
    else
        print_warning ".env file already exists. Skipping creation."
    fi
}

# Generate deployment summary
generate_summary() {
    print_success "🚀 GCP Project Setup Complete!"
    echo
    print_status "Project Information:"
    echo "  Project ID: $PROJECT_ID"
    echo "  Region: $REGION"
    echo "  Current Account: $(gcloud auth list --filter=status:ACTIVE --format="value(account)")"
    echo
    print_status "Next Steps:"
    echo "  1. Edit .env file with your API keys and configuration"
    echo "  2. Download datasets from Kaggle (see README.md)"
    echo "  3. Run deployment script: ./deploy.sh -p $PROJECT_ID"
    echo
    print_status "Useful Commands:"
    echo "  - Check project: gcloud projects describe $PROJECT_ID"
    echo "  - List services: gcloud services list --enabled"
    echo "  - View logs: gcloud logs tail"
    echo "  - Monitor billing: gcloud billing accounts list"
}

# Main setup function
main() {
    print_status "Starting GCP project setup for OpsMind..."
    print_status "Project: $PROJECT_ID"
    print_status "Region: $REGION"
    
    if [[ "$CREATE_PROJECT" == "true" ]]; then
        print_status "Creating new project: $PROJECT_ID"
        print_status "Billing Account: $BILLING_ACCOUNT"
    fi
    
    echo
    
    check_gcloud
    authenticate_gcp
    
    if [[ "$CREATE_PROJECT" == "true" ]]; then
        if [[ -z "$BILLING_ACCOUNT" ]]; then
            print_status "Available billing accounts:"
            list_billing_accounts
            read -p "Enter billing account ID: " BILLING_ACCOUNT
        fi
        create_project
    fi
    
    set_project
    check_permissions
    enable_apis
    setup_defaults
    create_env_file
    generate_summary
}

# Run main function
main "$@" 