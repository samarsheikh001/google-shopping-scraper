#!/bin/bash

# Google Shopping Scraper Runner Script for YUM-based systems
# This script provides various options to run the Google Shopping Scraper on CentOS/RHEL/Amazon Linux

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
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

# Function to check if running as root or with sudo
check_sudo() {
    if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
        print_warning "This script may need sudo privileges for system package installation."
        print_info "You may be prompted for your password."
    fi
}

# Function to install system dependencies via yum
install_system_deps() {
    print_info "Installing system dependencies via yum..."
    
    # Update package list
    if command -v dnf &> /dev/null; then
        print_info "Using dnf package manager"
        sudo dnf update -y
        sudo dnf groupinstall -y "Development Tools"
        sudo dnf install -y python3 python3-pip python3-devel curl wget unzip
        
        # Install Chrome dependencies
        sudo dnf install -y \
            google-chrome-stable \
            || sudo dnf install -y chromium \
            || print_warning "Could not install Chrome/Chromium via dnf"
    else
        print_info "Using yum package manager"
        sudo yum update -y
        sudo yum groupinstall -y "Development Tools"
        sudo yum install -y python3 python3-pip python3-devel curl wget unzip epel-release
        
        # Install Chrome dependencies
        sudo yum install -y \
            google-chrome-stable \
            || sudo yum install -y chromium \
            || print_warning "Could not install Chrome/Chromium via yum"
    fi
    
    # Install Google Chrome if not available in repos
    if ! command -v google-chrome &> /dev/null && ! command -v chromium &> /dev/null; then
        print_info "Installing Google Chrome manually..."
        wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo rpm --import -
        sudo sh -c 'echo "[google-chrome]
name=google-chrome
baseurl=http://dl.google.com/linux/chrome/rpm/stable/x86_64
enabled=1
gpgcheck=1
gpgkey=https://dl.google.com/linux/linux_signing_key.pub" > /etc/yum.repos.d/google-chrome.repo'
        
        if command -v dnf &> /dev/null; then
            sudo dnf install -y google-chrome-stable
        else
            sudo yum install -y google-chrome-stable
        fi
    fi
    
    print_success "System dependencies installed successfully"
}

# Function to check if Python is installed and install if needed
check_install_python() {
    if ! command -v python3 &> /dev/null; then
        print_warning "Python 3 is not installed. Installing via yum..."
        install_system_deps
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2)
    print_info "Python version: $python_version"
    
    # Check if pip is available
    if ! command -v pip3 &> /dev/null; then
        print_info "Installing pip3..."
        if command -v dnf &> /dev/null; then
            sudo dnf install -y python3-pip
        else
            sudo yum install -y python3-pip
        fi
    fi
    
    # Upgrade pip
    print_info "Upgrading pip..."
    python3 -m pip install --upgrade pip --user
}

# Function to check if Poetry is installed
check_poetry() {
    if ! command -v poetry &> /dev/null; then
        print_warning "Poetry is not installed. Installing Poetry..."
        curl -sSL https://install.python-poetry.org | python3 -
        
        # Add Poetry to PATH for current session
        export PATH="$HOME/.local/bin:$PATH"
        
        # Add to shell profile
        if [[ -f ~/.bashrc ]]; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        fi
        if [[ -f ~/.zshrc ]]; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
        fi
        
        print_info "Poetry installed. You may need to restart your shell or run: source ~/.bashrc"
    else
        print_info "Poetry is already installed"
    fi
}

# Function to install dependencies
install_dependencies() {
    print_info "Installing Python dependencies..."
    
    if command -v poetry &> /dev/null; then
        print_info "Using Poetry for dependency management"
        poetry install
        print_success "Dependencies installed successfully with Poetry"
    else
        print_info "Using pip for dependency management"
        python3 -m pip install -r requirements.txt --user
        print_success "Dependencies installed successfully with pip"
    fi
}

# Function to start the API server
start_api() {
    print_info "Starting Google Shopping Scraper API server..."
    
    if command -v poetry &> /dev/null; then
        poetry run python run_api.py
    else
        python3 run_api.py
    fi
}

# Function to run direct scraping
run_scrape() {
    local query="$1"
    
    if [ -z "$query" ]; then
        print_error "Query is required for scraping. Usage: $0 scrape \"your search query\""
        exit 1
    fi
    
    print_info "Scraping Google Shopping for query: '$query'"
    
    if command -v poetry &> /dev/null; then
        poetry run python scrape_to_json.py "$query"
    else
        python3 scrape_to_json.py "$query"
    fi
    
    print_success "Scraping completed. Check the generated JSON file."
}

# Function to test the API
test_api() {
    local query="${1:-smartphone}"
    
    print_info "Testing API with query: '$query'"
    
    # Check if API is running
    if ! curl -s http://localhost:8000/ > /dev/null; then
        print_error "API is not running. Please start the API first with: $0 api"
        exit 1
    fi
    
    print_info "Making API request..."
    curl -s "http://localhost:8000/scrape?query=$(echo "$query" | sed 's/ /%20/g')" | python3 -m json.tool
}

# Function to stop the API
stop_api() {
    print_info "Stopping API server..."
    
    # Try to find and kill the process
    if pgrep -f "run_api.py" > /dev/null; then
        pkill -f "run_api.py"
        print_success "API server stopped"
    elif pgrep -f "uvicorn.*api:app" > /dev/null; then
        pkill -f "uvicorn.*api:app"
        print_success "API server stopped"
    else
        print_warning "No API server process found"
    fi
}

# Function to clean up generated files
clean() {
    print_info "Cleaning up generated files..."
    
    rm -rf debug/
    rm -f shopping_results_*.json
    rm -f shopping.csv
    rm -f chromedriver.log
    rm -f chromedriver_test.log
    
    print_success "Cleanup completed"
}

# Function to setup firewall (if needed)
setup_firewall() {
    print_info "Checking firewall configuration for API access..."
    
    if command -v firewall-cmd &> /dev/null; then
        if sudo firewall-cmd --state &> /dev/null; then
            print_info "Opening port 8000 in firewall..."
            sudo firewall-cmd --permanent --add-port=8000/tcp
            sudo firewall-cmd --reload
            print_success "Firewall configured for port 8000"
        fi
    elif command -v iptables &> /dev/null; then
        print_info "Configuring iptables for port 8000..."
        sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
        print_success "iptables configured for port 8000"
    else
        print_info "No firewall management tool found, skipping firewall configuration"
    fi
}

# Function to show system info
show_system_info() {
    print_info "System Information:"
    echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
    echo "Kernel: $(uname -r)"
    echo "Architecture: $(uname -m)"
    
    if command -v python3 &> /dev/null; then
        echo "Python: $(python3 --version)"
    else
        echo "Python: Not installed"
    fi
    
    if command -v poetry &> /dev/null; then
        echo "Poetry: $(poetry --version)"
    else
        echo "Poetry: Not installed"
    fi
    
    if command -v google-chrome &> /dev/null; then
        echo "Chrome: $(google-chrome --version)"
    elif command -v chromium &> /dev/null; then
        echo "Chromium: $(chromium --version)"
    else
        echo "Chrome/Chromium: Not installed"
    fi
}

# Function to show usage
show_usage() {
    echo "Google Shopping Scraper Runner for YUM-based Systems"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  system-deps                Install system dependencies via yum/dnf"
    echo "  install                    Install Python dependencies"
    echo "  setup                      Full setup (system deps + Python deps)"
    echo "  api                        Start the API server"
    echo "  scrape \"query\"             Run direct scraping with the given query"
    echo "  test [query]               Test the API (default query: 'smartphone')"
    echo "  stop                       Stop the API server"
    echo "  clean                      Clean up generated files"
    echo "  firewall                   Configure firewall for API access"
    echo "  info                       Show system information"
    echo "  help                       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup                   # Full setup (recommended for first run)"
    echo "  $0 system-deps             # Install system packages only"
    echo "  $0 install                 # Install Python dependencies only"
    echo "  $0 api                     # Start the API server"
    echo "  $0 scrape \"cat food\"       # Scrape for 'cat food'"
    echo "  $0 test \"laptop\"           # Test API with 'laptop' query"
    echo "  $0 stop                    # Stop the API server"
    echo "  $0 clean                   # Clean up files"
    echo "  $0 firewall                # Configure firewall"
    echo "  $0 info                    # Show system info"
    echo ""
    echo "API Endpoints (when server is running):"
    echo "  http://localhost:8000/                    - API info"
    echo "  http://localhost:8000/docs                - Interactive documentation"
    echo "  http://localhost:8000/scrape?query=...    - Scrape endpoint"
    echo ""
    echo "Note: This script is designed for YUM-based systems (CentOS, RHEL, Amazon Linux, etc.)"
}

# Main script logic
main() {
    case "${1:-help}" in
        "system-deps")
            check_sudo
            install_system_deps
            ;;
        "install")
            check_install_python
            check_poetry
            install_dependencies
            ;;
        "setup")
            check_sudo
            install_system_deps
            check_install_python
            check_poetry
            install_dependencies
            print_success "Full setup completed!"
            ;;
        "api")
            check_install_python
            start_api
            ;;
        "scrape")
            check_install_python
            run_scrape "$2"
            ;;
        "test")
            test_api "$2"
            ;;
        "stop")
            stop_api
            ;;
        "clean")
            clean
            ;;
        "firewall")
            check_sudo
            setup_firewall
            ;;
        "info")
            show_system_info
            ;;
        "help"|"--help"|"-h"|"")
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run the main function with all arguments
main "$@" 