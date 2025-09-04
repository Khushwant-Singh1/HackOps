#!/bin/bash

# HackOps Backend Development Scripts

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install dependencies
install_deps() {
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    print_status "Dependencies installed successfully!"
}

# Install development dependencies
install_dev_deps() {
    print_status "Installing development dependencies..."
    pip install -r requirements-dev.txt
    print_status "Development dependencies installed successfully!"
}

# Setup database
setup_db() {
    print_status "Setting up database..."
    
    if [ -f ".env" ]; then
        print_status "Loading environment variables from .env"
        export $(cat .env | grep -v '^#' | xargs)
    else
        print_warning "No .env file found. Using default values."
    fi
    
    # Run Alembic migrations
    print_status "Running database migrations..."
    alembic upgrade head
    print_status "Database setup completed!"
}

# Start development server
dev_server() {
    print_status "Starting development server..."
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
}

# Start with Docker
docker_dev() {
    print_status "Starting development environment with Docker..."
    
    # Check if Docker is installed
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Start development services
    docker-compose -f docker-compose.dev.yml up -d
    print_status "Development services started!"
    print_status "PostgreSQL: localhost:5432"
    print_status "Redis: localhost:6379" 
    print_status "PgAdmin: http://localhost:5050"
    print_status "Redis Commander: http://localhost:8081"
}

# Stop Docker services
docker_stop() {
    print_status "Stopping Docker services..."
    docker-compose -f docker-compose.dev.yml down
    print_status "Docker services stopped!"
}

# Run tests
run_tests() {
    print_status "Running tests..."
    pytest -v --cov=app --cov-report=term-missing
}

# Format code
format_code() {
    print_status "Formatting code..."
    black .
    isort .
    print_status "Code formatted!"
}

# Lint code
lint_code() {
    print_status "Linting code..."
    flake8 .
    mypy app/
}

# Create migration
create_migration() {
    if [ -z "$1" ]; then
        print_error "Please provide a migration message"
        print_status "Usage: ./scripts/dev.sh migration \"Add user table\""
        exit 1
    fi
    
    print_status "Creating migration: $1"
    alembic revision --autogenerate -m "$1"
}

# Run migration
run_migration() {
    print_status "Running migrations..."
    alembic upgrade head
}

# Rollback migration
rollback_migration() {
    print_status "Rolling back last migration..."
    alembic downgrade -1
}

# Clean up
cleanup() {
    print_status "Cleaning up..."
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    print_status "Cleanup completed!"
}

# Show help
show_help() {
    echo "HackOps Backend Development Script"
    echo ""
    echo "Usage: ./scripts/dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  install          Install Python dependencies"
    echo "  install-dev      Install development dependencies"
    echo "  setup-db         Setup database and run migrations"
    echo "  dev              Start development server"
    echo "  docker-dev       Start development environment with Docker"
    echo "  docker-stop      Stop Docker development services"
    echo "  test             Run tests"
    echo "  format           Format code with black and isort"
    echo "  lint             Lint code with flake8 and mypy"
    echo "  migration MSG    Create new migration"
    echo "  migrate          Run pending migrations"
    echo "  rollback         Rollback last migration"
    echo "  cleanup          Clean up cache files"
    echo "  help             Show this help message"
}

# Main script logic
case "$1" in
    "install")
        install_deps
        ;;
    "install-dev")
        install_dev_deps
        ;;
    "setup-db")
        setup_db
        ;;
    "dev")
        dev_server
        ;;
    "docker-dev")
        docker_dev
        ;;
    "docker-stop")
        docker_stop
        ;;
    "test")
        run_tests
        ;;
    "format")
        format_code
        ;;
    "lint")
        lint_code
        ;;
    "migration")
        create_migration "$2"
        ;;
    "migrate")
        run_migration
        ;;
    "rollback")
        rollback_migration
        ;;
    "cleanup")
        cleanup
        ;;
    "help"|"")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
