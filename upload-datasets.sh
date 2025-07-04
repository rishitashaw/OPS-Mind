#!/bin/bash

# Dataset Upload Script for OpsMind
# This script uploads datasets to Google Cloud Storage

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PROJECT_ID=""
BUCKET_NAME=""
DATASETS_DIR="./opsmind/data/datasets"
PARALLEL_UPLOADS=true
VERIFY_UPLOADS=true

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

Upload OpsMind datasets to Google Cloud Storage

OPTIONS:
    -p, --project-id PROJECT_ID    GCP Project ID (required)
    -b, --bucket-name BUCKET       Cloud Storage bucket name (optional)
    -d, --datasets-dir DIR         Local datasets directory (default: ./opsmind/data/datasets)
    --no-parallel                  Disable parallel uploads
    --no-verify                    Skip upload verification
    -h, --help                     Show this help message

EXAMPLES:
    $0 -p my-project-id
    $0 -p my-project-id -b my-custom-bucket
    $0 -p my-project-id -d /path/to/datasets

DATASET STRUCTURE:
    The datasets directory should contain:
    - incidents/incident_event_log.csv
    - jira/issues.csv
    - jira/comments.csv
    - jira/changelog.csv
    - jira/issuelinks.csv

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--project-id)
            PROJECT_ID="$2"
            shift 2
            ;;
        -b|--bucket-name)
            BUCKET_NAME="$2"
            shift 2
            ;;
        -d|--datasets-dir)
            DATASETS_DIR="$2"
            shift 2
            ;;
        --no-parallel)
            PARALLEL_UPLOADS=false
            shift
            ;;
        --no-verify)
            VERIFY_UPLOADS=false
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

# Set default bucket name if not provided
if [[ -z "$BUCKET_NAME" ]]; then
    BUCKET_NAME="$PROJECT_ID-opsmind-datasets"
fi

# Check if gsutil is installed
check_gsutil() {
    print_status "Checking gsutil installation..."
    
    if ! command -v gsutil &> /dev/null; then
        print_error "gsutil is not installed or not in PATH"
        print_error "Please install Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    print_success "gsutil is available"
}

# Check authentication
check_authentication() {
    print_status "Checking GCP authentication..."
    
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
        print_error "Not authenticated with GCP"
        print_error "Please run: gcloud auth login"
        exit 1
    fi
    
    # Set project
    gcloud config set project "$PROJECT_ID"
    print_success "Authenticated and project set to: $PROJECT_ID"
}

# Check if datasets directory exists
check_datasets_directory() {
    print_status "Checking datasets directory: $DATASETS_DIR"
    
    if [[ ! -d "$DATASETS_DIR" ]]; then
        print_error "Datasets directory not found: $DATASETS_DIR"
        print_error "Please download datasets from Kaggle first (see README.md)"
        exit 1
    fi
    
    print_success "Datasets directory found"
}

# Validate dataset files
validate_datasets() {
    print_status "Validating dataset files..."
    
    local required_files=(
        "incidents/incident_event_log.csv"
        "jira/issues.csv"
        "jira/comments.csv"
        "jira/changelog.csv"
        "jira/issuelinks.csv"
    )
    
    local missing_files=()
    local total_size=0
    
    for file in "${required_files[@]}"; do
        local full_path="$DATASETS_DIR/$file"
        if [[ ! -f "$full_path" ]]; then
            missing_files+=("$file")
        else
            local size=$(stat -c%s "$full_path" 2>/dev/null || stat -f%z "$full_path" 2>/dev/null || echo "0")
            total_size=$((total_size + size))
            print_status "Found: $file ($(numfmt --to=iec $size))"
        fi
    done
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        print_warning "Missing dataset files:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        print_warning "Download missing files from Kaggle (see README.md)"
        read -p "Continue with available files? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    print_success "Dataset validation complete"
    print_status "Total dataset size: $(numfmt --to=iec $total_size)"
}

# Check if bucket exists
check_bucket() {
    print_status "Checking Cloud Storage bucket: gs://$BUCKET_NAME"
    
    if ! gsutil ls -b "gs://$BUCKET_NAME" &> /dev/null; then
        print_error "Bucket does not exist: gs://$BUCKET_NAME"
        print_status "Creating bucket..."
        
        gsutil mb -p "$PROJECT_ID" -l us-central1 "gs://$BUCKET_NAME"
        print_success "Created bucket: gs://$BUCKET_NAME"
    else
        print_success "Bucket exists: gs://$BUCKET_NAME"
    fi
}

# Set bucket permissions
set_bucket_permissions() {
    print_status "Setting bucket permissions..."
    
    # Make bucket accessible to the OpsMind service account
    local service_account="opsmind-service-account@$PROJECT_ID.iam.gserviceaccount.com"
    
    gsutil iam ch serviceAccount:$service_account:objectViewer "gs://$BUCKET_NAME" || {
        print_warning "Could not set service account permissions. You may need to set them manually."
    }
    
    print_success "Bucket permissions configured"
}

# Upload files to bucket
upload_datasets() {
    print_status "Uploading datasets to gs://$BUCKET_NAME..."
    
    local upload_options=()
    
    # Add parallel upload option if enabled
    if [[ "$PARALLEL_UPLOADS" == "true" ]]; then
        upload_options+=("-m")
    fi
    
    # Add other options
    upload_options+=("-r")  # Recursive
    upload_options+=("-C")  # Continue on error
    
    # Upload incidents directory
    if [[ -d "$DATASETS_DIR/incidents" ]]; then
        print_status "Uploading incidents dataset..."
        gsutil "${upload_options[@]}" cp "$DATASETS_DIR/incidents/*" "gs://$BUCKET_NAME/incidents/"
        print_success "Incidents dataset uploaded"
    fi
    
    # Upload jira directory
    if [[ -d "$DATASETS_DIR/jira" ]]; then
        print_status "Uploading Jira datasets..."
        gsutil "${upload_options[@]}" cp "$DATASETS_DIR/jira/*" "gs://$BUCKET_NAME/jira/"
        print_success "Jira datasets uploaded"
    fi
    
    print_success "All datasets uploaded successfully"
}

# Verify uploads
verify_uploads() {
    if [[ "$VERIFY_UPLOADS" != "true" ]]; then
        return 0
    fi
    
    print_status "Verifying uploads..."
    
    # List uploaded files
    print_status "Files in bucket:"
    gsutil ls -lh "gs://$BUCKET_NAME/**" | head -20
    
    # Check if we have more than 20 files
    local file_count=$(gsutil ls "gs://$BUCKET_NAME/**" | wc -l)
    if [[ $file_count -gt 20 ]]; then
        print_status "... and $((file_count - 20)) more files"
    fi
    
    # Calculate total size
    local total_size=$(gsutil du -s "gs://$BUCKET_NAME" | awk '{print $1}')
    print_status "Total size in bucket: $(numfmt --to=iec $total_size)"
    
    print_success "Upload verification complete"
}

# Generate access instructions
generate_access_instructions() {
    print_success "🚀 Dataset Upload Complete!"
    echo
    print_status "Bucket Information:"
    echo "  Bucket: gs://$BUCKET_NAME"
    echo "  Project: $PROJECT_ID"
    echo "  Region: us-central1"
    echo
    print_status "Access Instructions:"
    echo "  1. OpsMind will automatically access datasets from the bucket"
    echo "  2. Ensure your .env file has: DATASETS_BUCKET=$BUCKET_NAME"
    echo "  3. Service account has read permissions to the bucket"
    echo
    print_status "Useful Commands:"
    echo "  - List files: gsutil ls -lh gs://$BUCKET_NAME/**"
    echo "  - Check size: gsutil du -sh gs://$BUCKET_NAME"
    echo "  - Download file: gsutil cp gs://$BUCKET_NAME/path/to/file ."
    echo "  - Remove bucket: gsutil rm -r gs://$BUCKET_NAME"
    echo
    print_status "Cost Management:"
    echo "  - Monitor storage costs in GCP Console"
    echo "  - Consider lifecycle policies for old data"
    echo "  - Use regional storage for cost optimization"
}

# Main upload function
main() {
    print_status "Starting dataset upload to Google Cloud Storage..."
    print_status "Project: $PROJECT_ID"
    print_status "Bucket: $BUCKET_NAME"
    print_status "Datasets Directory: $DATASETS_DIR"
    print_status "Parallel Uploads: $PARALLEL_UPLOADS"
    print_status "Verify Uploads: $VERIFY_UPLOADS"
    echo
    
    check_gsutil
    check_authentication
    check_datasets_directory
    validate_datasets
    check_bucket
    set_bucket_permissions
    upload_datasets
    verify_uploads
    generate_access_instructions
}

# Show warning about costs
show_cost_warning() {
    print_warning "⚠️  COST INFORMATION ⚠️"
    echo
    print_status "Dataset sizes (approximate):"
    echo "  - Incident Event Log: 44 MB"
    echo "  - Jira Issues: 1.8 GB"
    echo "  - Jira Comments: 3.8 GB"
    echo "  - Jira Changelog: 2.5 GB"
    echo "  - Jira Issue Links: 99 MB"
    echo "  - Total: ~8.3 GB"
    echo
    print_status "Estimated monthly costs (US regions):"
    echo "  - Standard Storage: ~$0.20/month"
    echo "  - Network egress: Variable based on usage"
    echo "  - Operations: Minimal for normal usage"
    echo
    print_status "For detailed pricing, visit: https://cloud.google.com/storage/pricing"
    echo
    read -p "Continue with upload? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Upload cancelled by user"
        exit 0
    fi
}

# Run cost warning and main function
show_cost_warning
main "$@" 