#!/bin/bash
# WRAPD Linux Build Script

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🐧 WRAPD Linux Build Script${NC}"
echo "============================"

# Check if we're on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${RED}❌ This script must be run on Linux${NC}"
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
    echo "Install with: sudo apt install python3 python3-pip"
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}⚠️  uv not found, installing...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

echo -e "${GREEN}✅ Python and uv found${NC}"

# Check for system dependencies
echo -e "${BLUE}🔍 Checking system dependencies...${NC}"

# Check for Qt5 development libraries
if ! pkg-config --exists Qt5Core Qt5Widgets Qt5Gui; then
    echo -e "${YELLOW}⚠️  Qt5 development libraries not found${NC}"
    echo "Install with: sudo apt install qtbase5-dev qttools5-dev-tools"
    echo "Or on Fedora: sudo dnf install qt5-qtbase-devel qt5-qttools-devel"
    echo "Or on Arch: sudo pacman -S qt5-base qt5-tools"
fi

# Create virtual environment
echo -e "${BLUE}🐍 Creating virtual environment...${NC}"
cd "$SCRIPT_DIR"
uv venv --python 3.8
source .venv/bin/activate

# Install dependencies
echo -e "${BLUE}📦 Installing dependencies...${NC}"
uv pip install -r requirements.txt
uv pip install pyinstaller

# Check for PyQt5
echo -e "${BLUE}🖥️  Checking PyQt5...${NC}"
python3 -c "import PyQt5; print('PyQt5 OK')"

# Build the application
echo -e "${BLUE}🔨 Building WRAPD executable...${NC}"

# Build with PyInstaller
pyinstaller \
    --name=WRAPD \
    --onedir \
    --windowed \
    --distpath="$DIST_DIR" \
    --workpath="$BUILD_DIR" \
    --add-data="resources:resources" \
    --hidden-import=PyQt5 \
    --hidden-import=PyQt5.QtCore \
    --hidden-import=PyQt5.QtGui \
    --hidden-import=PyQt5.QtWidgets \
    --hidden-import=aiohttp \
    --hidden-import=keyring \
    --hidden-import=prompt_toolkit \
    --hidden-import=pygments \
    --hidden-import=paramiko \
    src/main.py

if [ ! -f "$DIST_DIR/WRAPD/WRAPD" ]; then
    echo -e "${RED}❌ Build failed - executable not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ WRAPD executable created successfully${NC}"

# Create AppImage (if appimagetool is available)
echo -e "${BLUE}📦 Creating AppImage...${NC}"

if command -v appimagetool &> /dev/null; then
    APPDIR="$BUILD_DIR/WRAPD.AppDir"
    mkdir -p "$APPDIR/usr/bin"
    mkdir -p "$APPDIR/usr/share/applications"
    mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "$APPDIR/usr/share/pixmaps"
    
    # Copy executable and dependencies
    cp -r "$DIST_DIR/WRAPD/"* "$APPDIR/usr/bin/"
    
    # Create desktop file
    cat > "$APPDIR/usr/share/applications/wrapd.desktop" << EOF
[Desktop Entry]
Type=Application
Name=WRAPD
Comment=Warp Replacement with AI-Powered Delivery
Exec=WRAPD
Icon=wrapd
Categories=Development;TerminalEmulator;
StartupNotify=true
EOF
    
    # Copy icon (create a simple one if not exists)
    if [ -f "resources/icons/wrapd.png" ]; then
        cp "resources/icons/wrapd.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/wrapd.png"
        cp "resources/icons/wrapd.png" "$APPDIR/usr/share/pixmaps/wrapd.png"
    else
        # Create a simple icon if none exists
        convert -size 256x256 xc:black -fill white -pointsize 48 -gravity center -annotate +0+0 'WRAPD' "$APPDIR/usr/share/icons/hicolor/256x256/apps/wrapd.png" 2>/dev/null || echo "No icon created"
    fi
    
    # Create AppRun
    cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin/:${PATH}"
cd "${HERE}/usr/bin"
exec "${HERE}/usr/bin/WRAPD" "$@"
EOF
    chmod +x "$APPDIR/AppRun"
    
    # Create desktop file in root
    cp "$APPDIR/usr/share/applications/wrapd.desktop" "$APPDIR/"
    
    # Copy icon to root
    if [ -f "$APPDIR/usr/share/pixmaps/wrapd.png" ]; then
        cp "$APPDIR/usr/share/pixmaps/wrapd.png" "$APPDIR/"
    fi
    
    # Build AppImage
    appimagetool "$APPDIR" "$DIST_DIR/WRAPD-1.0.0-x86_64.AppImage"
    
    if [ -f "$DIST_DIR/WRAPD-1.0.0-x86_64.AppImage" ]; then
        echo -e "${GREEN}✅ AppImage created successfully${NC}"
        chmod +x "$DIST_DIR/WRAPD-1.0.0-x86_64.AppImage"
    else
        echo -e "${YELLOW}⚠️  AppImage creation failed${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  appimagetool not found, skipping AppImage creation${NC}"
    echo "Install with: sudo apt install appimagetool"
fi

# Create DEB package (if dpkg-deb is available)
echo -e "${BLUE}📦 Creating DEB package...${NC}"

if command -v dpkg-deb &> /dev/null; then
    DEB_DIR="$BUILD_DIR/wrapd_1.0.0"
    mkdir -p "$DEB_DIR/DEBIAN"
    mkdir -p "$DEB_DIR/usr/bin"
    mkdir -p "$DEB_DIR/usr/share/applications"
    mkdir -p "$DEB_DIR/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "$DEB_DIR/usr/share/doc/wrapd"
    
    # Copy executable
    cp -r "$DIST_DIR/WRAPD/"* "$DEB_DIR/usr/bin/"
    
    # Create control file
    cat > "$DEB_DIR/DEBIAN/control" << EOF
Package: wrapd
Version: 1.0.0
Section: devel
Priority: optional
Architecture: amd64
Depends: libc6, libqt5core5a, libqt5gui5, libqt5widgets5
Maintainer: aegntic.ai <hello@aegntic.ai>
Description: WRAPD - Warp Replacement with AI-Powered Delivery
 An AI-powered terminal enhancement system that brings intelligent
 command suggestions, natural language processing, and contextual
 assistance while maintaining complete privacy and offline functionality.
Homepage: https://aegntic.ai
EOF
    
    # Create desktop file
    cp "$APPDIR/usr/share/applications/wrapd.desktop" "$DEB_DIR/usr/share/applications/" 2>/dev/null || true
    
    # Copy icon
    if [ -f "$APPDIR/usr/share/icons/hicolor/256x256/apps/wrapd.png" ]; then
        cp "$APPDIR/usr/share/icons/hicolor/256x256/apps/wrapd.png" "$DEB_DIR/usr/share/icons/hicolor/256x256/apps/"
    fi
    
    # Create copyright file
    cat > "$DEB_DIR/usr/share/doc/wrapd/copyright" << EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: WRAPD
Source: https://github.com/aegntic/wrapd

Files: *
Copyright: 2025 aegntic.ai
License: MIT
 MIT License - Forever Free
EOF
    
    # Build DEB
    dpkg-deb --build "$DEB_DIR" "$DIST_DIR/wrapd_1.0.0_amd64.deb"
    
    if [ -f "$DIST_DIR/wrapd_1.0.0_amd64.deb" ]; then
        echo -e "${GREEN}✅ DEB package created successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  DEB package creation failed${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  dpkg-deb not found, skipping DEB package creation${NC}"
fi

# Create TAR.GZ distribution
echo -e "${BLUE}📦 Creating TAR.GZ distribution...${NC}"
cd "$DIST_DIR"
tar -czf "WRAPD-1.0.0-linux-x86_64.tar.gz" WRAPD/
echo -e "${GREEN}✅ TAR.GZ created successfully${NC}"

echo -e "${GREEN}✅ Linux build complete!${NC}"
echo -e "${BLUE}📱 Executable: $DIST_DIR/WRAPD/WRAPD${NC}"
echo -e "${BLUE}📦 Archive: $DIST_DIR/WRAPD-1.0.0-linux-x86_64.tar.gz${NC}"

if [ -f "$DIST_DIR/WRAPD-1.0.0-x86_64.AppImage" ]; then
    echo -e "${BLUE}🖼️  AppImage: $DIST_DIR/WRAPD-1.0.0-x86_64.AppImage${NC}"
fi

if [ -f "$DIST_DIR/wrapd_1.0.0_amd64.deb" ]; then
    echo -e "${BLUE}📦 DEB: $DIST_DIR/wrapd_1.0.0_amd64.deb${NC}"
fi

echo -e "${BLUE}🎉 Build completed successfully!${NC}"
echo -e "${YELLOW}To run: ./dist/WRAPD/WRAPD${NC}"
echo -e "${YELLOW}To install DEB: sudo dpkg -i dist/wrapd_1.0.0_amd64.deb${NC}"
echo -e "${YELLOW}To run AppImage: ./dist/WRAPD-1.0.0-x86_64.AppImage${NC}"