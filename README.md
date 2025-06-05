# WRAPD: Warp Replacement with AI-Powered Delivery

<div align="center">
  <img src="resources/icons/wrapd.png" alt="WRAPD Logo" width="128" height="128">
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-blue)](https://github.com/aegntic/wrapd)
  [![Python](https://img.shields.io/badge/python-3.8+-blue)](https://www.python.org/downloads/)
  [![Forever Free](https://img.shields.io/badge/💖-Forever%20Free-ff69b4)](https://aegntic.ai)
  
  **Forever Free. ❤️ aegntic.ai**
</div>

WRAPD (Warp Replacement with AI-Powered Delivery) is an open-source terminal enhancement system that brings AI-powered assistance to your command line without subscription fees. By leveraging locally-run language models, WRAPD provides intelligent command suggestions, natural language processing, and contextual assistance while maintaining complete privacy and offline functionality.

## ✨ Features

- 🆓 **Zero Subscription Cost**: Free and open-source alternative to premium terminal tools
- 🔒 **Complete Privacy**: All processing happens locally with no data sent to external servers
- 📴 **Offline Operation**: Fully functional without internet connectivity
- 🧠 **Smart Command Suggestions**: Get intelligent command completions and suggestions
- 🗣️ **Natural Language Processing**: Convert plain English requests into terminal commands
- 📖 **Command Explanation**: Understand what complex commands do before running them
- 🎯 **Context-Aware Assistance**: Suggestions based on current directory, command history, and active processes
- 🐚 **Multi-Shell Support**: Works with Bash, Zsh, Fish, and other popular shells
- ⚡ **Terminal Workflows**: Create and run complex command sequences with simple triggers
- 💨 **Minimal Resource Usage**: Optimized to run efficiently on modest hardware
- 🎛️ **Customizable Models**: Choose from multiple LLM options based on your hardware capabilities
- 🎨 **25+ Premium Themes**: Wu-Tang, TMNT, Rocko's Modern Life, Sesame Street, Nine Inch Nails, and more!
- 🔌 **Extensible Architecture**: Add custom plugins and extensions to enhance functionality

## 🎨 Featured Themes

WRAPD comes with 25+ professionally designed themes:

| Theme Collection | Variants | Preview |
|-----------------|----------|---------|
| **Wu-Tang Clan / Killa Bee** | Dark, Light, Pastel, Contrast | Golden honeycomb patterns with Wu-Tang aesthetics |
| **Teenage Mutant Ninja Turtles** | Dark, Light, Pastel, Contrast | Turtle power with Leo, Donnie, Mikey, and Raph colors |
| **Rocko's Modern Life** | Dark, Light, Pastel, Contrast | 90s nostalgia with vibrant retro styling |
| **Sesame Street** | Dark, Light, Pastel, Contrast | Educational fun with Elmo, Big Bird, and Cookie Monster |
| **Nine Inch Nails** | Dark, Light, Pastel, Contrast | Industrial cyberpunk with mechanical aesthetics |

*Each theme collection includes 4 variants: Dark (default), Light, Pastel, and High Contrast for accessibility.*

## 🚀 Quick Start

### One-Line Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/aegntic/wrapd/main/install.sh | bash
```

### Manual Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/aegntic/wrapd.git
   cd wrapd
   ```

2. **Make the launcher executable:**
   ```bash
   chmod +x wrapd.sh
   ```

3. **Run WRAPD:**
   ```bash
   ./wrapd.sh
   ```

The launcher will automatically:
- Install uv (ultra-fast Python package manager)
- Create a virtual environment
- Install all dependencies
- Set up Ollama (if desired)
- Pull the default Wu-Tang themed experience
- Launch WRAPD

## 📦 Platform-Specific Installation

### 🍎 macOS

**Requirements:** macOS 10.14+ (Mojave or later)

```bash
# Install via Homebrew (coming soon)
brew install aegntic/tap/wrapd

# Or download DMG
curl -L https://github.com/aegntic/wrapd/releases/latest/download/WRAPD-macOS.dmg -o WRAPD.dmg
open WRAPD.dmg
```

### 🐧 Linux

**Ubuntu/Debian:**
```bash
# Install dependencies
sudo apt update && sudo apt install python3 python3-pip qtbase5-dev

# Install via DEB package
curl -L https://github.com/aegntic/wrapd/releases/latest/download/wrapd_amd64.deb -o wrapd.deb
sudo dpkg -i wrapd.deb

# Or install via AppImage
curl -L https://github.com/aegntic/wrapd/releases/latest/download/WRAPD-x86_64.AppImage -o WRAPD.AppImage
chmod +x WRAPD.AppImage
./WRAPD.AppImage
```

**Fedora/RHEL:**
```bash
# Install dependencies
sudo dnf install python3 python3-pip qt5-qtbase-devel

# Install from source
git clone https://github.com/aegntic/wrapd.git && cd wrapd && ./wrapd.sh
```

**Arch Linux:**
```bash
# Install from AUR (coming soon)
yay -S wrapd

# Or install dependencies and run from source
sudo pacman -S python qt5-base && git clone https://github.com/aegntic/wrapd.git && cd wrapd && ./wrapd.sh
```

### 🪟 Windows

**Windows 10/11:**

1. **Download installer:**
   ```powershell
   # Via PowerShell
   Invoke-WebRequest -Uri "https://github.com/aegntic/wrapd/releases/latest/download/WRAPD-Windows-Setup.exe" -OutFile "WRAPD-Setup.exe"
   .\WRAPD-Setup.exe
   ```

2. **Or run from source:**
   ```cmd
   git clone https://github.com/aegntic/wrapd.git
   cd wrapd
   build_windows.bat
   ```

## 🛠️ Building from Source

### Prerequisites

- **Python 3.8+**
- **uv** (automatically installed by build scripts)
- **Platform-specific requirements:**
  - **macOS:** Xcode Command Line Tools
  - **Linux:** Qt5 development libraries
  - **Windows:** Visual Studio Build Tools (optional)

### Build Commands

```bash
# Universal build script (auto-detects platform)
./build.sh

# Or platform-specific:
./build_macos.sh    # Creates .app and .dmg
./build_linux.sh    # Creates AppImage, DEB, and tar.gz
./build_windows.bat # Creates .exe and installer
```

## 🎛️ Configuration

### AI Models

WRAPD supports both local and cloud AI models:

**Local Models (via Ollama):**
- Gemma 3 1B (default) - Fast, lightweight
- Phi-3 3B - Microsoft's efficient model
- Qwen2 7B - Alibaba's multilingual model
- Any Ollama-compatible model

**Cloud Models (via OpenRouter):**
- GPT-4, Claude, Gemini Pro
- Requires API key (stored securely)

### Themes

Switch themes instantly:
1. **Menu Bar:** View → Theme → [Select Theme]
2. **Keyboard:** `Ctrl+Shift+T` → Theme selector
3. **Settings:** File → Settings → Appearance

### Keyboard Shortcuts

| Action | Default Shortcut | Customizable |
|--------|------------------|-------------|
| New Tab | `Ctrl+T` | ✅ |
| Close Tab | `Ctrl+W` | ✅ |
| Clear Terminal | `Ctrl+L` | ✅ |
| Increase Font | `Ctrl++` | ✅ |
| Decrease Font | `Ctrl+-` | ✅ |
| Toggle Transparency | `Ctrl+Shift+T` | ✅ |
| AI Help | `help` or `?` after command | ✅ |

## 🔧 Advanced Usage

### Custom Themes

Create your own themes by copying any existing theme from `resources/themes/` and modifying the CSS:

```bash
cp resources/themes/wutang_dark.css resources/themes/my_theme.css
# Edit my_theme.css
# Restart WRAPD and select "Custom" theme
```

### API Configuration

```bash
# Set OpenRouter API key
echo "export OPENROUTER_API_KEY='your-key-here'" >> ~/.bashrc

# Or configure in settings UI
File → Settings → AI Models → OpenRouter API Key
```

### Command Workflows

Create custom command workflows:

```bash
# Natural language commands
$ "install docker"
# AI suggests: curl -fsSL https://get.docker.com | bash

$ "show me large files"
# AI suggests: find . -type f -size +100M -exec ls -lh {} \;
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
git clone https://github.com/aegntic/wrapd.git
cd wrapd
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
python src/main.py
```

### Create a Theme

1. Copy an existing theme file
2. Modify colors and styling
3. Test with `python src/main.py`
4. Submit a PR with your theme!

## 📜 License

MIT License - Forever Free ❤️

```
Copyright (c) 2025 aegntic.ai

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 🌟 Support

- 🐛 **Bug Reports:** [GitHub Issues](https://github.com/aegntic/wrapd/issues)
- 💡 **Feature Requests:** [GitHub Discussions](https://github.com/aegntic/wrapd/discussions)
- 📧 **Email:** hello@aegntic.ai
- 🌐 **Website:** [aegntic.ai](https://aegntic.ai)

## 🎉 Acknowledgments

- Inspired by [Warp Terminal](https://www.warp.dev/)
- Built with [PyQt5](https://riverbankcomputing.com/software/pyqt/)
- AI powered by [Ollama](https://ollama.ai/) and [OpenRouter](https://openrouter.ai/)
- Package management by [uv](https://github.com/astral-sh/uv)

---

<div align="center">
  <strong>Forever Free. ❤️ aegntic.ai</strong><br>
  <em>Because great tools should be accessible to everyone.</em>
</div>
