#!/bin/bash

# WRAPD Global Shortcut Installer
# Installs Ctrl+Alt+Shift+T shortcut to launch WRAPD

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Installing WRAPD Global Shortcut...${NC}"

# Get the absolute path to WRAPD directory
WRAPD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPD_SCRIPT="$WRAPD_DIR/wrapd.sh"

echo -e "${BLUE}📁 WRAPD Directory: $WRAPD_DIR${NC}"

# Check if wrapd.sh exists
if [ ! -f "$WRAPD_SCRIPT" ]; then
    echo -e "${RED}❌ Error: wrapd.sh not found at $WRAPD_SCRIPT${NC}"
    exit 1
fi

# Make sure wrapd.sh is executable
chmod +x "$WRAPD_SCRIPT"

# Create launcher script in user's local bin
LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"

LAUNCHER_SCRIPT="$LOCAL_BIN/wrapd-launcher"

cat > "$LAUNCHER_SCRIPT" << EOF
#!/bin/bash
# WRAPD Launcher Script
# Launches a new instance of WRAPD Terminal

export WRAPD_DIR="$WRAPD_DIR"
cd "\$WRAPD_DIR"

# Launch WRAPD in a new process, detached from terminal
nohup ./wrapd.sh > /dev/null 2>&1 &

# Optional: Show notification
if command -v notify-send &> /dev/null; then
    notify-send "WRAPD" "Launching new terminal instance..." -i terminal
fi
EOF

chmod +x "$LAUNCHER_SCRIPT"

echo -e "${GREEN}✅ Created launcher script: $LAUNCHER_SCRIPT${NC}"

# Create desktop entry
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

DESKTOP_FILE="$DESKTOP_DIR/wrapd.desktop"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=WRAPD Terminal
Comment=Warp Replacement with AI-Powered Delivery
Exec=$LAUNCHER_SCRIPT
Icon=terminal
Terminal=false
Categories=System;TerminalEmulator;
Keywords=terminal;command;prompt;shell;ai;wrapd;
StartupNotify=true
EOF

echo -e "${GREEN}✅ Created desktop entry: $DESKTOP_FILE${NC}"

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$DESKTOP_DIR"
    echo -e "${GREEN}✅ Updated desktop database${NC}"
fi

# Detect desktop environment and configure shortcut
if [ "$XDG_CURRENT_DESKTOP" = "GNOME" ] || [ "$DESKTOP_SESSION" = "gnome" ]; then
    echo -e "${BLUE}🔧 Configuring GNOME shortcut...${NC}"
    
    # Get current custom keybindings
    CUSTOM_KEYBINDINGS=$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings)
    
    # Find next available slot
    SLOT=0
    while gsettings list-recursively org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom$SLOT/ 2>/dev/null | grep -q .; do
        SLOT=$((SLOT + 1))
    done
    
    CUSTOM_PATH="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom$SLOT/"
    
    # Add new keybinding path to the list
    if [ "$CUSTOM_KEYBINDINGS" = "@as []" ]; then
        NEW_KEYBINDINGS="['$CUSTOM_PATH']"
    else
        # Remove the closing bracket and add our path
        NEW_KEYBINDINGS=$(echo "$CUSTOM_KEYBINDINGS" | sed "s/]/, '$CUSTOM_PATH']/")
    fi
    
    # Set the custom keybindings list
    gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "$NEW_KEYBINDINGS"
    
    # Configure the specific keybinding
    gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$CUSTOM_PATH name "Launch WRAPD Terminal"
    gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$CUSTOM_PATH command "$LAUNCHER_SCRIPT"
    gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$CUSTOM_PATH binding "<Ctrl><Alt><Shift>t"
    
    echo -e "${GREEN}✅ GNOME shortcut configured: Ctrl+Alt+Shift+T${NC}"

elif [ "$XDG_CURRENT_DESKTOP" = "KDE" ] || [ "$DESKTOP_SESSION" = "plasma" ]; then
    echo -e "${BLUE}🔧 Configuring KDE shortcut...${NC}"
    
    # Create KDE shortcut configuration
    KDE_SHORTCUTS_DIR="$HOME/.config"
    KDE_SHORTCUTS_FILE="$KDE_SHORTCUTS_DIR/kglobalshortcutsrc"
    
    # Add WRAPD shortcut to KDE global shortcuts
    if [ -f "$KDE_SHORTCUTS_FILE" ]; then
        # Backup existing file
        cp "$KDE_SHORTCUTS_FILE" "$KDE_SHORTCUTS_FILE.backup"
    fi
    
    # Add our shortcut section
    cat >> "$KDE_SHORTCUTS_FILE" << EOF

[wrapd-launcher.desktop]
_k_friendly_name=WRAPD Terminal
launch-wrapd=Ctrl+Alt+Shift+T,none,Launch WRAPD Terminal
EOF

    echo -e "${GREEN}✅ KDE shortcut configured: Ctrl+Alt+Shift+T${NC}"
    echo -e "${YELLOW}⚠️  You may need to restart KDE or log out/in for the shortcut to take effect${NC}"

elif [ "$XDG_CURRENT_DESKTOP" = "XFCE" ]; then
    echo -e "${BLUE}🔧 Configuring XFCE shortcut...${NC}"
    
    # Add XFCE keyboard shortcut
    xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/<Primary><Alt><Shift>t" -n -t string -s "$LAUNCHER_SCRIPT"
    
    echo -e "${GREEN}✅ XFCE shortcut configured: Ctrl+Alt+Shift+T${NC}"

else
    echo -e "${YELLOW}⚠️  Desktop environment not automatically detected${NC}"
    echo -e "${BLUE}📋 Manual setup required:${NC}"
    echo -e "   1. Open your system's keyboard shortcuts settings"
    echo -e "   2. Add a new custom shortcut:"
    echo -e "      Name: Launch WRAPD Terminal"
    echo -e "      Command: $LAUNCHER_SCRIPT"
    echo -e "      Shortcut: Ctrl+Alt+Shift+T"
fi

# Add to PATH if not already there
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    echo -e "${BLUE}📝 Adding $LOCAL_BIN to PATH...${NC}"
    
    # Add to .bashrc
    echo "" >> "$HOME/.bashrc"
    echo "# Add local bin to PATH for WRAPD" >> "$HOME/.bashrc"
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$HOME/.bashrc"
    
    # Add to .zshrc if it exists
    if [ -f "$HOME/.zshrc" ]; then
        echo "" >> "$HOME/.zshrc"
        echo "# Add local bin to PATH for WRAPD" >> "$HOME/.zshrc"
        echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$HOME/.zshrc"
    fi
    
    echo -e "${GREEN}✅ Added to PATH (restart terminal or run 'source ~/.bashrc')${NC}"
fi

echo ""
echo -e "${GREEN}🎉 WRAPD Global Shortcut Installation Complete!${NC}"
echo ""
echo -e "${BLUE}📋 Summary:${NC}"
echo -e "   • Shortcut: ${YELLOW}Ctrl+Alt+Shift+T${NC}"
echo -e "   • Command: ${YELLOW}wrapd-launcher${NC}"
echo -e "   • Desktop Entry: $DESKTOP_FILE"
echo -e "   • Launcher Script: $LAUNCHER_SCRIPT"
echo ""
echo -e "${BLUE}🔥 Usage:${NC}"
echo -e "   • Press ${YELLOW}Ctrl+Alt+Shift+T${NC} to launch WRAPD from anywhere"
echo -e "   • Run ${YELLOW}wrapd-launcher${NC} from terminal"
echo -e "   • Find WRAPD in your application menu"
echo ""