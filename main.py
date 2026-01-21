import tkinter as tk
import subprocess
import sys
import os
import time

BG = "#1e1e1e"
PANEL = "#252526"
TEXT = "#d4d4d4"
ACCENT = "#0e639c"

# Creates the chat menu launcher
class ChatLauncher:

    # create the design of the chat menu launcher
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Launcher")
        self.root.geometry("300x220")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.server_process = None

        self.build_ui()

    # Creates the text label "Chat system laucnher at the top"
    def build_ui(self):
        tk.Label(
            self.root,
            text="Chat System Launcher",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=15)

    # Creates the start server button when pressed runs the methoed "start_server"
        self.server_btn = tk.Button(
            self.root,
            text="Start Server",
            bg=ACCENT,
            fg="white",
            command=self.start_server, # runs the server when pressed
            height=2,
        )
        self.server_btn.pack(fill=tk.X, padx=30, pady=5) # adds padding between the start server button to the client button

        # create client button
        self.client_btn = tk.Button(
            self.root,
            text="Open New Client",
            bg=PANEL,
            fg=TEXT,
            command=self.start_client,
            height=2,
            state="disabled",
        )
        self.client_btn.pack(fill=tk.X, padx=30, pady=5) # adds padding between the client button and the server statues message

        # adds the sever statues message
        self.status = tk.Label(
            self.root,
            text="Server not running",
            bg=BG,
            fg="#ff6666",
        )
        self.status.pack(pady=10)

    # ===== Actions =====
    def start_server(self):
        if self.server_process: # makes sure the server does not start twice
            return

        # starts the server by running the file server.py
        # see start_server function at server.py to see the server start proccess (line 225)
        python = sys.executable
        self.server_process = subprocess.Popen(
            [python, "server.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Give server a moment to boot
        time.sleep(0.5)

        self.status.config(text="Server running", fg="#6aff6a")
        self.server_btn.config(state="disabled")
        self.client_btn.config(state="normal")

    # creates a new client and opens their own chat window
    # see client creation proccess at line 105 in client_ui.py
    def start_client(self):
        python = sys.executable
        subprocess.Popen([python, "client_ui.py"])

    # when we close the window, end the process
    def on_close(self):
        if self.server_process:
            self.server_process.terminate()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatLauncher(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
