#!/usr/bin/env python3
# WRAPD: Local Launcher Script
# This script can be used to launch WRAPD on your local machine

import os
import sys
import subprocess
import platform
import argparse
import time

def print_banner():
    """Print the WRAPD banner"""
    banner = """
\033[34m
██╗    ██╗██████╗  █████╗ ██████╗ ██████╗ 
██║    ██║██╔══██╗██╔══██╗██╔══██╗██╔══██╗
██║ █╗ ██║██████╔╝███████║██████╔╝██║  ██║
██║███╗██║██╔══██╗██╔══██║██╔═══╝ ██║  ██║
╚███╔███╔╝██║  ██║██║  ██║██║     ██████╔╝
 ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═════╝ 
\033[0m
Warp Replacement with AI-Powered Delivery
Version 1.0.0
------------------------------------------
"""
    print(banner)

def check_uv_available():
    """Check if uv is available and install if needed"""
    try:
        subprocess.check_output(["uv", "--version"], stderr=subprocess.DEVNULL)
        print("\033[32muv is available.\033[0m")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\033[33muv is not installed. Installing uv...\033[0m")
        try:
            # Install uv using the official installer
            if platform.system() == "Windows":
                subprocess.check_call(["powershell", "-Command", "irm https://astral.sh/uv/install.ps1 | iex"])
            else:
                subprocess.check_call(["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"])
            
            # Add to PATH for current session
            if platform.system() != "Windows":
                cargo_bin = os.path.expanduser("~/.cargo/bin")
                if cargo_bin not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = f"{cargo_bin}:{os.environ.get('PATH', '')}"
            
            # Check again
            subprocess.check_output(["uv", "--version"], stderr=subprocess.DEVNULL)
            print("\033[32muv installed successfully.\033[0m")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("\033[33mFailed to install uv. Falling back to pip.\033[0m")
            return False

def check_dependencies():
    """Check for required dependencies"""
    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 8):
        print("\033[31mError: Python 3.8 or higher is required.\033[0m")
        print(f"Current Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
        sys.exit(1)
    
    print(f"\033[32mPython {python_version.major}.{python_version.minor}.{python_version.micro} found.\033[0m")
    
    # Check for uv
    uv_available = check_uv_available()
    
    # Check for PyQt5
    try:
        import PyQt5
        print("\033[32mPyQt5 is installed.\033[0m")
    except ImportError:
        print("\033[31mError: PyQt5 is not installed.\033[0m")
        print("Please install PyQt5 with: pip install PyQt5")
        sys.exit(1)
    
    # Check for other required modules
    required_modules = ["aiohttp", "asyncio", "keyring"]
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"\033[32m{module} is installed.\033[0m")
        except ImportError:
            missing_modules.append(module)
            print(f"\033[33m{module} is not installed.\033[0m")
    
    if missing_modules:
        print("\033[33mSome modules are missing. Installing...\033[0m")
        for module in missing_modules:
            try:
                if uv_available:
                    subprocess.check_call(["uv", "pip", "install", module])
                else:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", module])
                print(f"\033[32mInstalled {module}.\033[0m")
            except subprocess.CalledProcessError:
                print(f"\033[31mFailed to install {module}.\033[0m")
                install_cmd = f"uv pip install {module}" if uv_available else f"pip install {module}"
                print(f"Please install {module} manually with: {install_cmd}")
    
    # Check for Ollama (optional)
    ollama_path = None
    
    if platform.system() == "Windows":
        # On Windows, check in Program Files
        possible_paths = [
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Ollama", "ollama.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Ollama", "ollama.exe")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                ollama_path = path
                break
    else:
        # On Unix-like systems, check in PATH
        try:
            ollama_path = subprocess.check_output(["which", "ollama"], universal_newlines=True).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            ollama_path = None
    
    if ollama_path:
        print(f"\033[32mOllama found at: {ollama_path}\033[0m")
        has_ollama = True
    else:
        print("\033[33mOllama not found.\033[0m")
        print("For local AI models, please install Ollama from https://ollama.com/")
        print("WRAPD will use OpenRouter (cloud) models instead.")
        has_ollama = False
    
    return uv_available, has_ollama

def check_ollama_running():
    """Check if Ollama is running"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_ollama():
    """Start Ollama if it's installed but not running"""
    if platform.system() == "Windows":
        # On Windows, start Ollama through PowerShell
        try:
            subprocess.Popen(["powershell", "-Command", "Start-Process ollama serve -WindowStyle Hidden"])
            print("\033[34mStarting Ollama...\033[0m")
            return True
        except:
            return False
    else:
        # On Unix-like systems, start Ollama directly
        try:
            subprocess.Popen(["ollama", "serve"])
            print("\033[34mStarting Ollama...\033[0m")
            return True
        except:
            return False

def pull_gemma_model():
    """Pull the Gemma 3 1B model if it's not already installed"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        
        if response.status_code == 200:
            models = response.json().get("models", [])
            
            # Check if Gemma 3 1B is in the list of models
            for model in models:
                if model.get("name") == "gemma3:1b":
                    print("\033[32mGemma 3 1B model is already installed.\033[0m")
                    return True
            
            # If we get here, we need to pull the model
            print("\033[34mPulling Gemma 3 1B model...\033[0m")
            subprocess.run(["ollama", "pull", "gemma3:1b"], check=True)
            print("\033[32mGemma 3 1B model installed successfully.\033[0m")
            return True
    except:
        print("\033[33mFailed to pull Gemma 3 1B model.\033[0m")
        print("WRAPD will use OpenRouter (cloud) models instead.")
        return False

def launch_wrapd(script_dir, no_ollama=False):
    """Launch the WRAPD application"""
    main_script = os.path.join(script_dir, "src", "main.py")
    
    if not os.path.exists(main_script):
        print(f"\033[31mError: Main script not found at {main_script}\033[0m")
        sys.exit(1)
    
    print("\033[34mLaunching WRAPD...\033[0m")
    
    # Use pythonw on Windows to avoid console window
    if platform.system() == "Windows":
        python_exe = os.path.join(sys.prefix, "pythonw.exe")
        if not os.path.exists(python_exe):
            python_exe = sys.executable
    else:
        python_exe = sys.executable
    
    # Launch the application
    args = [python_exe, main_script]
    if no_ollama:
        args.append("--no-ollama")
    
    subprocess.Popen(args)
    print("\033[32mWRAPD launched successfully!\033[0m")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="WRAPD Local Launcher")
    parser.add_argument("--no-ollama", "-n", action="store_true", help="Skip Ollama check and use OpenRouter")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")
    args = parser.parse_args()
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Print banner
    print_banner()
    
    # Check dependencies
    if not args.no_ollama:
        uv_available, has_ollama = check_dependencies()
        
        if has_ollama:
            # Check if Ollama is running
            if not check_ollama_running():
                print("\033[33mOllama is not running.\033[0m")
                
                # Try to start Ollama
                if start_ollama():
                    # Wait for Ollama to start
                    print("\033[34mWaiting for Ollama to start...\033[0m")
                    for i in range(10):
                        if check_ollama_running():
                            print("\033[32mOllama started successfully.\033[0m")
                            break
                        
                        if i == 9:
                            print("\033[33mFailed to start Ollama. Will use OpenRouter instead.\033[0m")
                            break
                        
                        print(f"Waiting... ({i+1}/10)")
                        time.sleep(1)
                else:
                    print("\033[33mFailed to start Ollama. Will use OpenRouter instead.\033[0m")
            else:
                print("\033[32mOllama is already running.\033[0m")
            
            # Check for Gemma 3
            if check_ollama_running():
                pull_gemma_model()