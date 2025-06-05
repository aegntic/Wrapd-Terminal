#!/usr/bin/env python3
# WRAPD: Terminal Widget Component

import os
import sys
import re
import asyncio
import threading
import platform
import logging
from datetime import datetime
from functools import partial
from pathlib import Path

# PyQt5 imports
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                           QLineEdit, QCompleter, QLabel, QScrollBar, 
                           QSizePolicy, QFrame, QToolTip, QMenu, QAction)
from PyQt5.QtGui import (QFont, QColor, QTextCursor, QKeySequence, 
                        QSyntaxHighlighter, QTextCharFormat, QPalette, 
                        QContextMenuEvent)
from PyQt5.QtCore import (Qt, QThread, pyqtSignal, QStringListModel, 
                         QTimer, QEvent, QObject, QRect)

class CommandInputHandler(QObject):
    """Command input handler for the terminal widget
    
    Handles command completion, history navigation, and other input events.
    """
    
    def __init__(self, input_field, completer, command_processor, parent=None):
        """Initialize the command input handler
        
        Args:
            input_field (QLineEdit): Command input field
            completer (QCompleter): Command completer
            command_processor: Command processor instance
            parent (QObject, optional): Parent object
        """
        super().__init__(parent)
        
        self.input_field = input_field
        self.completer = completer
        self.command_processor = command_processor
        
        # Command history
        self.history = []
        self.history_index = -1
        
        # Cached partial commands for history navigation
        self.current_input = ""
        
        # Connect signals
        if self.completer:
            self.completer.activated.connect(self.complete_command)
    
    def eventFilter(self, obj, event):
        """Event filter for command input field
        
        Args:
            obj (QObject): Object that triggered the event
            event (QEvent): Event object
        
        Returns:
            bool: True if event was handled, False otherwise
        """
        if obj is self.input_field and event.type() == QEvent.KeyPress:
            # Handle key press events
            key = event.key()
            
            if key == Qt.Key_Up:
                # Navigate to previous command in history
                self.navigate_history(-1)
                return True
            
            elif key == Qt.Key_Down:
                # Navigate to next command in history
                self.navigate_history(1)
                return True
            
            elif key == Qt.Key_Tab:
                # Handle tab completion
                if self.completer and not self.completer.popup().isVisible():
                    self.show_completion()
                    return True
            
            elif key == Qt.Key_Escape:
                # Clear input field
                self.input_field.clear()
                return True
        
        # Let parent handle the event
        return super().eventFilter(obj, event)
    
    def update_history(self, history):
        """Update command history
        
        Args:
            history (list): Command history
        """
        self.history = history
        self.history_index = len(self.history)
    
    def navigate_history(self, direction):
        """Navigate through command history
        
        Args:
            direction (int): Direction to navigate (1 for next, -1 for previous)
        """
        if not self.history:
            return
        
        if self.history_index == len(self.history) and direction < 0:
            # Save current input when navigating up from bottom
            self.current_input = self.input_field.text()
        
        # Calculate new index within bounds
        new_index = max(0, min(len(self.history), self.history_index + direction))
        
        if new_index == len(self.history):
            # At the bottom of history, restore current input
            self.input_field.setText(self.current_input)
        elif 0 <= new_index < len(self.history):
            # Set text to history item
            self.input_field.setText(self.history[new_index])
        
        # Update index
        self.history_index = new_index
        
        # Move cursor to end of text
        self.input_field.setCursorPosition(len(self.input_field.text()))
    
    def show_completion(self):
        """Show command completion popup"""
        if not self.completer:
            return
        
        # Get current text
        text = self.input_field.text()
        
        # Update completer model with completion options
        self.update_completer_model(text)
        
        # Show completer popup
        self.completer.setCompletionPrefix(text)
        
        if self.completer.completionCount() > 0:
            popup = self.completer.popup()
            popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
            
            # Calculate popup position
            rect = self.input_field.rect()
            rect.setWidth(self.completer.popup().sizeHintForColumn(0)
                + self.completer.popup().verticalScrollBar().sizeHint().width())
            rect.moveTo(self.input_field.mapToGlobal(rect.topLeft()))
            
            # Show popup
            self.completer.complete(rect)
    
    def update_completer_model(self, text):
        """Update completer model with command suggestions
        
        Args:
            text (str): Current input text
        """
        if not self.completer:
            return
        
        # Use command processor to get suggestions
        suggestions = []
        
        # Get basic command completions
        if text:
            parts = text.split()
            if len(parts) == 1:
                # Complete base command
                base_cmd = parts[0]
                matching_commands = [cmd for cmd in self.command_processor.supported_commands
                                    if cmd.startswith(base_cmd)]
                
                # Add matching aliases
                matching_aliases = [alias for alias in self.command_processor.command_aliases.keys()
                                   if alias.startswith(base_cmd)]
                
                # Combine and sort by usage frequency
                all_matches = matching_commands + matching_aliases
                all_matches.sort(key=lambda cmd: self.command_processor.command_usage_count.get(cmd, 0),
                               reverse=True)
                
                suggestions.extend(all_matches[:10])  # Limit to top 10
        
        # Update the model
        model = QStringListModel(suggestions)
        self.completer.setModel(model)
    
    def complete_command(self, text):
        """Complete command with selected completion
        
        Args:
            text (str): Completion text
        """
        self.input_field.setText(text)
        self.input_field.setFocus()

class TerminalWidget(QWidget):
    """Terminal emulator widget for WRAPD
    
    Provides terminal display and command input with AI assistance.
    """
    
    # Signals
    commandExecuted = pyqtSignal(str)  # Signal emitted when a command is executed
    statusMessage = pyqtSignal(str)  # Signal emitted when a status message is set
    
    def __init__(self, config_manager, llm_interface, command_processor, parent=None):
        """Initialize the terminal widget
        
        Args:
            config_manager: Configuration manager instance
            llm_interface: LLM interface instance
            command_processor: Command processor instance
            parent (QWidget, optional): Parent widget
        """
        super().__init__(parent)
        
        self.config = config_manager
        self.llm = llm_interface
        self.command_processor = command_processor
        self.logger = logging.getLogger("wrapd.terminal")
        
        # Terminal state
        self._command_running = False
        self._last_command = ""
        
        # Set up UI
        self._setup_ui()
        
        # Load command history
        self._load_history()
        
        # Start with prompt
        self._print_prompt()
    
    def _setup_ui(self):
        """Set up the UI components"""
        # Main layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)
        
        # Terminal display
        self.terminal_display = QTextEdit()
        self.terminal_display.setReadOnly(True)
        self.terminal_display.setFrameStyle(QFrame.NoFrame)
        self.terminal_display.setAcceptRichText(True)
        self.terminal_display.setUndoRedoEnabled(False)
        
        # Set font
        font_family = self.config.get('appearance', 'font_family', 'Consolas, Menlo, monospace')
        font_size = self.config.get_int('appearance', 'font_size', 12)
        self.terminal_font = QFont(font_family.split(',')[0].strip())
        self.terminal_font.setPointSize(font_size)
        self.terminal_font.setStyleHint(QFont.Monospace)
        self.terminal_display.setFont(self.terminal_font)
        
        # Add terminal display to layout
        self.layout.addWidget(self.terminal_display, 1)
        
        # Input area layout
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(5, 5, 5, 5)
        input_layout.setSpacing(5)
        
        # Command prompt label
        self.prompt_label = QLabel("$ ")
        self.prompt_label.setFont(self.terminal_font)
        input_layout.addWidget(self.prompt_label)
        
        # Command input field
        self.command_input = QLineEdit()
        self.command_input.setFont(self.terminal_font)
        self.command_input.setFrame(False)
        self.command_input.returnPressed.connect(self._execute_command)
        input_layout.addWidget(self.command_input, 1)
        
        # Input area container
        input_container = QWidget()
        input_container.setLayout(input_layout)
        
        # Add input area to main layout
        self.layout.addWidget(input_container, 0)
        
        # Set up completer
        self.completer = QCompleter()
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setWidget(self.command_input)
        
        # Set up input handler
        self.input_handler = CommandInputHandler(
            self.command_input,
            self.completer,
            self.command_processor
        )
        self.command_input.installEventFilter(self.input_handler)
    
    def _load_history(self):
        """Load command history from command processor"""
        history = self.command_processor.get_history()
        self.input_handler.update_history(history)
    
    def _print_prompt(self):
        """Print command prompt to terminal display"""
        # Get current path
        current_path = os.getcwd()
        
        # Get username
        try:
            username = os.getlogin()
        except:
            username = "user"
        
        # Get hostname
        try:
            hostname = platform.node()
        except:
            hostname = "localhost"
        
        # Create prompt
        prompt = f"<span style='color:#00aaff;'>{username}@{hostname}</span>:<span style='color:#00aa00;'>{current_path}</span>$ "
        
        # Print to terminal
        self.terminal_display.append(prompt)
        
        # Scroll to bottom
        self.terminal_display.moveCursor(QTextCursor.End)
    
    async def _execute_command_async(self, command):
        """Execute a command asynchronously
        
        Args:
            command (str): Command to execute
        """
        if not command.strip():
            # Empty command, just print prompt
            self._print_prompt()
            return
        
        # Set command running state
        self._command_running = True
        self._last_command = command
        
        # Print command to terminal
        self.terminal_display.textCursor().insertText(command)
        self.terminal_display.append("")
        
        # Execute command
        terminal_output_callback = self._handle_terminal_output
        success, output, error = await self.command_processor.execute_command(
            command,
            terminal_output_callback
        )
        
        # Special case for exit/quit command
        if output == "exit" or command.strip() in ["exit", "quit"]:
            # Close application
            window = self.window()
            window.close()
            return
        
        # Check if we need to update the prompt (e.g., after cd command)
        if command.strip().startswith("cd "):
            # Update window title with new path
            self.commandExecuted.emit(command)
        
        # Reset command running state
        self._command_running = False
        
        # Print prompt
        self._print_prompt()
        
        # Focus on command input
        self.command_input.setFocus()
    
    def _execute_command(self):
        """Execute the current command in the input field"""
        # Get command text
        command = self.command_input.text()
        
        # Clear input field
        self.command_input.clear()
        
        # Run command asynchronously
        try:
            # Try to get the running event loop
            loop = asyncio.get_event_loop()
            
            # Check if the loop is running
            if loop.is_running():
                # Create a future to run in the existing loop
                asyncio.run_coroutine_threadsafe(self._execute_command_async(command), loop)
            else:
                # Run the coroutine in the loop
                loop.run_until_complete(self._execute_command_async(command))
        except RuntimeError:
            # No event loop in this thread, create a new one
            self.logger.debug("Creating new event loop for command execution")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the coroutine in the new loop
            loop.run_until_complete(self._execute_command_async(command))
    
    def _handle_terminal_output(self, text):
        """Handle terminal output from command execution
        
        Args:
            text (str): Output text
        """
        # Convert ANSI color codes to HTML
        text = self._ansi_to_html(text)
        
        # Insert text
        cursor = self.terminal_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(text)
        
        # Scroll to bottom
        self.terminal_display.setTextCursor(cursor)
        self.terminal_display.ensureCursorVisible()
    
    def _ansi_to_html(self, text):
        """Convert ANSI color codes to HTML
        
        Args:
            text (str): Text with ANSI color codes
        
        Returns:
            str: HTML formatted text
        """
        # ANSI color to CSS color map
        color_map = {
            '30': 'black',
            '31': 'red',
            '32': 'green',
            '33': 'yellow',
            '34': 'blue',
            '35': 'magenta',
            '36': 'cyan',
            '37': 'white',
            '90': '#888888',
            '91': '#ff0000',
            '92': '#00ff00',
            '93': '#ffff00',
            '94': '#0000ff',
            '95': '#ff00ff',
            '96': '#00ffff',
            '97': '#ffffff',
        }
        
        # Replace ANSI escape sequences with HTML
        result = ""
        parts = re.split(r'\033\[([\d;]+)m', text)
        
        if len(parts) == 1:
            # No ANSI codes
            return text.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        
        # Current text style
        current_color = None
        is_bold = False
        
        # Process parts
        i = 0
        while i < len(parts):
            if i % 2 == 0:
                # Text part
                part = parts[i].replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
                
                # Apply current style
                if current_color or is_bold:
                    style = []
                    if current_color:
                        style.append(f"color:{current_color}")
                    if is_bold:
                        style.append("font-weight:bold")
                    
                    result += f"<span style='{';'.join(style)}'>{part}</span>"
                else:
                    result += part
            else:
                # ANSI code part
                codes = parts[i].split(';')
                
                for code in codes:
                    if code == '0':
                        # Reset
                        current_color = None
                        is_bold = False
                    elif code == '1':
                        # Bold
                        is_bold = True
                    elif code in color_map:
                        # Foreground color
                        current_color = color_map[code]
            
            i += 1
        
        return result
    
    def copy_selection(self):
        """Copy selected text to clipboard"""
        self.terminal_display.copy()
    
    def paste_clipboard(self):
        """Paste clipboard content to input field"""
        self.command_input.paste()
    
    def select_all(self):
        """Select all text in terminal display"""
        self.terminal_display.selectAll()
    
    def clear(self):
        """Clear the terminal display"""
        self.terminal_display.clear()
        self._print_prompt()
    
    def increase_font_size(self):
        """Increase the font size"""
        current_size = self.terminal_font.pointSize()
        new_size = min(current_size + 1, 36)  # Max 36pt
        
        if new_size != current_size:
            self._set_font_size(new_size)
    
    def decrease_font_size(self):
        """Decrease the font size"""
        current_size = self.terminal_font.pointSize()
        new_size = max(current_size - 1, 6)  # Min 6pt
        
        if new_size != current_size:
            self._set_font_size(new_size)
    
    def reset_font_size(self):
        """Reset the font size to default"""
        default_size = self.config.get_int('appearance', 'font_size', 12)
        current_size = self.terminal_font.pointSize()
        
        if default_size != current_size:
            self._set_font_size(default_size)
    
    def _set_font_size(self, size):
        """Set the font size
        
        Args:
            size (int): Font size
        """
        # Update font
        self.terminal_font.setPointSize(size)
        
        # Apply to widgets
        self.terminal_display.setFont(self.terminal_font)
        self.command_input.setFont(self.terminal_font)
        self.prompt_label.setFont(self.terminal_font)
        
        # Update config
        self.config.set('appearance', 'font_size', str(size))
    
    def contextMenuEvent(self, event):
        """Handle context menu event
        
        Args:
            event (QContextMenuEvent): Context menu event
        """
        # Create context menu
        menu = QMenu(self)
        
        # Add actions
        copy_action = menu.addAction("Copy")
        paste_action = menu.addAction("Paste")
        select_all_action = menu.addAction("Select All")
        menu.addSeparator()
        clear_action = menu.addAction("Clear Terminal")
        
        # Execute menu and get selected action
        action = menu.exec_(event.globalPos())
        
        # Handle selected action
        if action == copy_action:
            self.copy_selection()
        elif action == paste_action:
            self.paste_clipboard()
        elif action == select_all_action:
            self.select_all()
        elif action == clear_action:
            self.clear()
