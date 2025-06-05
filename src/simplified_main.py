#!/usr/bin/env python3
# WRAPD: Simplified version for easier testing

import os
import sys
import asyncio
import aiohttp
import platform
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("wrapd")

# Constants
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".wrapd")
os.makedirs(CONFIG_DIR, exist_ok=True)

class Config:
    """Simple configuration class"""
    
    def __init__(self):
        self.config = {
            'provider': 'local',
            'model': 'gemma3:1b',
            'temperature': 0.1,
            'max_tokens': 256
        }
    
    def get(self, key, default=None):
        return self.config.get(key, default)

class WRAPDTerminal:
    """Simple WRAPD terminal implementation"""
    
    def __init__(self):
        self.config = Config()
        
    async def start(self):
        """Start the terminal"""
        print("=" * 50)
        print("WRAPD Terminal".center(50))
        print("=" * 50)
        print("A Warp Terminal Replacement with AI-Powered Delivery")
        print("Version 1.0.0")
        print()
        
        # Check if Ollama is running
        if self.config.get('provider') == 'local':
            ollama_running = await self._check_ollama()
            if ollama_running:
                print(f"✓ Ollama is running and using {self.config.get('model')}")
            else:
                print("✗ Ollama is not running. Switch to OpenRouter or start Ollama.")
        else:
            print(f"Using OpenRouter with model: {self.config.get('model')}")
        
        print()
        print("Type 'exit' to quit or 'help' for assistance.")
        print()
        
        # Start command loop
        await self._command_loop()
    
    async def _check_ollama(self):
        """Check if Ollama is running"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:11434/api/tags") as response:
                    if response.status == 200:
                        return True
                    return False
        except:
            return False
    
    async def _command_loop(self):
        """Command processing loop"""
        while True:
            # Display prompt
            username = os.getlogin()
            current_dir = os.getcwd()
            print(f"\033[94m{username}@{platform.node()}\033[0m:\033[92m{current_dir}\033[0m$ ", end="")
            
            # Get command
            command = input().strip()
            
            # Handle exit
            if command.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
            
            # Handle help
            if command.lower() == 'help':
                await self._show_help()
                continue
            
            # Handle empty command
            if not command:
                continue
            
            # Handle cd command
            if command.startswith('cd '):
                path = command[3:].strip()
                try:
                    os.chdir(path)
                    print(f"Changed directory to: {os.getcwd()}")
                except Exception as e:
                    print(f"Error: {str(e)}")
                continue
            
            # Handle clear command
            if command in ['clear', 'cls']:
                os.system('cls' if os.name == 'nt' else 'clear')
                continue
            
            # Handle model command
            if command.startswith('model '):
                model_name = command[6:].strip()
                self.config.config['model'] = model_name
                print(f"Changed model to: {model_name}")
                continue
            
            # Handle AI query (commands starting with '?')
            if command.startswith('?'):
                query = command[1:].strip()
                response = await self._get_ai_response(query)
                print(f"\n\033[96m{response}\033[0m\n")
                continue
            
            # Handle regular command
            try:
                result = os.system(command)
                if result != 0:
                    print(f"Command exited with status: {result}")
            except Exception as e:
                print(f"Error executing command: {str(e)}")
    
    async def _get_ai_response(self, query):
        """Get response from AI model"""
        if self.config.get('provider') == 'local':
            return await self._get_local_ai_response(query)
        else:
            return await self._get_openrouter_response(query)
    
    async def _get_local_ai_response(self, query):
        """Get response from local model via Ollama"""
        try:
            api_url = "http://localhost:11434/api/chat"
            
            data = {
                "model": self.config.get('model'),
                "messages": [{"role": "user", "content": query}],
                "temperature": self.config.get('temperature'),
                "max_tokens": self.config.get('max_tokens'),
                "stream": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=data) as response:
                    if response.status != 200:
                        return f"Error: API returned status code {response.status}"
                    
                    result = await response.json()
                    return result.get("message", {}).get("content", "No response")
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def _get_openrouter_response(self, query):
        """Get response from OpenRouter"""
        return "OpenRouter integration is not implemented in this simplified version.\nPlease set up the full application for OpenRouter support."
    
    async def _show_help(self):
        """Show help text"""
        print("\nWRAPD Terminal Help:")
        print("--------------------")
        print("Basic Commands:")
        print("  exit, quit          Exit the terminal")
        print("  clear, cls          Clear the screen")
        print("  help                Show this help message")
        print("\nNavigation:")
        print("  cd <path>           Change directory")
        print("\nAI Commands:")
        print("  ? <query>           Ask the AI a question")
        print("  model <model_name>  Change the AI model")
        print("\nExamples:")
        print("  ? What is the unix command to list files?")
        print("  ? How do I create a new directory in bash?")
        print("  model gemma3:1b")
        print()

async def main():
    """Main entry point"""
    terminal = WRAPDTerminal()
    await terminal.start()

if __name__ == "__main__":
    asyncio.run(main())
