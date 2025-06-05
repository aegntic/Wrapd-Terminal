#!/bin/bash
# WRAPD Universal Build Script

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 WRAPD Universal Build Script${NC}"
echo "=================================="

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Detect platform
case "$OSTYPE" in
    darwin*)
        echo -e "${BLUE}🍎 Detected macOS${NC}"
        if [ -f "$SCRIPT_DIR/build_macos.sh" ]; then
            exec "$SCRIPT_DIR/build_macos.sh" "$@"
        else
            echo -e "${RED}❌ macOS build script not found${NC}"
            exit 1
        fi
        ;;
    linux-gnu*)
        echo -e "${BLUE}🐧 Detected Linux${NC}"
        if [ -f "$SCRIPT_DIR/build_linux.sh" ]; then
            exec "$SCRIPT_DIR/build_linux.sh" "$@"
        else
            echo -e "${RED}❌ Linux build script not found${NC}"
            exit 1
        fi
        ;;
    msys*|cygwin*|mingw*)
        echo -e "${BLUE}🪟 Detected Windows (WSL/MinGW)${NC}"
        if [ -f "$SCRIPT_DIR/build_windows.bat" ]; then
            echo -e "${YELLOW}ℹ️  Running Windows batch script...${NC}"
            cmd.exe /c "\"$SCRIPT_DIR/build_windows.bat\""
        else
            echo -e "${RED}❌ Windows build script not found${NC}"
            exit 1
        fi
        ;;
    *)
        echo -e "${RED}❌ Unsupported platform: $OSTYPE${NC}"
        echo "Supported platforms:"
        echo "  - macOS (darwin)"
        echo "  - Linux (linux-gnu)"
        echo "  - Windows (via WSL/MinGW or run build_windows.bat directly)"
        exit 1
        ;;
esac