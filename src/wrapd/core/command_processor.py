#!/usr/bin/env python3
# WRAPD: Command Processor for handling terminal commands

import os
import re
import sys
import platform
import subprocess
import difflib
import asyncio
import logging
from typing import Dict, List, Optional, Union, Any, Tuple

class CommandProcessor:
    """Process and execute terminal commands with AI assistance"""
    
    def __init__(self, config_manager, llm_interface):
        """Initialize the command processor
        
        Args:
            config_manager: Configuration manager instance
            llm_interface: LLM interface instance
        """
        self.config = config_manager
        self.llm = llm_interface
        self.logger = logging.getLogger("wrapd.command")
        
        # Command history
        self.history = []
        self.history_max_size = self.config.get_int('terminal', 'history_size', 1000)
        
        # Command usage statistics
        self.command_usage_count = {}
        
        # Determine OS family
        self.os_family = 'posix' if os.name == 'posix' else 'nt'
        
        # Command aliases
        self.command_aliases = self._load_command_aliases()
        
        # Supported commands by platform
        self.supported_commands = self._load_supported_commands()
        
        # Load common commands
        self.common_commands = self._load_common_commands()
        
        # Shell integration
        self.supported_shells = self._load_supported_shells()
    
    def _load_command_aliases(self):
        """Load command aliases from configuration
        
        Returns:
            dict: Command aliases mapping
        """
        # Default aliases
        aliases = {
            "ls": "dir" if self.os_family == 'nt' else "ls",
            "pwd": "cd" if self.os_family == 'nt' else "pwd",
            "rm": "del" if self.os_family == 'nt' else "rm",
            "cp": "copy" if self.os_family == 'nt' else "cp",
            "mv": "move" if self.os_family == 'nt' else "mv",
            "clear": "cls" if self.os_family == 'nt' else "clear",
            "cat": "type" if self.os_family == 'nt' else "cat",
        }
        
        # In our implementation, we don't need to load from config yet
        # We'll implement this in a future version
        
        return aliases
    
    def _load_supported_commands(self):
        """Load supported commands for current platform
        
        Returns:
            list: List of supported commands
        """
        if self.os_family == 'nt':
            return [
                "dir", "cd", "mkdir", "rmdir", "del", "copy", "move", "type", "ren", "xcopy",
                "attrib", "tree", "fsutil",
                "ipconfig", "ping", "netstat", "nslookup", "tracert", "arp", "route",
                "systeminfo", "whoami", "net", "tasklist", "taskkill",
                "diskpart", "format", "chkdsk", "vol", "mountvol",
                "icacls", "cacls",
                "shutdown", "restart", "sfc", "dism", "powercfg", "schtasks", "sc",
                "powershell", "wsl", "git", "python", "pip", "npm", "docker", "code"
            ]
        else:
            return [
                "ls", "cd", "pwd", "mkdir", "rm", "cp", "mv", "cat", "grep", "awk", "sed",
                "ps", "top", "kill", "ping", "ifconfig", "netstat", "ssh", "scp", "tar", "gzip",
                "apt", "apt-get", "yum", "dnf", "brew", "systemctl", "journalctl",
                "chmod", "chown", "chgrp", "ln", "df", "du", "find", "locate",
                "uname", "whoami", "id", "groups", "sudo", "su",
                "git", "python", "pip", "npm", "docker", "code"
            ]
    
    def _load_common_commands(self):
        """Load common commands for reference
        
        Returns:
            dict: Dictionary of command categories and their commands
        """
        return {
            'file': [
                "cd", "ls", "dir", "pwd", "mkdir", "rm", "rmdir", "del", "cp", "copy",
                "mv", "move", "cat", "type", "touch", "grep", "find", "chmod", "chown"
            ],
            'network': [
                "ping", "ifconfig", "ipconfig", "netstat", "nslookup", "tracert",
                "traceroute", "ssh", "scp", "curl", "wget"
            ],
            'system': [
                "ps", "top", "kill", "tasklist", "taskkill", "systemctl", "service",
                "shutdown", "reboot", "restart", "apt", "apt-get", "yum", "dnf", "brew"
            ],
            'development': [
                "git", "python", "pip", "npm", "node", "docker", "code", "make",
                "gcc", "g++"
            ]
        }
    
    def _load_supported_shells(self):
        """Load supported shells for the current platform
        
        Returns:
            dict: Dictionary of supported shells and their configurations
        """
        if self.os_family == 'nt':
            return {
                "cmd": {
                    "prefix": "",
                    "commands": self.supported_commands
                },
                "powershell": {
                    "prefix": "powershell -Command ",
                    "commands": [
                        "Get-Process", "Get-Service", "Start-Service", "Stop-Service",
                        "Get-ChildItem", "Set-Location", "New-Item", "Remove-Item"
                    ]
                },
                "wsl": {
                    "prefix": "wsl ",
                    "commands": [
                        "ls", "cd", "pwd", "mkdir", "rm", "cp", "mv", "cat", "grep"
                    ]
                }
            }
        else:
            shells = {
                "bash": {
                    "prefix": "",
                    "commands": self.supported_commands
                }
            }
            
            # Add zsh if available
            if os.path.exists("/bin/zsh") or os.path.exists("/usr/bin/zsh"):
                shells["zsh"] = {
                    "prefix": "/bin/zsh -c " if os.path.exists("/bin/zsh") else "/usr/bin/zsh -c ",
                    "commands": self.supported_commands
                }
            
            # Add fish if available
            if os.path.exists("/bin/fish") or os.path.exists("/usr/bin/fish"):
                shells["fish"] = {
                    "prefix": "/bin/fish -c " if os.path.exists("/bin/fish") else "/usr/bin/fish -c ",
                    "commands": self.supported_commands
                }
            
            return shells
    
    def get_system_commands(self):
        """Get available system commands from PATH
        
        Returns:
            list: List of available system commands
        """
        try:
            commands = []
            path_dirs = os.environ.get('PATH', '').split(os.pathsep)
            
            for path_dir in path_dirs:
                if os.path.exists(path_dir):
                    for file in os.listdir(path_dir):
                        file_path = os.path.join(path_dir, file)
                        if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                            commands.append(os.path.splitext(file)[0])
            
            return commands
        except Exception as e:
            self.logger.error(f"Error getting system commands: {str(e)}")
            return []
    
    def is_valid_command(self, command_text):
        """Check if a command is valid
        
        Args:
            command_text (str): Command text to check
        
        Returns:
            bool: True if valid command, False otherwise
        """
        if not command_text:
            return False
        
        parts = command_text.split()
        base_command = parts[0]
        
        # Check if command is in supported commands or aliases
        if base_command in self.supported_commands or base_command in self.command_aliases:
            return True
        
        # Check if command is available in PATH
        system_commands = self.get_system_commands()
        return base_command in system_commands
    
    def correct_command(self, command_text):
        """Suggest correction for a command
        
        Args:
            command_text (str): Command text to correct
        
        Returns:
            tuple: (corrected_command, is_corrected)
        """
        if not command_text:
            return command_text, False
        
        parts = command_text.split()
        base_command = parts[0]
        
        # If command is already valid, no correction needed
        if self.is_valid_command(command_text):
            return command_text, False
        
        # Get all possible commands
        all_commands = self.supported_commands + list(self.command_aliases.keys()) + self.get_system_commands()
        
        # Find similar commands
        matches = difflib.get_close_matches(base_command, all_commands, n=1, cutoff=0.6)
        
        if matches:
            corrected_command = " ".join([matches[0]] + parts[1:])
            return corrected_command, True
        
        return command_text, False
    
    async def execute_command(self, command_text, terminal_output_callback=None):
        """Execute a command
        
        Args:
            command_text (str): Command to execute
            terminal_output_callback (callable, optional): Callback for terminal output
        
        Returns:
            tuple: (success, output, error)
        """
        if not command_text:
            return False, "", "No command provided"
        
        # Add to history
        self._add_to_history(command_text)
        
        # Process command text
        parts = command_text.split()
        base_command = parts[0]
        
        # Handle command aliases
        if base_command in self.command_aliases:
            alias_value = self.command_aliases[base_command]
            command_text = alias_value + " " + " ".join(parts[1:])
            parts = command_text.split()
            base_command = parts[0]
            
            if terminal_output_callback:
                terminal_output_callback(f"Alias: {base_command} -> {alias_value}\n")
        
        # Track command usage
        self._track_command_usage(base_command)
        
        # Process special commands (help, cd, etc.)
        if len(parts) > 1 and parts[1].lower() in ["help", "?", "--help", "-h"]:
            return await self._handle_help_command(base_command, terminal_output_callback)
        
        # Handle built-in commands
        if base_command == "cd":
            return self._handle_cd_command(command_text, terminal_output_callback)
        elif base_command in ["clear", "cls"]:
            if terminal_output_callback:
                terminal_output_callback("\033c")  # ANSI escape code to clear screen
            return True, "", ""
        elif base_command == "exit" or base_command == "quit":
            # This should be handled by the caller
            return True, "exit", ""
        
        # Execute external command
        return await self._execute_external_command(command_text, terminal_output_callback)
    
    def _add_to_history(self, command_text):
        """Add command to history
        
        Args:
            command_text (str): Command to add to history
        """
        self.history.append(command_text)
        
        # Limit history size
        if len(self.history) > self.history_max_size:
            self.history = self.history[-self.history_max_size:]
    
    def _track_command_usage(self, command):
        """Track command usage frequency
        
        Args:
            command (str): Command to track
        """
        self.command_usage_count[command] = self.command_usage_count.get(command, 0) + 1
    
    async def _handle_help_command(self, command, terminal_output_callback):
        """Handle help request for a command
        
        Args:
            command (str): Command to get help for
            terminal_output_callback (callable, optional): Callback for terminal output
        
        Returns:
            tuple: (success, output, error)
        """
        prompt = f"Please explain the '{command}' command, its common usage, and important options."
        
        if terminal_output_callback:
            terminal_output_callback(f"Getting help for '{command}'...\n")
        
        response = await self.llm.get_response(prompt)
        
        if terminal_output_callback:
            terminal_output_callback(f"\n{response}\n")
        
        return True, response, ""
    
    def _handle_cd_command(self, command_text, terminal_output_callback):
        """Handle cd command to change directory
        
        Args:
            command_text (str): Full command text
            terminal_output_callback (callable, optional): Callback for terminal output
        
        Returns:
            tuple: (success, output, error)
        """
        parts = command_text.split()
        
        # Default to home directory if no path provided
        if len(parts) == 1:
            path = os.path.expanduser("~")
        else:
            path = " ".join(parts[1:])
            
            # Handle tilde expansion for home directory
            if path.startswith("~"):
                path = os.path.expanduser(path)
        
        try:
            os.chdir(path)
            new_path = os.getcwd()
            
            if terminal_output_callback:
                terminal_output_callback(f"Changed directory to: {new_path}\n")
            
            return True, new_path, ""
        except Exception as e:
            error_msg = f"Failed to change directory: {str(e)}"
            
            if terminal_output_callback:
                terminal_output_callback(f"Error: {error_msg}\n")
            
            return False, "", error_msg
    
    async def _execute_external_command(self, command_text, terminal_output_callback):
        """Execute an external command
        
        Args:
            command_text (str): Command to execute
            terminal_output_callback (callable, optional): Callback for terminal output
        
        Returns:
            tuple: (success, output, error)
        """
        # Security check for potentially dangerous commands
        if self._is_dangerous_command(command_text):
            warning = (
                f"Warning: The command '{command_text}' may be potentially dangerous. "
                "Please double-check before proceeding. "
                "Type 'confirm' to proceed or anything else to cancel."
            )
            
            if terminal_output_callback:
                terminal_output_callback(f"{warning}\n")
            
            return False, "", warning
        
        # Determine shell and command prefix
        shell_name = self.config.get('terminal', 'default_shell', '')
        shell_info = self.supported_shells.get(shell_name, None)
        
        if not shell_info:
            # Default to system shell
            shell = True
            prefix = ""
        else:
            shell = True
            prefix = shell_info["prefix"]
        
        # Prepare command
        full_command = f"{prefix}{command_text}".strip()
        
        try:
            process = await asyncio.create_subprocess_shell(
                full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=shell
            )
            
            # Process output in real-time
            while True:
                # Check if there's any stdout data
                line = await process.stdout.readline()
                if line:
                    output_line = line.decode('utf-8', errors='replace')
                    if terminal_output_callback:
                        terminal_output_callback(output_line)
                
                # Check if there's any stderr data
                error_line = await process.stderr.readline()
                if error_line:
                    error_output = error_line.decode('utf-8', errors='replace')
                    if terminal_output_callback:
                        terminal_output_callback(error_output)
                
                # If both are empty, process has likely completed
                if not line and not error_line:
                    break
            
            # Wait for process to complete
            await process.wait()
            
            # Get any remaining output
            stdout, stderr = await process.communicate()
            
            if stdout:
                output = stdout.decode('utf-8', errors='replace')
                if terminal_output_callback:
                    terminal_output_callback(output)
            else:
                output = ""
            
            if stderr:
                error = stderr.decode('utf-8', errors='replace')
                if terminal_output_callback:
                    terminal_output_callback(error)
            else:
                error = ""
            
            # Check if command execution was successful
            success = process.returncode == 0
            
            # Log command execution
            self.logger.info(f"Command executed: '{full_command}', success: {success}")
            
            # If command failed and we have error output, send to LLM for analysis
            if not success and error:
                await self._analyze_command_error(command_text, error, terminal_output_callback)
            
            return success, output, error
            
        except Exception as e:
            error_msg = f"Failed to execute command: {str(e)}"
            self.logger.error(error_msg)
            
            if terminal_output_callback:
                terminal_output_callback(f"Error: {error_msg}\n")
            
            return False, "", error_msg
    
    def _is_dangerous_command(self, command_text):
        """Check if a command is potentially dangerous
        
        Args:
            command_text (str): Command to check
        
        Returns:
            bool: True if command is potentially dangerous
        """
        dangerous_patterns = [
            r'\brm\s+(-rf?|--recursive)\s+[/\\]',
            r'\bformat\s+[a-zA-Z]:',
            r'\bdd\s+.*\bof=/dev/(hd|sd|mmcblk)',
            r'\bmkfs\..*\s+/dev/',
            r'\b(shutdown|reboot|halt)\b',
            r'\bchmod\s+777\b',
            r'>(>)?\s*/dev/(null|zero|random|urandom)',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command_text, re.IGNORECASE):
                return True
        
        return False
    
    async def _analyze_command_error(self, command, error, terminal_output_callback):
        """Use LLM to analyze command error
        
        Args:
            command (str): Command that failed
            error (str): Error output
            terminal_output_callback (callable, optional): Callback for terminal output
        """
        # Skip analysis if error is too short or empty
        if not error or len(error.strip()) < 5:
            return
        
        prompt = (
            f"The command '{command}' failed with the following error:\n"
            f"{error}\n\n"
            "What does this error mean, and how can I fix it? "
            "Please provide a concise explanation and suggest a solution."
        )
        
        if terminal_output_callback:
            terminal_output_callback("\n💡 Analyzing error...\n")
        
        response = await self.llm.get_response(prompt)
        
        if terminal_output_callback:
            terminal_output_callback(f"\n💡 {response}\n")
    
    async def get_command_suggestions(self, partial_command):
        """Get AI-powered command suggestions
        
        Args:
            partial_command (str): Partial command to get suggestions for
        
        Returns:
            list: List of command suggestions
        """
        # If empty, return most used commands
        if not partial_command:
            return self._get_most_used_commands(5)
        
        # If it's just the beginning of a command, return matching commands
        parts = partial_command.split()
        if len(parts) == 1:
            return self._get_matching_commands(parts[0])
        
        # For more complex command completion, use LLM
        prompt = (
            f"I'm trying to complete this command: '{partial_command}'. "
            "Suggest up to 3 possible completions that make sense. "
            "Return only the commands, one per line, without explanations."
        )
        
        response = await self.llm.get_response(prompt)
        
        # Parse response into list of commands
        suggestions = []
        for line in response.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                suggestions.append(line)
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    def _get_most_used_commands(self, count=5):
        """Get most frequently used commands
        
        Args:
            count (int): Number of commands to return
        
        Returns:
            list: List of most used commands
        """
        sorted_commands = sorted(
            self.command_usage_count.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [cmd for cmd, _ in sorted_commands[:count]]
    
    def _get_matching_commands(self, prefix):
        """Get commands matching a prefix
        
        Args:
            prefix (str): Command prefix to match
        
        Returns:
            list: List of matching commands
        """
        all_commands = (
            self.supported_commands +
            list(self.command_aliases.keys()) +
            self.get_system_commands()
        )
        
        # Remove duplicates
        all_commands = list(set(all_commands))
        
        # Find matching commands
        matching = [cmd for cmd in all_commands if cmd.startswith(prefix)]
        
        # Sort by usage frequency
        return sorted(
            matching,
            key=lambda cmd: self.command_usage_count.get(cmd, 0),
            reverse=True
        )
    
    def get_history(self):
        """Get command history
        
        Returns:
            list: Command history
        """
        return self.history
    
    def clear_history(self):
        """Clear command history"""
        self.history = []
