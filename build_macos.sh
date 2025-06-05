#!/bin/bash
# WRAPD macOS Build Script

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🍎 WRAPD macOS Build Script${NC}"
echo "=============================="

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}❌ This script must be run on macOS${NC}"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BUILD_DIR="$SCRIPT_DIR/build"
DIST_DIR="$SCRIPT_DIR/dist"

echo -e "${BLUE}📂 Setting up build environment...${NC}"

# Create build directories
mkdir -p "$BUILD_DIR"
mkdir -p "$DIST_DIR"

# Check for required tools
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is required but not installed${NC}"
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}⚠️  uv not found, installing...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

echo -e "${GREEN}✅ Python and uv found${NC}"

# Create virtual environment
echo -e "${BLUE}🐍 Creating virtual environment...${NC}"
cd "$SCRIPT_DIR"
uv venv --python 3.8
source .venv/bin/activate

# Install dependencies
echo -e "${BLUE}📦 Installing dependencies...${NC}"
uv pip install -r requirements.txt
uv pip install pyinstaller

# Install macOS-specific dependencies
uv pip install py2app

# Check for PyQt5
echo -e "${BLUE}🖥️  Checking PyQt5...${NC}"
python3 -c "import PyQt5; print('PyQt5 OK')"

# Build the application
echo -e "${BLUE}🔨 Building WRAPD.app...${NC}"

# Create setup.py for py2app
cat > setup.py << 'EOF'
from setuptools import setup

APP = ['src/main.py']
DATA_FILES = [
    ('resources', ['resources']),
]

OPTIONS = {
    'argv_emulation': True,
    'plist': {
        'CFBundleName': 'WRAPD',
        'CFBundleDisplayName': 'WRAPD Terminal',
        'CFBundleGetInfoString': "WRAPD - Warp Replacement with AI-Powered Delivery",
        'CFBundleIdentifier': 'ai.aegntic.wrapd',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': '© 2025 aegntic.ai - Forever Free',
        'LSMinimumSystemVersion': '10.14',
        'LSApplicationCategoryType': 'public.app-category.developer-tools',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
    },
    'packages': ['PyQt5'],
    'includes': ['sip'],
    'excludes': ['tkinter'],
    'resources': ['resources/'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
EOF

# Build with py2app
python3 setup.py py2app --dist-dir="$DIST_DIR"

# Create DMG
echo -e "${BLUE}💾 Creating DMG installer...${NC}"

DMG_NAME="WRAPD-1.0.0-macOS"
DMG_PATH="$DIST_DIR/$DMG_NAME.dmg"

# Remove old DMG if exists
rm -f "$DMG_PATH"

# Create temporary DMG directory
DMG_TEMP_DIR="$BUILD_DIR/dmg_temp"
rm -rf "$DMG_TEMP_DIR"
mkdir -p "$DMG_TEMP_DIR"

# Copy app to temp directory
cp -R "$DIST_DIR/WRAPD.app" "$DMG_TEMP_DIR/"

# Create Applications symlink
ln -s /Applications "$DMG_TEMP_DIR/Applications"

# Create DMG
hdiutil create -volname "WRAPD" -srcfolder "$DMG_TEMP_DIR" -ov -format UDZO "$DMG_PATH"

# Clean up
rm -rf "$DMG_TEMP_DIR"
rm -f setup.py

echo -e "${GREEN}✅ macOS build complete!${NC}"
echo -e "${BLUE}📱 App: $DIST_DIR/WRAPD.app${NC}"
echo -e "${BLUE}💾 DMG: $DMG_PATH${NC}"

# Check app bundle
echo -e "${BLUE}🔍 Verifying app bundle...${NC}"
if [ -d "$DIST_DIR/WRAPD.app" ]; then
    echo -e "${GREEN}✅ WRAPD.app created successfully${NC}"
    ls -la "$DIST_DIR/WRAPD.app/Contents/"
else
    echo -e "${RED}❌ Failed to create WRAPD.app${NC}"
    exit 1
fi

echo -e "${BLUE}🎉 Build completed successfully!${NC}"
echo -e "${YELLOW}To install: Mount the DMG and drag WRAPD.app to Applications${NC}"