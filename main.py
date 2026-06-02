import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, simpledialog
import ollama
import threading
import subprocess
import json
import os
import sys
import shutil
from datetime import datetime

class OllamaAssistantGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OpenCMD-AI GUI Terminal")
        self.root.state('zoomed')  # Fullscreen mode on Windows
        
        self.conversation_history = []
        self.is_processing = False
        self.thinking_status_label = None
        self.thinking_after_id = None
        self.thinking_tick = 0
        self.typing_queue = []
        self.typing_in_progress = False
        self.selected_model = tk.StringVar(value='qwen2:0.5b')
        app_data_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "OllamaTerminal")
        os.makedirs(app_data_dir, exist_ok=True)
        self.memory_file = os.path.join(app_data_dir, "conversation_memory.json")
        self.log_file = os.path.join(app_data_dir, "app.log")
        self.ollama_binary = None
        self.ollama_error = None
        self.setup_logging()
        
        # Password protection
        if not self.check_password():
            self.root.destroy()
            return
        
        # Create GUI elements
        self.setup_ui()
        
        # Ensure Ollama is visible to this app, especially when running as an exe
        self.configure_ollama_path()
        
        # Check selected model availability and prompt download if needed
        self.check_and_handle_model_availability()
        
        # Load saved conversation if exists (after UI is ready)
        self.load_memory()
    def setup_ui(self):
        """Setup the user interface"""
        # Set dark background for root
        self.root.config(bg="#0a0e27")
        
        # Create main container frame
        main_frame = tk.Frame(self.root, bg="#0a0e27")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create title label
        title_label = tk.Label(
            main_frame,
            text="◆ OpenCMD-AI TERMINAL ◆",
            font=("Courier New", 14, "bold"),
            bg="#0a0e27",
            fg="#00ff41",
            pady=10
        )
        title_label.pack(fill=tk.X)
        
        # Create content frame
        content_frame = tk.Frame(main_frame, bg="#0a0e27")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Chat display area
        self.chat_display = scrolledtext.ScrolledText(
            content_frame,
            wrap=tk.WORD,
            font=("Courier New", 10),
            bg="#0a0e27",
            fg="#00ff41",
            insertbackground="#00ff41",
            state=tk.DISABLED
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Configure tags for different message types
        self.chat_display.tag_config("user", foreground="#0099ff", font=("Courier New", 10, "bold"))
        self.chat_display.tag_config("assistant", foreground="#00ff41", font=("Courier New", 10, "bold"))
        self.chat_display.tag_config("error", foreground="#ff0055", font=("Courier New", 10, "bold"))
        
        # Model selection frame
        model_frame = tk.Frame(main_frame, bg="#0d1233")
        model_frame.pack(fill=tk.X, padx=10, pady=5)
        
        model_label = tk.Label(model_frame, text="[MODEL]", bg="#0a0e27", fg="#00ff41", font=("Courier New", 10, "bold"))
        model_label.pack(side=tk.LEFT, padx=5)
        
        model_combo = ttk.Combobox(
            model_frame,
            textvariable=self.selected_model,
            values=[
                'qwen2:0.5b',
                'qwen2:1.5b',
                'qwen2.5-coder:0.5b',
                'qwen2.5-coder:1.5b',
                'deepseek-coder:1.3b',
                'qwen3.5:0.8b',
                'qwen3.5:2b',
                'gemma:2b',
                'gemma:2b-instruct',
                'gemma:2b-instruct-fp16',
                'gemma:2b-text',
                'gemma:2b-text-fp16',
                'phi3:mini',
                'phi3:mini-4k',
                'phi3:mini-128k',
                'phi3:latest',
                'qwen3-coder-next:latest',
                'lfm2.5-thinking'
            ],
            font=("Courier New", 10),
            state='readonly',
            width=20
        )
        model_combo.bind("<<ComboboxSelected>>", lambda e: self.on_model_changed())
        model_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Style the combobox
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            'TCombobox',
            fieldbackground='#1a1f3a',
            background='#1a1f3a',
            foreground='#00ff41',
            insertbackground='#00ff41'
        )
        
        # Input frame
        input_frame = tk.Frame(main_frame, bg="#0a0e27")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Input field label
        input_label = tk.Label(input_frame, text="[INPUT]", bg="#0a0e27", fg="#00ff41", font=("Courier New", 10, "bold"))
        input_label.pack(side=tk.LEFT, padx=5)
        
        self.input_field = tk.Entry(
            input_frame,
            font=("Courier New", 10),
            bg="#1a1f3a",
            fg="#00ff41",
            insertbackground="#00ff41",
            relief=tk.FLAT,
            bd=2
        )
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.input_field.bind("<Return>", lambda e: self.send_message())
        
        # Send button
        self.send_button = tk.Button(
            input_frame,
            text="[SEND]",
            command=self.send_message,
            bg="#1a1f3a",
            fg="#00ff41",
            font=("Courier New", 10, "bold"),
            padx=20,
            relief=tk.FLAT,
            activebackground="#00ff41",
            activeforeground="#0a0e27"
        )
        self.send_button.pack(side=tk.LEFT, padx=5)
        
        # Clear button
        clear_button = tk.Button(
            input_frame,
            text="[CLEAR]",
            command=self.clear_chat,
            bg="#1a1f3a",
            fg="#ff0055",
            font=("Courier New", 10, "bold"),
            padx=15,
            relief=tk.FLAT,
            activebackground="#ff0055",
            activeforeground="#0a0e27"
        )
        clear_button.pack(side=tk.LEFT, padx=5)
        
        # Load Memory button
        load_button = tk.Button(
            input_frame,
            text="[LOAD]",
            command=self.load_memory,
            bg="#1a1f3a",
            fg="#ffaa00",
            font=("Courier New", 10, "bold"),
            padx=15,
            relief=tk.FLAT,
            activebackground="#ffaa00",
            activeforeground="#0a0e27"
        )
        load_button.pack(side=tk.LEFT, padx=5)
        
        # Save button
        save_button = tk.Button(
            input_frame,
            text="[SAVE]",
            command=self.save_memory,
            bg="#1a1f3a",
            fg="#00ffaa",
            font=("Courier New", 10, "bold"),
            padx=15,
            relief=tk.FLAT,
            activebackground="#00ffaa",
            activeforeground="#0a0e27"
        )
        save_button.pack(side=tk.LEFT, padx=5)
        self.thinking_status_label = tk.Label(
            input_frame,
            text="",
            font=("Courier New", 10, "italic"),
            bg="#0a0e27",
            fg="#00ff41"
        )
        self.thinking_status_label.pack(side=tk.LEFT, padx=5)
        
        # Initial message
        self.display_message("SYSTEM", ">> OpenCMD-AI v1.2", "assistant")
        self.display_message("SYSTEM", ">> Ready to process your queries...", "assistant")
    
    def configure_ollama_path(self):
        """Find the Ollama executable and expose it to the packaged application."""
        self.ollama_binary = shutil.which("ollama")
        if not self.ollama_binary:
            possible_paths = []
            if sys.platform == "win32":
                local_appdata = os.environ.get("LOCALAPPDATA", "")
                program_files = os.environ.get("ProgramFiles", "")
                program_files_x86 = os.environ.get("ProgramFiles(x86)", "")
                user_profile = os.environ.get("USERPROFILE", "")
                possible_paths.extend([
                    os.path.join(local_appdata, "Programs", "Ollama", "ollama.exe"),
                    os.path.join(program_files, "Ollama", "ollama.exe"),
                    os.path.join(program_files_x86, "Ollama", "ollama.exe"),
                    os.path.join(user_profile, ".ollama", "bin", "ollama.exe"),
                ])
            else:
                possible_paths.extend([
                    "/usr/local/bin/ollama",
                    "/usr/bin/ollama",
                    "/opt/homebrew/bin/ollama",
                    os.path.expanduser("~/.ollama/bin/ollama"),
                ])
            for path in possible_paths:
                if path and os.path.exists(path):
                    self.ollama_binary = path
                    break
        if self.ollama_binary:
            bin_dir = os.path.dirname(self.ollama_binary)
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
            os.environ["OLLAMA_PATH"] = self.ollama_binary
            self.log_event(f"Using Ollama binary at {self.ollama_binary}")
        else:
            self.ollama_error = (
                "Ollama executable not found. Install Ollama or place it on PATH, "
                "then restart the app."
            )
            self.log_event("Ollama executable not found", level="ERROR")
            self.display_message("ERROR", self.ollama_error, "error")

    def on_model_changed(self):
        """Handle model change from combobox selection"""
        is_available, available_models = self.check_model_availability()
        
        if not is_available:
            selected_model = self.selected_model.get()
            self.display_message("SYSTEM", f">> Model '{selected_model}' not found locally", "assistant")
            self.prompt_download_model()

    def check_and_handle_model_availability(self):
        """Check model availability and prompt download if needed"""
        is_available, available_models = self.check_model_availability()
        
        if not is_available:
            self.root.after(500, self.prompt_download_model)

    def check_model_availability(self):
        """Check if the selected model is installed. Returns (is_available, available_models)"""
        try:
            if not self.ollama_binary:
                self.log_event("Cannot check model availability: Ollama binary not found", level="WARNING")
                return False, []
            
            result = subprocess.run(
                [self.ollama_binary, "list"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                self.log_event(f"Failed to list models: {result.stderr}", level="ERROR")
                return False, []
            
            available_models = []
            for line in result.stdout.strip().split('\n')[1:]:
                if line.strip():
                    parts = line.split()
                    if parts:
                        available_models.append(parts[0])
            
            selected_model = self.selected_model.get()
            is_available = selected_model in available_models
            
            self.log_event(f"Model check: {selected_model} - {'Available' if is_available else 'Not found'}. Available: {', '.join(available_models)}")
            return is_available, available_models
            
        except Exception as e:
            self.log_event(f"Error checking model availability: {e}", level="ERROR")
            return False, []

    def download_model(self):
        """Download the selected model in background thread with progress display"""
        try:
            selected_model = self.selected_model.get()
            self.display_message("SYSTEM", f">> Starting download of model: {selected_model}", "assistant")
            self.log_event(f"Starting model download: {selected_model}")
            
            if not self.ollama_binary:
                raise RuntimeError("Ollama binary not found")
            
            process = subprocess.Popen(
                [self.ollama_binary, "pull", selected_model],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )
            
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if line:
                    self.root.after(0, lambda msg=line: self.display_message("DOWNLOAD", msg, "assistant"))
                    self.log_event(f"Download progress: {line}")
            
            process.wait()
            
            if process.returncode == 0:
                self.display_message("SYSTEM", f">> Successfully downloaded {selected_model}", "assistant")
                self.log_event(f"Model download successful: {selected_model}")
            else:
                error_msg = f"Model download failed with return code {process.returncode}"
                self.display_message("ERROR", error_msg, "error")
                self.log_event(error_msg, level="ERROR")
                
        except Exception as e:
            error_msg = f"Error downloading model: {str(e)}"
            self.display_message("ERROR", error_msg, "error")
            self.log_event(error_msg, level="ERROR")

    def prompt_download_model(self):
        """Prompt user to download missing model with yes/no dialog"""
        selected_model = self.selected_model.get()
        message = f"Model '{selected_model}' is not installed.\n\nWould you like to download it now?\n\n(This may take several minutes depending on model size)"
        
        if messagebox.askyesno("Model Not Found", message):
            self.display_message("SYSTEM", ">> User confirmed download", "assistant")
            thread = threading.Thread(target=self.download_model)
            thread.daemon = True
            thread.start()
        else:
            self.display_message("SYSTEM", ">> Download cancelled. App may fail on first query if model not available.", "assistant")
            self.log_event("User declined model download")

    def setup_logging(self):
        """Create the application log file and record startup information."""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()} - INFO - Application started\n")
        except Exception:
            pass

    def log_event(self, message, level="INFO"):
        """Write diagnostic events to the local application log."""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()} - {level} - {message}\n")
        except Exception:
            pass

    def backup_memory_file(self):
        """Create a backup of the conversation memory before overwriting it."""
        try:
            if os.path.exists(self.memory_file):
                backup_file = self.memory_file + ".bak"
                shutil.copy2(self.memory_file, backup_file)
                self.log_event(f"Backup created at {backup_file}")
        except Exception as e:
            self.log_event(f"Backup failed: {e}", level="WARNING")

    def check_password(self):
        """Prompt for password authentication with hacker style UI"""
        # Create password window
        pwd_window = tk.Toplevel(self.root)
        pwd_window.title("ACCESS DENIED")
        pwd_window.geometry("600x400")
        pwd_window.config(bg="#0a0e27")
        pwd_window.resizable(False, False)
        pwd_window.attributes('-topmost', True)
        
        # Center window on screen
        pwd_window.update_idletasks()
        x = (pwd_window.winfo_screenwidth() // 2) - 300
        y = (pwd_window.winfo_screenheight() // 2) - 200
        pwd_window.geometry(f"+{x}+{y}")
        
        # ASCII art header
        header = tk.Label(
            pwd_window,
            text="╔═══════════════════════════════════════╗\n║     ◆ SYSTEM ACCESS REQUIRED ◆     ║\n╚═══════════════════════════════════════╝",
            font=("Courier New", 11, "bold"),
            bg="#0a0e27",
            fg="#00ff41",
            pady=20
        )
        header.pack()
        
        # Status message
        status = tk.Label(
            pwd_window,
            text=">> SCANNING BIOMETRICS...\n>> ACCESS LEVEL: ADMIN",
            font=("Courier New", 9),
            bg="#0a0e27",
            fg="#00ff41",
            pady=15,
            justify=tk.LEFT
        )
        status.pack()
        
        # Password label
        pwd_label = tk.Label(
            pwd_window,
            text="[PASSWORD]",
            font=("Courier New", 10, "bold"),
            bg="#0a0e27",
            fg="#00ff41"
        )
        pwd_label.pack(pady=10)
        
        # Password entry
        pwd_entry = tk.Entry(
            pwd_window,
            font=("Courier New", 12),
            bg="#1a1f3a",
            fg="#00ff41",
            insertbackground="#00ff41",
            relief=tk.FLAT,
            bd=2,
            show="●"
        )
        pwd_entry.pack(pady=5, padx=50, fill=tk.X)
        pwd_entry.focus()
        
        # Result storage
        result = {"valid": False}
        
        def verify_password():
            if pwd_entry.get() == "Valley Forge":
                result["valid"] = True
                pwd_window.destroy()
            else:
                pwd_entry.delete(0, tk.END)
                status.config(text=">> BIOMETRIC SCAN FAILED\n>> ACCESS DENIED")
                pwd_window.after(1000, lambda: pwd_window.destroy())
        
        def on_key(event):
            if event.keysym == "Return":
                verify_password()
        
        # Buttons
        button_frame = tk.Frame(pwd_window, bg="#0a0e27")
        button_frame.pack(pady=20)
        
        enter_button = tk.Button(
            button_frame,
            text="[AUTHENTICATE]",
            command=verify_password,
            bg="#1a1f3a",
            fg="#00ff41",
            font=("Courier New", 10, "bold"),
            padx=15,
            relief=tk.FLAT,
            activebackground="#00ff41",
            activeforeground="#0a0e27"
        )
        enter_button.pack(side=tk.LEFT, padx=10)
        
        exit_button = tk.Button(
            button_frame,
            text="[EXIT]",
            command=pwd_window.destroy,
            bg="#1a1f3a",
            fg="#ff0055",
            font=("Courier New", 10, "bold"),
            padx=25,
            relief=tk.FLAT,
            activebackground="#ff0055",
            activeforeground="#0a0e27"
        )
        exit_button.pack(side=tk.LEFT, padx=10)
        
        pwd_entry.bind("<Return>", on_key)
        
        # Wait for window to close
        pwd_window.wait_window()
        
        return result["valid"]
    
    def display_message(self, sender, message, tag="user"):
        """Display a message in the chat display area"""
        # Insert message immediately (no animation or audio)
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{sender}: ", tag)
        self.chat_display.insert(tk.END, f"{message}\n\n")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def insert_assistant_prefix(self):
        """Insert the assistant prefix for streaming output."""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "Assistant: ", "assistant")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def append_message_chunk(self, chunk, tag="assistant"):
        """Append a chunk of assistant output to the chat display."""
        if not chunk:
            return
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, chunk, tag)
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def normalize_stream_chunk(self, event):
        """Extract text from a stream event emitted by Ollama."""
        if event is None:
            return ""
        if isinstance(event, bytes):
            return event.decode('utf-8', errors='replace')
        if isinstance(event, str):
            return event
        if isinstance(event, dict):
            if isinstance(event.get("message"), dict):
                return event["message"].get("content", "") or ""
            if event.get("content") is not None:
                return event.get("content", "") or ""
            if event.get("delta") is not None:
                delta = event.get("delta")
                if isinstance(delta, dict):
                    return delta.get("content", "") or delta.get("text", "") or ""
                return str(delta)
            if event.get("text") is not None:
                return event.get("text", "") or ""
            return ""

        if hasattr(event, "content"):
            return str(getattr(event, "content", "") or "")

        if hasattr(event, "message"):
            msg = getattr(event, "message")
            if isinstance(msg, dict):
                return msg.get("content", "") or ""
            if hasattr(msg, "content"):
                return str(getattr(msg, "content", "") or "")

        if hasattr(event, "delta"):
            delta = getattr(event, "delta")
            if isinstance(delta, dict):
                return delta.get("content", "") or delta.get("text", "") or ""
            return str(delta or "")

        if hasattr(event, "text"):
            return str(getattr(event, "text", "") or "")

        if hasattr(event, "data"):
            return str(getattr(event, "data", "") or "")

        if hasattr(event, "__dict__"):
            return self.normalize_stream_chunk(event.__dict__)

        return ""

    def queue_assistant_text(self, text, tag="assistant"):
        """Queue assistant output for typing animation."""
        if not text and text != "":
            return
        text = str(text)
        if not text:
            return
        self.typing_queue.append((text, tag))
        if not self.typing_in_progress:
            self.typing_in_progress = True
            self._type_next_char()

    def _type_next_char(self, delay=15):
        if not self.typing_queue:
            self.typing_in_progress = False
            return

        current_text, current_tag = self.typing_queue[0]
        if not current_text:
            self.typing_queue.pop(0)
            self.root.after(1, self._type_next_char)
            return

        char = current_text[0]
        remaining = current_text[1:]
        self.typing_queue[0] = (remaining, current_tag)
        self.append_message_chunk(char, current_tag)
        self.root.after(delay, self._type_next_char)

    def type_out_message(self, message, delay=15):
        """Type assistant output one character at a time."""
        self.queue_assistant_text(message, tag="assistant")

    def start_thinking_indicator(self):
        if not getattr(self, 'thinking_status_label', None):
            return
        self.thinking_tick = 0
        try:
            self.thinking_status_label.config(text="Thinking")
        except Exception:
            pass
        self.schedule_thinking_tick()

    def schedule_thinking_tick(self):
        # update the thinking indicator every 2 seconds
        if getattr(self, 'thinking_after_id', None):
            try:
                self.root.after_cancel(self.thinking_after_id)
            except Exception:
                pass

        def _tick():
            try:
                self.thinking_tick = (self.thinking_tick + 1) % 4
                dots = '.' * self.thinking_tick
                self.thinking_status_label.config(text=f"Thinking{dots}")
            except Exception:
                pass
            try:
                self.thinking_after_id = self.root.after(2000, _tick)
            except Exception:
                self.thinking_after_id = None

        # schedule first tick after 2 seconds
        try:
            self.thinking_after_id = self.root.after(2000, _tick)
        except Exception:
            self.thinking_after_id = None

    def stop_thinking_indicator(self):
        try:
            if getattr(self, 'thinking_after_id', None):
                try:
                    self.root.after_cancel(self.thinking_after_id)
                except Exception:
                    pass
                self.thinking_after_id = None
        except Exception:
            pass
        try:
            if getattr(self, 'thinking_status_label', None):
                self.thinking_status_label.config(text="")
        except Exception:
            pass
        self.thinking_tick = 0
    
    def send_message(self):
        """Send user message and get AI response"""
        user_input = self.input_field.get().strip()
        
        if not user_input:
            return
        
        # Display user message
        self.display_message("You", user_input, "user")
        self.input_field.delete(0, tk.END)
        
        # Check if user is asking for help
        normalized = user_input.lower().strip()
        if normalized in ("help", "commands"):
            self.handle_help_command()
            return
        
        # Check if user is trying to open an app
        if normalized.startswith("open "):
            app_name = normalized[5:].strip().lower()
            self.handle_open_app(app_name)
            return
        
        # Check if user is trying to close an app
        if normalized.startswith("close "):
            app_name = normalized[6:].strip().lower()
            self.handle_close_app(app_name)
            return
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Disable send button and get response in background thread
        self.send_button.config(state=tk.DISABLED)
        self.input_field.config(state=tk.DISABLED)
        self.is_processing = True
        self.start_thinking_indicator()
        
        thread = threading.Thread(target=self.get_ai_response)
        thread.daemon = True
        thread.start()
    
    def handle_open_app(self, app_name):
        """Handle opening an app from user command"""
        app_commands = {
            "notepad": ["notepad.exe"],
            "calculator": ["calc.exe"],
            "calc": ["calc.exe"],
            "explorer": ["explorer.exe"],
            "file explorer": ["explorer.exe"],
            "files": ["explorer.exe"],
            "task manager": ["taskmgr.exe"],
            "taskmgr": ["taskmgr.exe"],
            "cmd": ["cmd.exe", "/K"],
            "command prompt": ["cmd.exe", "/K"],
            "powershell": ["powershell.exe", "-NoExit"],
            "code": ["code"],
            "vscode": ["code"],
            "python": [sys.executable, "-m", "idlelib.idle"],
            "idle": [sys.executable, "-m", "idlelib.idle"]
        }
        
        if app_name in app_commands:
            try:
                cmd = app_commands[app_name]
                # Use Shell-backed launch methods so Windows treats this as a normal user action.
                if sys.platform == "win32":
                    # Prefer os.startfile for direct executables when possible (uses ShellExecute).
                    try:
                        exe_path = cmd[0]
                        if os.path.exists(exe_path):
                            os.startfile(exe_path)
                            self.display_message("SYSTEM", f">> Opening: {app_name.upper()}", "assistant")
                            return
                    except Exception:
                        pass

                    # For interactive shells, use cmd /c start to let the shell create a normal console window.
                    if app_name in ("cmd", "command prompt"):
                        subprocess.Popen(["cmd.exe", "/c", "start", "", "cmd.exe", "/K"], shell=False)
                    elif app_name == "powershell":
                        subprocess.Popen(["cmd.exe", "/c", "start", "", "powershell.exe", "-NoExit"], shell=False)
                    else:
                        # Fall back to start via cmd to get ShellExecute behaviour for other apps.
                        subprocess.Popen(["cmd.exe", "/c", "start", "", cmd[0]] + cmd[1:], shell=False)
                else:
                    subprocess.Popen(cmd)

                self.display_message("SYSTEM", f">> Opening: {app_name.upper()}", "assistant")
            except Exception as e:
                self.display_message("ERROR", f"Failed to open {app_name}: {str(e)}", "error")
        else:
            self.display_message("ERROR", f"Unknown app: {app_name}. Try: notepad, calculator, explorer, etc.", "error")
    
    def handle_close_app(self, app_name):
        """Handle closing an app from user command"""
        app_processes = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "files": "explorer.exe",
            "task manager": "taskmgr.exe",
            "taskmgr": "taskmgr.exe",
            "cmd": "cmd.exe",
            "command prompt": "cmd.exe",
            "powershell": "powershell.exe",
            "code": "code.exe",
            "vscode": "code.exe",
            "python": "python.exe",
            "idle": "pythonw.exe",
            "chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "edge": "msedge.exe"
        }
        
        if app_name in app_processes:
            try:
                process_name = app_processes[app_name]
                subprocess.run(["taskkill", "/IM", process_name], check=False)
                self.display_message("SYSTEM", f">> Closed: {app_name.upper()}", "assistant")
            except Exception as e:
                self.display_message("ERROR", f"Failed to close {app_name}: {str(e)}", "error")
        else:
            self.display_message("ERROR", f"Unknown app: {app_name}. Try: notepad, calculator, cmd, powershell, code, etc.", "error")
    
    def handle_help_command(self):
        """Display help for commands, model selection, and downloads."""
        help_text = (
            "Commands:\n"
            "  help | commands - Show this help text\n"
            "  open <app> - Open apps like notepad, calculator, explorer, cmd, powershell, code, python\n"
            "  close <app> - Close apps like notepad, calculator, explorer, cmd, powershell, code\n"
            "\n"
            "Model guide:\n"
            "  Use the model dropdown to choose a model. If the selected model is not installed, the app will prompt you to download it.\n"
            "  Download may take several minutes for larger models.\n"
            "\n"
            "Best models by category:\n"
            "  Lightweight: qwen2:0.5b, phi3:mini\n"
            "  Best balance: qwen3.5:0.8b, deepseek-coder:1.3b\n"
            "  Heaviest: qwen3.5:2b, gemma:2b\n"
            "\n"
            "Tip: Switch models from the dropdown, then ask a question or type a command. If the model is missing, choose Yes to download it."
        )
        self.display_message("SYSTEM", help_text, "assistant")
    
    def get_ai_response(self):
        """Get response from Ollama AI via CLI or Python module"""
        try:
            if self.ollama_error:
                raise RuntimeError(self.ollama_error)
            
            selected_model = self.selected_model.get()
            self.log_event(f"Requesting response from Ollama model {selected_model}")

            assistant_message = ""
            self.root.after(0, self.insert_assistant_prefix)
            streamed = False

            # Try Python module first
            try:
                response_stream = ollama.chat(
                    model=selected_model,
                    messages=self.conversation_history,
                    stream=True
                )

                if hasattr(response_stream, '__iter__') and not isinstance(response_stream, (str, bytes, dict)):
                    for event in response_stream:
                        chunk = self.normalize_stream_chunk(event)
                        if chunk:
                            streamed = True
                            assistant_message += chunk
                            self.root.after(0, self.queue_assistant_text, chunk)

                    if not assistant_message:
                        # Some Ollama stream objects may still expose a final message payload
                        fallback = ""
                        if isinstance(response_stream, dict):
                            fallback = response_stream.get("message", {}).get("content", "")
                        elif hasattr(response_stream, "message"):
                            msg = getattr(response_stream, "message")
                            if isinstance(msg, dict):
                                fallback = msg.get("content", "") or ""
                            elif hasattr(msg, "content"):
                                fallback = str(getattr(msg, "content", "") or "")
                        elif hasattr(response_stream, "content"):
                            fallback = str(getattr(response_stream, "content", "") or "")
                        if fallback:
                            assistant_message = fallback
                            streamed = False
                            self.root.after(0, self.type_out_message, assistant_message + "\n\n")
                else:
                    if isinstance(response_stream, dict):
                        assistant_message = response_stream.get("message", {}).get("content", "")
                    else:
                        assistant_message = str(response_stream)
                    if assistant_message:
                        self.root.after(0, self.type_out_message, assistant_message + "\n\n")
                        streamed = True
            except (ImportError, ModuleNotFoundError, AttributeError):
                # Fallback: use Ollama CLI directly
                if not self.ollama_binary:
                    raise RuntimeError("Ollama CLI not found and Python module unavailable")

                import json as json_module
                messages_json = json_module.dumps(self.conversation_history)
                process = subprocess.Popen(
                    [self.ollama_binary, "run", selected_model],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1
                )
                process.stdin.write(messages_json)
                process.stdin.close()

                while True:
                    char = process.stdout.read(1)
                    if char == "":
                        break
                    streamed = True
                    assistant_message += char
                    self.root.after(0, self.queue_assistant_text, char)

                process.wait()
                if process.returncode != 0:
                    self.log_event(f"Ollama CLI error code {process.returncode}", level="ERROR")
                    raise RuntimeError(f"Ollama CLI error: return code {process.returncode}")

            if not streamed:
                self.root.after(0, self.type_out_message, assistant_message + "\n\n")
            else:
                self.root.after(0, self.queue_assistant_text, "\n\n")

            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            self.log_event("AI response received")
            
        except Exception as e:
            selected_model = self.selected_model.get()
            self.log_event(f"Error calling Ollama with model {selected_model}: {e}", level="ERROR")
            error_message = (
                f"Error calling Ollama with model {selected_model}:\n{str(e)}\n"
                "Make sure Ollama is running and the selected model is installed."
            )
            self.root.after(0, lambda: self.display_message("SYSTEM", error_message, "error"))
        
        finally:
            # Stop thinking indicator
            self.root.after(0, self.stop_thinking_indicator)
            # Re-enable send button
            self.root.after(0, lambda: self.send_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.input_field.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.input_field.focus())
            self.is_processing = False
    
    def clear_chat(self):
        """Clear chat history"""
        if messagebox.askyesno("Clear Chat", "Are you sure you want to clear the conversation?"):
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.config(state=tk.DISABLED)
            self.conversation_history.clear()
            self.display_message("Assistant", "Chat cleared. How can I help you?", "assistant")
    
    def save_memory(self):
        """Save conversation history to JSON file"""
        try:
            self.backup_memory_file()
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, indent=2)
            self.log_event(f"Memory saved ({len(self.conversation_history)} messages)")
            self.display_message("SYSTEM", f">> Memory saved ({len(self.conversation_history)} messages)", "assistant")
        except Exception as e:
            self.log_event(f"Failed to save memory: {e}", level="ERROR")
            self.display_message("ERROR", f"Failed to save memory: {str(e)}", "error")
    
    def load_memory(self):
        """Load conversation history from JSON file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.conversation_history = json.load(f)
                self.log_event(f"Memory loaded ({len(self.conversation_history)} messages)")
                self.display_message("SYSTEM", f">> Memory loaded ({len(self.conversation_history)} messages)", "assistant")
                # Display loaded messages
                for msg in self.conversation_history:
                    if msg["role"] == "user":
                        self.display_message("You", msg["content"], "user")
                    elif msg["role"] == "assistant":
                        self.display_message("Assistant", msg["content"], "assistant")
            else:
                self.log_event("No saved memory found, starting fresh")
                self.display_message("SYSTEM", ">> No saved memory found. Starting fresh.", "assistant")
        except Exception as e:
            self.log_event(f"Failed to load memory: {e}", level="ERROR")
            self.display_message("ERROR", f"Failed to load memory: {str(e)}", "error")
            self.conversation_history = []


if __name__ == "__main__":
    root = tk.Tk()
    app = OllamaAssistantGUI(root)
    root.mainloop()
