# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WRAPD (Warp Replacement with AI-Powered Delivery) is an open-source PyQt5-based terminal enhancement system that provides AI-powered assistance for command line operations. The application supports both local models (via Ollama) and cloud models (via OpenRouter).

## Development Commands

### Setup and Installation
- `./wrapd.sh` - Main launcher script that handles uv/virtual environment setup, dependency installation, and application launch
- `python local_launcher.py` - Alternative Python launcher script (with uv support)
- `uv pip install -r requirements.txt` - Install dependencies with uv (faster)
- `pip install -r requirements.txt` - Install dependencies manually (fallback)
- `uv sync` - Sync dependencies using pyproject.toml (recommended for development)

### Running the Application
- `./wrapd.sh` - Standard launch with Ollama support
- `./wrapd.sh --no-ollama` - Launch without Ollama (cloud-only mode)
- `python src/main.py` - Direct launch from source

### Testing and Validation
- Check `src/main.py` for main application entry point
- No specific test framework detected - manual testing recommended
- Verify PyQt5 installation: `python -c "import PyQt5; print('PyQt5 available')"`

## Architecture Overview

### Core Components
- **Main Application**: `src/main.py` - Entry point, initializes all core components
- **Command Processor**: `src/core/command_processor.py` - Handles terminal command execution, validation, and AI-powered error analysis
- **LLM Interface**: `src/core/llm_interface.py` - Manages communication with both local (Ollama) and cloud (OpenRouter) AI models
- **Configuration Manager**: `src/core/config_manager.py` - Handles application settings and configuration
- **GUI Framework**: `src/gui/` - PyQt5-based user interface components

### Key Design Patterns
- **Modular Architecture**: Core functionality separated from GUI components
- **Dual AI Provider Support**: Seamless switching between local and cloud models
- **Async Operations**: Command execution and LLM queries use asyncio for non-blocking operations
- **Configuration-Driven**: All settings managed through centralized config system

### AI Integration
- Local models via Ollama API (default: gemma3:1b)
- Cloud models via OpenRouter API
- Intelligent command suggestions and error analysis
- Contextual help through natural language processing
- Dialog history management for conversation context

### Multi-Platform Support
- Cross-platform command handling (Windows cmd/PowerShell, Linux/macOS bash/zsh/fish)
- Platform-specific command aliases and security checks
- Dangerous command pattern detection and warnings

## Configuration Files
- `pyproject.toml` - Modern Python project configuration with uv support, dependencies, and tool settings
- `requirements.txt` - Legacy Python dependencies (PyQt5, aiohttp, asyncio, keyring, etc.)
- `~/.wrapd/config.ini` - User configuration file (created at runtime)
- `~/.wrapd/wrapd.log` - Application log file
- `resources/themes/` - CSS theme files for UI customization

## Key Dependencies
- PyQt5 (GUI framework)
- aiohttp (async HTTP client for API calls)
- keyring (secure API key storage)
- prompt_toolkit (command line interface enhancements)
- pygments (syntax highlighting)
- paramiko (SSH functionality)

## Development Notes
- **Package Management**: Uses uv for fast dependency management with fallback to pip
- **Project Structure**: Modern pyproject.toml configuration with development tools (black, mypy, pytest)
- **GUI Framework**: Qt's signal/slot mechanism for component communication
- **Performance**: Terminal widget supports real-time command output streaming
- **Customization**: Theme system supports custom CSS themes
- **AI Integration**: Command history and usage statistics are tracked for AI optimization
- **Security**: Dangerous command detection and confirmation prompts

## Development Workflow
- `uv venv` - Create virtual environment (faster than python -m venv)
- `uv pip install -e .` - Install package in development mode
- `uv sync` - Sync all dependencies including dev tools
- `uv run python src/main.py` - Run application through uv