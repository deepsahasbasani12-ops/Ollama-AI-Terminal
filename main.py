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
        self.root.title("Ollama System GUI Terminal")
        self.root.state('zoomed')  # Fullscreen mode on Windows
        
        self.conversation_history = []
        self.is_processing = False
        self.selected_model = tk.StringVar(value='qwen2:1.5b')
        app_data_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "OllamaTerminal")
        os.makedirs(app_data_dir, exist_ok=True)
        self.memory_file = os.path.join(app_data_dir, "conversation_memory.json")
        self.ollama_binary = None
        self.ollama_error = None
        
        # Password protection
        if not self.check_password():
            self.root.destroy()
            return
        
        # Create GUI elements
        self.setup_ui()
        
        # Ensure Ollama is visible to this app, especially when running as an exe
        self.configure_ollama_path()
        
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
            text="◆ OLLAMA AI TERMINAL ◆",
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
            values=['qwen2:0.5b', 'qwen2:1.5b', 'phi3:mini', 'deepseek-coder:1.3b', 'qwen2.5-coder:1.5b', 'qwen2.5-coder:0.5b'],
            font=("Courier New", 10),
            state='readonly',
            width=20
        )
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
        
        # Initial message
        self.display_message("SYSTEM", ">> Ollama AI Terminal v1.0", "assistant")
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
        else:
            self.ollama_error = (
                "Ollama executable not found. Install Ollama or place it on PATH, "
                "then restart the app."
            )
            self.display_message("ERROR", self.ollama_error, "error")

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
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{sender}: ", tag)
        self.chat_display.insert(tk.END, f"{message}\n\n")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def send_message(self):
        """Send user message and get AI response"""
        user_input = self.input_field.get().strip()
        
        if not user_input:
            return
        
        # Display user message
        self.display_message("You", user_input, "user")
        self.input_field.delete(0, tk.END)
        
        # Check if user is trying to open an app
        if user_input.lower().startswith("open "):
            app_name = user_input[5:].strip().lower()
            self.handle_open_app(app_name)
            return
        
        # Check if user is trying to close an app
        if user_input.lower().startswith("close "):
            app_name = user_input[6:].strip().lower()
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
            "cmd": ["cmd.exe"],
            "command prompt": ["cmd.exe"],
            "powershell": ["powershell.exe"],
            "code": ["code"],
            "vscode": ["code"],
            "python": [sys.executable, "-m", "idlelib.idle"],
            "idle": [sys.executable, "-m", "idlelib.idle"]
        }
        
        if app_name in app_commands:
            try:
                cmd = app_commands[app_name]
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
    
    def get_ai_response(self):
        """Get response from Ollama AI via CLI or Python module"""
        try:
            if self.ollama_error:
                raise RuntimeError(self.ollama_error)
            
            selected_model = self.selected_model.get()
            
            # Try Python module first
            try:
                response = ollama.chat(
                    model=selected_model,
                    messages=self.conversation_history,
                    stream=False
                )
                assistant_message = response['message']['content']
            except (ImportError, ModuleNotFoundError):
                # Fallback: use Ollama CLI directly
                if not self.ollama_binary:
                    raise RuntimeError("Ollama CLI not found and Python module unavailable")
                
                import json as json_module
                messages_json = json_module.dumps(self.conversation_history)
                result = subprocess.run(
                    [self.ollama_binary, "run", selected_model, "--nostream"],
                    input=messages_json,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode != 0:
                    raise RuntimeError(f"Ollama CLI error: {result.stderr}")
                
                assistant_message = result.stdout.strip()
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            # Display assistant message
            self.root.after(0, lambda: self.display_message("Assistant", assistant_message, "assistant"))
            
        except Exception as e:
            selected_model = self.selected_model.get()
            error_message = (
                f"Error calling Ollama with model {selected_model}:\n{str(e)}\n"
                "Make sure Ollama is running and the selected model is installed."
            )
            self.root.after(0, lambda: self.display_message("SYSTEM", error_message, "error"))
        
        finally:
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
            with open(self.memory_file, 'w') as f:
                json.dump(self.conversation_history, f, indent=2)
            self.display_message("SYSTEM", f">> Memory saved ({len(self.conversation_history)} messages)", "assistant")
        except Exception as e:
            self.display_message("ERROR", f"Failed to save memory: {str(e)}", "error")
    
    def load_memory(self):
        """Load conversation history from JSON file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    self.conversation_history = json.load(f)
                self.display_message("SYSTEM", f">> Memory loaded ({len(self.conversation_history)} messages)", "assistant")
                # Display loaded messages
                for msg in self.conversation_history:
                    if msg["role"] == "user":
                        self.display_message("You", msg["content"], "user")
                    elif msg["role"] == "assistant":
                        self.display_message("Assistant", msg["content"], "assistant")
            else:
                self.display_message("SYSTEM", ">> No saved memory found. Starting fresh.", "assistant")
        except Exception as e:
            self.display_message("ERROR", f"Failed to load memory: {str(e)}", "error")
            self.conversation_history = []


if __name__ == "__main__":
    root = tk.Tk()
    app = OllamaAssistantGUI(root)
    root.mainloop()

