#!/usr/bin/env python3
"""
WRAPD: Comprehensive terminal widget with block-based interface, AI integration,
and advanced terminal features inspired by Warp
"""

import os
import sys
import re
import asyncio
import threading
import platform
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum

# PyQt5 imports
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QLabel, 
    QScrollArea, QFrame, QSizePolicy, QMenu, QAction, QToolTip,
    QCompleter, QSplitter, QTextBrowser, QProgressBar, QPushButton,
    QApplication, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import (
    QFont, QColor, QTextCursor, QTextCharFormat, QTextDocument,
    QSyntaxHighlighter, QPalette, QKeySequence, QPixmap, QPainter,
    QLinearGradient, QBrush, QPen
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QEvent, QObject, QRect, QSize,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QSequentialAnimationGroup, QAbstractAnimation, QStringListModel
)

from ..utils.error_handling import TerminalError, WRAPDError
from ..core.config_manager import TerminalConfig, UIConfig


class BlockStatus(Enum):
    """Status of a command block"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class CommandBlock:
    """Represents a command block in the terminal"""
    id: str
    command: str
    timestamp: datetime
    status: BlockStatus
    output: str = ""
    error: str = ""
    execution_time: float = 0.0
    exit_code: Optional[int] = None
    working_directory: str = ""
    ai_suggestion: Optional[str] = None
    
    def __post_init__(self):
        if not self.working_directory:
            self.working_directory = os.getcwd()


class SyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for terminal output"""
    
    def __init__(self, parent: QTextDocument, theme_colors: Dict[str, str]):
        super().__init__(parent)
        self.theme_colors = theme_colors
        self._setup_formats()
    
    def _setup_formats(self):
        """Setup text formats for different syntax elements"""
        self.formats = {}
        
        # Command format
        self.formats['command'] = QTextCharFormat()
        self.formats['command'].setForeground(QColor(self.theme_colors.get('command', '#ffffff')))
        self.formats['command'].setFontWeight(QFont.Bold)
        
        # Output format
        self.formats['output'] = QTextCharFormat()
        self.formats['output'].setForeground(QColor(self.theme_colors.get('output', '#d0d0d0')))
        
        # Error format
        self.formats['error'] = QTextCharFormat()
        self.formats['error'].setForeground(QColor(self.theme_colors.get('error', '#ff6b6b')))
        
        # Success format
        self.formats['success'] = QTextCharFormat()
        self.formats['success'].setForeground(QColor(self.theme_colors.get('success', '#51cf66')))
        
        # Warning format
        self.formats['warning'] = QTextCharFormat()
        self.formats['warning'].setForeground(QColor(self.theme_colors.get('warning', '#ffd43b')))
        
        # Prompt format
        self.formats['prompt'] = QTextCharFormat()
        self.formats['prompt'].setForeground(QColor(self.theme_colors.get('prompt', '#74c0fc')))
        self.formats['prompt'].setFontWeight(QFont.Bold)
    
    def highlightBlock(self, text: str):
        """Highlight a block of text"""
        # Basic ANSI color code highlighting
        ansi_pattern = re.compile(r'\x1b\[([0-9;]+)m')
        
        for match in ansi_pattern.finditer(text):
            start = match.start()
            length = match.end() - start
            
            # Apply format based on ANSI code
            codes = match.group(1).split(';')
            format_obj = QTextCharFormat()
            
            for code in codes:
                if code == '31':  # Red
                    format_obj.setForeground(QColor('#ff6b6b'))
                elif code == '32':  # Green
                    format_obj.setForeground(QColor('#51cf66'))
                elif code == '33':  # Yellow
                    format_obj.setForeground(QColor('#ffd43b'))
                elif code == '34':  # Blue
                    format_obj.setForeground(QColor('#339af0'))
                elif code == '1':   # Bold
                    format_obj.setFontWeight(QFont.Bold)
            
            self.setFormat(start, length, format_obj)


class CommandInputWidget(QLineEdit):
    """Enhanced command input widget with auto-completion and history"""
    
    commandSubmitted = pyqtSignal(str)
    commandChanged = pyqtSignal(str)
    completionRequested = pyqtSignal(str)
    
    def __init__(self, terminal_config: TerminalConfig, parent=None):
        super().__init__(parent)
        self.terminal_config = terminal_config
        self.command_history: List[str] = []
        self.history_index = -1
        self.current_input = ""
        
        # Setup auto-completion
        self.completer = QCompleter()
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompleter(self.completer)
        
        # Connect signals
        self.returnPressed.connect(self._submit_command)
        self.textChanged.connect(self.commandChanged.emit)
        
        # Style the input
        self._apply_styling()
    
    def _apply_styling(self):
        """Apply styling to the input widget"""
        self.setStyleSheet("""
            QLineEdit {
                border: 2px solid #4a4a4a;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: #2a2a2a;
                color: #ffffff;
                font-size: 14px;
                selection-background-color: #4a9eff;
            }
            QLineEdit:focus {
                border-color: #4a9eff;
                background-color: #333333;
            }
        """)
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        key = event.key()
        modifiers = event.modifiers()
        
        if key == Qt.Key_Up and not modifiers:
            self._navigate_history(-1)
            return
        elif key == Qt.Key_Down and not modifiers:
            self._navigate_history(1)
            return
        elif key == Qt.Key_Tab and not modifiers:
            self._request_completion()
            return
        elif key == Qt.Key_Escape and not modifiers:
            self.clear()
            return
        
        super().keyPressEvent(event)
    
    def _submit_command(self):
        """Submit the current command"""
        command = self.text().strip()
        if command:
            self._add_to_history(command)
            self.commandSubmitted.emit(command)
            self.clear()
    
    def _add_to_history(self, command: str):
        """Add command to history"""
        if command and (not self.command_history or self.command_history[-1] != command):
            self.command_history.append(command)
            
            # Limit history size
            if len(self.command_history) > self.terminal_config.history_size:
                self.command_history.pop(0)
        
        self.history_index = len(self.command_history)
    
    def _navigate_history(self, direction: int):
        """Navigate through command history"""
        if not self.command_history:
            return
        
        if self.history_index == len(self.command_history) and direction < 0:
            self.current_input = self.text()
        
        new_index = max(0, min(len(self.command_history), self.history_index + direction))
        
        if new_index == len(self.command_history):
            self.setText(self.current_input)
        elif 0 <= new_index < len(self.command_history):
            self.setText(self.command_history[new_index])
        
        self.history_index = new_index
    
    def _request_completion(self):
        """Request command completion"""
        current_text = self.text()
        if current_text:
            self.completionRequested.emit(current_text)
    
    def update_completions(self, completions: List[str]):
        """Update available completions"""
        model = QStringListModel(completions)
        self.completer.setModel(model)
        
        if completions:
            self.completer.complete()


class CommandBlockWidget(QFrame):
    """Widget representing a single command block"""
    
    blockClicked = pyqtSignal(str)  # block_id
    blockDeleted = pyqtSignal(str)  # block_id
    
    def __init__(self, block: CommandBlock, ui_config: UIConfig, parent=None):
        super().__init__(parent)
        self.block = block
        self.ui_config = ui_config
        self.is_expanded = True
        
        self._setup_ui()
        self._apply_styling()
        self._update_content()
    
    def _setup_ui(self):
        """Setup the UI for the command block"""
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(1)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        self.setLayout(layout)
        
        # Header layout
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Status indicator
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(12, 12)
        header_layout.addWidget(self.status_indicator)
        
        # Command label
        self.command_label = QLabel(self.block.command)
        self.command_label.setFont(QFont("monospace", 11, QFont.Bold))
        header_layout.addWidget(self.command_label, 1)
        
        # Timestamp label
        self.timestamp_label = QLabel()
        self.timestamp_label.setStyleSheet("color: #888888; font-size: 10px;")
        header_layout.addWidget(self.timestamp_label)
        
        # Execution time label
        self.exec_time_label = QLabel()
        self.exec_time_label.setStyleSheet("color: #888888; font-size: 10px;")
        header_layout.addWidget(self.exec_time_label)
        
        layout.addLayout(header_layout)
        
        # Output area
        self.output_area = QTextBrowser()
        self.output_area.setMaximumHeight(200)
        self.output_area.setFont(QFont("monospace", 10))
        self.output_area.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(self.output_area)
        
        # Progress bar (for running commands)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444444;
                border-radius: 3px;
                text-align: center;
                background-color: #2a2a2a;
            }
            QProgressBar::chunk {
                background-color: #4a9eff;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # AI suggestion area (if available)
        if self.block.ai_suggestion:
            self.ai_suggestion_area = QTextBrowser()
            self.ai_suggestion_area.setMaximumHeight(100)
            self.ai_suggestion_area.setStyleSheet("""
                QTextBrowser {
                    border: 1px solid #4a9eff;
                    border-radius: 4px;
                    background-color: #1a2332;
                    color: #ffffff;
                    padding: 8px;
                }
            """)
            self.ai_suggestion_area.setHtml(f"<b>AI Suggestion:</b><br>{self.block.ai_suggestion}")
            layout.addWidget(self.ai_suggestion_area)
    
    def _apply_styling(self):
        """Apply styling based on block status"""
        status_colors = {
            BlockStatus.PENDING: "#888888",
            BlockStatus.RUNNING: "#4a9eff",
            BlockStatus.SUCCESS: "#51cf66",
            BlockStatus.ERROR: "#ff6b6b",
            BlockStatus.CANCELLED: "#ffd43b"
        }
        
        color = status_colors.get(self.block.status, "#888888")
        
        # Update status indicator
        self.status_indicator.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border-radius: 6px;
            }}
        """)
        
        # Update block border
        self.setStyleSheet(f"""
            QFrame {{
                border: 2px solid {color};
                border-radius: 8px;
                background-color: #2a2a2a;
                margin: 4px 0px;
            }}
        """)
        
        # Show/hide progress bar
        if self.block.status == BlockStatus.RUNNING:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
        else:
            self.progress_bar.setVisible(False)
    
    def _update_content(self):
        """Update the content of the block"""
        # Update timestamp
        time_str = self.block.timestamp.strftime("%H:%M:%S")
        self.timestamp_label.setText(time_str)
        
        # Update execution time
        if self.block.execution_time > 0:
            exec_time = f"{self.block.execution_time:.2f}s"
            self.exec_time_label.setText(exec_time)
        
        # Update output
        output_text = ""
        if self.block.output:
            output_text = self.block.output
        if self.block.error:
            output_text += f"\n<span style='color: #ff6b6b;'>{self.block.error}</span>"
        
        self.output_area.setHtml(output_text)
        
        # Update styling
        self._apply_styling()
    
    def update_block(self, block: CommandBlock):
        """Update the block data and refresh display"""
        self.block = block
        self._update_content()
    
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if event.button() == Qt.LeftButton:
            self.blockClicked.emit(self.block.id)
        super().mousePressEvent(event)


class TerminalWidget(QWidget):
    """
    Comprehensive terminal widget with block-based interface, AI integration,
    and advanced terminal features inspired by Warp
    """
    
    # Signals
    commandExecuted = pyqtSignal(str, str)  # command, block_id
    statusChanged = pyqtSignal(str)
    blockCreated = pyqtSignal(str)  # block_id
    blockCompleted = pyqtSignal(str, bool)  # block_id, success
    
    def __init__(self, config_manager, llm_interface, command_processor, logger, parent=None):
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.llm_interface = llm_interface
        self.command_processor = command_processor
        self.logger = logger
        
        # Configuration shortcuts
        self.terminal_config = config_manager.terminal_config
        self.ui_config = config_manager.ui_config
        
        # Terminal state
        self.command_blocks: Dict[str, CommandBlock] = {}
        self.block_widgets: Dict[str, CommandBlockWidget] = {}
        self.current_working_directory = os.getcwd()
        self.is_running_command = False
        self.command_counter = 0
        
        # Theme colors
        self.theme_colors = {
            'command': '#ffffff',
            'output': '#d0d0d0',
            'error': '#ff6b6b',
            'success': '#51cf66',
            'warning': '#ffd43b',
            'prompt': '#74c0fc',
            'background': '#1a1a1a',
            'surface': '#2a2a2a'
        }
        
        # Setup UI
        self._setup_ui()
        self._apply_theme()
        self._setup_connections()
        
        # Initialize with welcome message
        self._add_welcome_block()
        
        self.logger.info("TerminalWidget initialized successfully")
    
    def _setup_ui(self):
        """Setup the user interface"""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # Create splitter for terminal content and input
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)
        
        # Terminal content area
        self._setup_terminal_area(splitter)
        
        # Command input area
        self._setup_input_area(splitter)
        
        # Set splitter proportions
        splitter.setSizes([800, 100])
        splitter.setChildrenCollapsible(False)
    
    def _setup_terminal_area(self, parent):
        """Setup the terminal content area"""
        # Scroll area for command blocks
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Container widget for blocks
        self.blocks_container = QWidget()
        self.blocks_layout = QVBoxLayout()
        self.blocks_layout.setContentsMargins(12, 12, 12, 12)
        self.blocks_layout.setSpacing(8)
        self.blocks_layout.addStretch()  # Push blocks to top
        self.blocks_container.setLayout(self.blocks_layout)
        
        self.scroll_area.setWidget(self.blocks_container)
        parent.addWidget(self.scroll_area)
    
    def _setup_input_area(self, parent):
        """Setup the command input area"""
        input_container = QFrame()
        input_container.setFrameStyle(QFrame.StyledPanel)
        input_container.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-top: 2px solid #4a4a4a;
            }
        """)
        
        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_container.setLayout(input_layout)
        
        # Working directory label
        self.cwd_label = QLabel()
        self.cwd_label.setStyleSheet("color: #74c0fc; font-weight: bold;")
        self._update_cwd_label()
        input_layout.addWidget(self.cwd_label)
        
        # Command input with prompt
        input_row_layout = QHBoxLayout()
        input_row_layout.setSpacing(8)
        
        # Prompt symbol
        prompt_label = QLabel("❯")
        prompt_label.setStyleSheet("color: #4a9eff; font-size: 16px; font-weight: bold;")
        input_row_layout.addWidget(prompt_label)
        
        # Command input
        self.command_input = CommandInputWidget(self.terminal_config)
        input_row_layout.addWidget(self.command_input, 1)
        
        # AI assist button
        self.ai_button = QPushButton("✨ AI")
        self.ai_button.setToolTip("Get AI assistance")
        self.ai_button.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #339af0;
            }
            QPushButton:pressed {
                background-color: #228be6;
            }
        """)
        input_row_layout.addWidget(self.ai_button)
        
        input_layout.addLayout(input_row_layout)
        parent.addWidget(input_container)
    
    def _setup_connections(self):
        """Setup signal connections"""
        self.command_input.commandSubmitted.connect(self._execute_command)
        self.command_input.commandChanged.connect(self._on_command_changed)
        self.command_input.completionRequested.connect(self._provide_completions)
        self.ai_button.clicked.connect(self._request_ai_assistance)
    
    def _apply_theme(self):
        """Apply the current theme to the terminal"""
        bg_color = self.theme_colors['background']
        surface_color = self.theme_colors['surface']
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                color: #ffffff;
            }}
            QScrollArea {{
                border: none;
                background-color: {bg_color};
            }}
        """)
        
        # Update blocks container background
        self.blocks_container.setStyleSheet(f"background-color: {bg_color};")
    
    def _update_cwd_label(self):
        """Update the current working directory label"""
        try:
            # Get relative path from home directory
            home = Path.home()
            current = Path(self.current_working_directory)
            
            if current == home:
                display_path = "~"
            elif home in current.parents:
                display_path = f"~/{current.relative_to(home)}"
            else:
                display_path = str(current)
            
            # Add username and hostname
            username = os.getenv('USER', 'user')
            hostname = platform.node().split('.')[0]
            
            self.cwd_label.setText(f"{username}@{hostname} {display_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to update working directory label: {e}")
            self.cwd_label.setText(f"Terminal [{self.current_working_directory}]")
    
    def _add_welcome_block(self):
        """Add a welcome message block"""
        welcome_text = f"""
        <div style='text-align: center; color: #74c0fc;'>
            <h2>🚀 Welcome to WRAPD Terminal</h2>
            <p>AI-powered terminal enhancement • Version 2.0</p>
            <p style='color: #888888; font-size: 12px;'>
                Type your commands below or click the AI button for assistance
            </p>
        </div>
        """
        
        welcome_block = CommandBlock(
            id="welcome",
            command="# Welcome to WRAPD",
            timestamp=datetime.now(),
            status=BlockStatus.SUCCESS,
            output=welcome_text
        )
        
        self._add_block(welcome_block)
    
    def _generate_block_id(self) -> str:
        """Generate a unique block ID"""
        self.command_counter += 1
        return f"block_{int(time.time())}_{self.command_counter}"
    
    def _add_block(self, block: CommandBlock):
        """Add a command block to the terminal"""
        # Store block data
        self.command_blocks[block.id] = block
        
        # Create block widget
        block_widget = CommandBlockWidget(block, self.ui_config)
        block_widget.blockClicked.connect(self._on_block_clicked)
        block_widget.blockDeleted.connect(self._on_block_deleted)
        
        # Add to layout (before the stretch)
        self.blocks_layout.insertWidget(self.blocks_layout.count() - 1, block_widget)
        self.block_widgets[block.id] = block_widget
        
        # Scroll to bottom
        QTimer.singleShot(100, self._scroll_to_bottom)
        
        # Emit signal
        self.blockCreated.emit(block.id)
    
    def _update_block(self, block_id: str, **updates):
        """Update a command block"""
        if block_id not in self.command_blocks:
            return
        
        block = self.command_blocks[block_id]
        
        # Update block data
        for key, value in updates.items():
            if hasattr(block, key):
                setattr(block, key, value)
        
        # Update widget
        if block_id in self.block_widgets:
            self.block_widgets[block_id].update_block(block)
    
    def _scroll_to_bottom(self):
        """Scroll to the bottom of the terminal"""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _execute_command(self, command: str):
        """Execute a command"""
        if not command.strip():
            return
        
        if self.is_running_command:
            self.statusChanged.emit("Another command is already running...")
            return
        
        # Create new command block
        block_id = self._generate_block_id()
        block = CommandBlock(
            id=block_id,
            command=command,
            timestamp=datetime.now(),
            status=BlockStatus.PENDING,
            working_directory=self.current_working_directory
        )
        
        self._add_block(block)
        
        # Execute command asynchronously
        self._execute_command_async(block_id, command)
        
        # Emit signal
        self.commandExecuted.emit(command, block_id)
    
    def _execute_command_async(self, block_id: str, command: str):
        """Execute command asynchronously"""
        def run_command():
            try:
                self.is_running_command = True
                self._update_block(block_id, status=BlockStatus.RUNNING)
                
                start_time = time.time()
                
                # Handle built-in commands
                if command.strip() in ['clear', 'cls']:
                    self._clear_terminal()
                    execution_time = time.time() - start_time
                    self._update_block(
                        block_id, 
                        status=BlockStatus.SUCCESS,
                        output="Terminal cleared",
                        execution_time=execution_time
                    )
                    return
                
                elif command.strip().startswith('cd '):
                    self._handle_cd_command(block_id, command, start_time)
                    return
                
                elif command.strip() in ['exit', 'quit']:
                    self._handle_exit_command(block_id, command, start_time)
                    return
                
                # Execute command via command processor
                success, output, error = self.command_processor.execute_command_sync(
                    command,
                    cwd=self.current_working_directory
                )
                
                execution_time = time.time() - start_time
                
                # Update block with results
                status = BlockStatus.SUCCESS if success else BlockStatus.ERROR
                self._update_block(
                    block_id,
                    status=status,
                    output=output or "",
                    error=error or "",
                    execution_time=execution_time,
                    exit_code=0 if success else 1
                )
                
                # Emit completion signal
                self.blockCompleted.emit(block_id, success)
                
            except Exception as e:
                self.logger.error(f"Command execution failed: {e}", exc_info=True)
                execution_time = time.time() - start_time
                self._update_block(
                    block_id,
                    status=BlockStatus.ERROR,
                    error=f"Execution failed: {str(e)}",
                    execution_time=execution_time
                )
                self.blockCompleted.emit(block_id, False)
            
            finally:
                self.is_running_command = False
        
        # Run in thread to avoid blocking UI
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    def _handle_cd_command(self, block_id: str, command: str, start_time: float):
        """Handle cd command"""
        try:
            # Extract path from command
            parts = command.strip().split(' ', 1)
            if len(parts) < 2:
                target_dir = os.path.expanduser('~')
            else:
                target_dir = os.path.expanduser(parts[1])
            
            # Resolve relative path
            if not os.path.isabs(target_dir):
                target_dir = os.path.join(self.current_working_directory, target_dir)
            
            target_dir = os.path.abspath(target_dir)
            
            # Check if directory exists
            if not os.path.exists(target_dir):
                raise FileNotFoundError(f"Directory not found: {target_dir}")
            
            if not os.path.isdir(target_dir):
                raise NotADirectoryError(f"Not a directory: {target_dir}")
            
            # Change directory
            self.current_working_directory = target_dir
            os.chdir(target_dir)
            
            execution_time = time.time() - start_time
            self._update_block(
                block_id,
                status=BlockStatus.SUCCESS,
                output=f"Changed directory to: {target_dir}",
                execution_time=execution_time
            )
            
            # Update working directory label
            self._update_cwd_label()
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_block(
                block_id,
                status=BlockStatus.ERROR,
                error=str(e),
                execution_time=execution_time
            )
    
    def _handle_exit_command(self, block_id: str, command: str, start_time: float):
        """Handle exit command"""
        execution_time = time.time() - start_time
        self._update_block(
            block_id,
            status=BlockStatus.SUCCESS,
            output="Goodbye! 👋",
            execution_time=execution_time
        )
        
        # Close application after a short delay
        QTimer.singleShot(1000, self._close_application)
    
    def _close_application(self):
        """Close the application"""
        app = QApplication.instance()
        if app:
            app.quit()
    
    def _clear_terminal(self):
        """Clear all command blocks"""
        # Remove all block widgets
        for block_id, widget in self.block_widgets.items():
            widget.setParent(None)
            widget.deleteLater()
        
        # Clear data
        self.command_blocks.clear()
        self.block_widgets.clear()
        
        # Reset counter
        self.command_counter = 0
        
        # Add welcome message back
        self._add_welcome_block()
    
    def _on_command_changed(self, text: str):
        """Handle command input changes"""
        # This could be used for real-time suggestions
        pass
    
    def _provide_completions(self, text: str):
        """Provide command completions"""
        try:
            completions = self.command_processor.get_completions(text)
            self.command_input.update_completions(completions)
        except Exception as e:
            self.logger.warning(f"Failed to provide completions: {e}")
            self.command_input.update_completions([])
    
    def _request_ai_assistance(self):
        """Request AI assistance for command input"""
        current_command = self.command_input.text().strip()
        
        if not current_command:
            # Show general help
            self.statusChanged.emit("💡 Type a command and I'll help you with it!")
            return
        
        # Get AI suggestion
        try:
            suggestion = self.llm_interface.get_command_suggestion(
                current_command, 
                self.current_working_directory
            )
            
            if suggestion:
                self.statusChanged.emit(f"AI Suggestion: {suggestion}")
            else:
                self.statusChanged.emit("No AI suggestion available for this command")
                
        except Exception as e:
            self.logger.warning(f"Failed to get AI assistance: {e}")
            self.statusChanged.emit("AI assistance temporarily unavailable")
    
    def _on_block_clicked(self, block_id: str):
        """Handle block click events"""
        # Could be used to show block details or copy command
        if block_id in self.command_blocks:
            block = self.command_blocks[block_id]
            self.statusChanged.emit(f"Block: {block.command}")
    
    def _on_block_deleted(self, block_id: str):
        """Handle block deletion"""
        if block_id in self.block_widgets:
            widget = self.block_widgets[block_id]
            widget.setParent(None)
            widget.deleteLater()
            del self.block_widgets[block_id]
        
        if block_id in self.command_blocks:
            del self.command_blocks[block_id]
    
    # Public API methods
    
    def execute_command(self, command: str):
        """Execute a command programmatically"""
        self.command_input.setText(command)
        self._execute_command(command)
    
    def get_command_history(self) -> List[str]:
        """Get command history"""
        return self.command_input.command_history.copy()
    
    def clear_terminal(self):
        """Clear the terminal"""
        self._clear_terminal()
    
    def focus_input(self):
        """Focus on command input"""
        self.command_input.setFocus()
    
    def get_current_directory(self) -> str:
        """Get current working directory"""
        return self.current_working_directory
    
    def set_current_directory(self, directory: str):
        """Set current working directory"""
        try:
            directory = os.path.abspath(os.path.expanduser(directory))
            if os.path.isdir(directory):
                self.current_working_directory = directory
                os.chdir(directory)
                self._update_cwd_label()
            else:
                raise NotADirectoryError(f"Not a directory: {directory}")
        except Exception as e:
            self.logger.error(f"Failed to set directory: {e}")
            raise TerminalError(f"Failed to change directory: {e}")