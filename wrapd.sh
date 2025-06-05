#!/bin/bash
# WRAPD: Warp Replacement with AI-Powered Delivery
# Launcher script

set -e  # Exit on error

# ANSI colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Print banner
echo -e "${BLUE}"
echo "██╗    ██╗██████╗  █████╗ ██████╗ ██████╗ "
echo "██║    ██║██╔══██╗██╔══██╗██╔══██╗██╔══██╗"
echo "██║ █╗ ██║██████╔╝███████║██████╔╝██║  ██║"
echo "██║███╗██║██╔══██╗██╔══██║██╔═══╝ ██║  ██║"
echo "╚███╔███╔╝██║  ██║██║  ██║██║     ██████╔╝"
echo " ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═════╝ "
echo -e "${NC}"
echo "Warp Replacement with AI-Powered Delivery"
echo "Version 1.0.0"
echo "------------------------------------------"

# Check for required dependencies
check_dependency() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${YELLOW}$1 is not installed.${NC}"
        return 1
    else
        echo -e "${GREEN}$1 is installed.${NC}"
        return 0
    fi
}

# Check for uv first, then Python 3.8+
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}uv is not installed. Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    
    # Check if installation was successful
    if ! command -v uv &> /dev/null; then
        echo -e "${RED}Failed to install uv. Please install it manually from https://github.com/astral-sh/uv${NC}"
        echo -e "${YELLOW}Falling back to traditional Python setup...${NC}"
        UV_AVAILABLE=false
    else
        echo -e "${GREEN}uv installed successfully.${NC}"
        UV_AVAILABLE=true
    fi
else
    echo -e "${GREEN}uv is available.${NC}"
    UV_AVAILABLE=true
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is required but not installed. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo -e "${RED}Python 3.8 or higher is required. Found Python $PYTHON_VERSION.${NC}"
    exit 1
fi

echo -e "${GREEN}Python $PYTHON_VERSION found.${NC}"

# Create and manage virtual environment
if [ "$UV_AVAILABLE" = true ]; then
    # Use uv for faster dependency management
    if [ ! -d "$SCRIPT_DIR/.venv" ]; then
        echo -e "${BLUE}Creating virtual environment with uv...${NC}"
        cd "$SCRIPT_DIR"
        uv venv
        echo -e "${BLUE}Installing dependencies with uv...${NC}"
        uv pip install -r requirements.txt
    else
        echo -e "${BLUE}Syncing dependencies with uv...${NC}"
        cd "$SCRIPT_DIR"
        # Check if requirements need to be updated
        if [ "$SCRIPT_DIR/requirements.txt" -nt "$SCRIPT_DIR/.venv" ]; then
            uv pip install -r requirements.txt
            touch "$SCRIPT_DIR/.venv"  # Update timestamp
        fi
    fi
    
    # Activate virtual environment
    source "$SCRIPT_DIR/.venv/bin/activate"
else
    # Fallback to traditional venv and pip
    if [ ! -d "$SCRIPT_DIR/.venv" ]; then
        echo -e "${BLUE}Creating virtual environment...${NC}"
        python3 -m venv "$SCRIPT_DIR/.venv"
        
        # Activate virtual environment
        source "$SCRIPT_DIR/.venv/bin/activate"
        
        # Upgrade pip
        echo -e "${BLUE}Upgrading pip...${NC}"
        pip install --upgrade pip
        
        # Install requirements
        echo -e "${BLUE}Installing requirements...${NC}"
        pip install -r "$SCRIPT_DIR/requirements.txt"
    else
        # Activate virtual environment
        source "$SCRIPT_DIR/.venv/bin/activate"
        
        # Check if requirements need to be updated
        if [ "$SCRIPT_DIR/requirements.txt" -nt "$SCRIPT_DIR/.venv" ]; then
            echo -e "${BLUE}Updating requirements...${NC}"
            pip install -r "$SCRIPT_DIR/requirements.txt"
            touch "$SCRIPT_DIR/.venv"  # Update timestamp
        fi
    fi
fi

# Check if we want to try Ollama for local models
USE_OLLAMA=true

# If any argument is "--no-ollama" or "-n", don't use Ollama
for arg in "$@"; do
    if [ "$arg" == "--no-ollama" ] || [ "$arg" == "-n" ]; then
        USE_OLLAMA=false
        break
    fi
done

# Check if Ollama is installed and running
if $USE_OLLAMA; then
    if ! command -v ollama &> /dev/null; then
        echo -e "${YELLOW}Ollama is not installed. For local models, please install Ollama from https://ollama.com/${NC}"
        echo -e "${YELLOW}Will use OpenRouter by default.${NC}"
        echo -e "${YELLOW}Please make sure to enter your OpenRouter API key in the settings when the application starts.${NC}"
    else
        # Check if Ollama is running
        if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
            echo -e "${YELLOW}Ollama is not running. Starting Ollama...${NC}"
            ollama serve &
            
            # Wait for Ollama to start
            echo -e "${BLUE}Waiting for Ollama to start...${NC}"
            for i in {1..10}; do
                if curl -s http://localhost:11434/api/tags &> /dev/null; then
                    echo -e "${GREEN}Ollama started successfully.${NC}"
                    break
                fi
                
                if [ $i -eq 10 ]; then
                    echo -e "${YELLOW}Failed to start Ollama. Will use OpenRouter instead.${NC}"
                    break
                fi
                
                echo "Waiting... ($i/10)"
                sleep 1
            done
        fi
        
        # Check if Gemma 3 1B is available
        if curl -s http://localhost:11434/api/tags | grep -q "gemma3:1b"; then
            echo -e "${GREEN}Gemma 3 1B model found.${NC}"
        else
            echo -e "${YELLOW}Gemma 3 1B model not found. Pulling model...${NC}"
            ollama pull gemma3:1b
            
            if [ $? -ne 0 ]; then
                echo -e "${YELLOW}Failed to pull Gemma 3 1B model. Will use OpenRouter instead.${NC}"
            fi
        fi
    fi
else
    echo -e "${YELLOW}Note: Skipping Ollama check. Will use OpenRouter by default.${NC}"
    echo -e "${YELLOW}Please make sure to enter your OpenRouter API key in the settings when the application starts.${NC}"
fi

# Optional dependency checks
echo -e "${BLUE}Checking optional dependencies...${NC}"
check_dependency "keyring" || echo -e "${YELLOW}API key storage will be limited.${NC}"

echo -e "${BLUE}Starting WRAPD Terminal...${NC}"
# Run the application
python "$SCRIPT_DIR/src/main.py" "$@"
