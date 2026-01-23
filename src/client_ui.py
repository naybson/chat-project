import tkinter as tk
from tkinter import scrolledtext

from client_logic import UsernameDialog, ChatClientLogic

# ============================================================
# UI Theme
# ============================================================

BG = "#1e1e1e"
PANEL = "#252526"
TEXT = "#d4d4d4"
ACCENT = "#0e639c"
ENTRY = "#333333"
INACTIVE = "#555555"
# ============================================================
# UI Class (inherits logic)
# ============================================================

class ChatClientGUI(ChatClientLogic):
    def build_ui(self):
        # sets the title size and background color
        self.root.title(f"Chat Client - {self.username}")
        self.root.geometry("800x500")
        self.root.configure(bg=BG)

        # ---------- Header ----------
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(
            header,
            text=f"Hello: {self.username.capitalize()}",
            fg=ACCENT,
            bg=BG,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")

        self.chat_label = tk.Label(
            header, text="Chatting with: GLOBAL", fg=TEXT, bg=BG
        )
        self.chat_label.pack(anchor="w")

        # ---------- Main ----------
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.chat_area = scrolledtext.ScrolledText(
            main, bg=PANEL, fg=TEXT, state="disabled", wrap=tk.WORD
        )
        self.chat_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ---------- Right Panel ----------
        right = tk.Frame(main, bg=BG, width=200)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        tk.Label(right, text="Members", bg=BG, fg=TEXT).pack(anchor="w")

        self.members = tk.Listbox(
            right, bg=PANEL, fg=TEXT, selectbackground=ACCENT
        )
        self.members.pack(fill=tk.X)
        self.members.bind("<<ListboxSelect>>", self.select_member)

        # STORE GLOBAL BUTTON
        self.global_btn = tk.Button(
            right,
            text="GLOBAL CHAT",
            bg=ACCENT,          # global is default
            fg="white",
            command=self.select_global,
        )
        self.global_btn.pack(fill=tk.X, pady=10)

        # ---------- Bottom ----------
        bottom = tk.Frame(self.root, bg=BG)
        bottom.pack(fill=tk.X, padx=10, pady=5)

        self.entry = tk.Entry(
            bottom, bg=ENTRY, fg=TEXT, insertbackground=TEXT
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        self.entry.bind("<Return>", self.send)

        tk.Button(
            bottom, text="Send", bg=ACCENT, fg="white", command=self.send
        ).pack(side=tk.RIGHT)

    # ========================================================
    # UI helpers (CALLED FROM LOGIC)
    # ========================================================

    def update_global_button(self):
        if self.current_mode == "global":
            self.global_btn.config(bg=ACCENT)
        else:
            self.global_btn.config(bg=INACTIVE)


# ============================================================
# Entry point
# ============================================================
if __name__ == "__main__":
    root = tk.Tk() # creates the main application
    root.withdraw() # hide the window (until we select a username)

    # open the select a username box
    dialog = UsernameDialog(root)
    if not dialog.username:
        exit()

    # makes the main window visable again
    root.deiconify()

    # creates the UI window
    gui = ChatClientGUI(root, dialog.username, dialog.sock)

    #handle the first message from the server
    if dialog._first_server_line:
        gui.queue.put(dialog._first_server_line)

    # starts the UI loop
    root.mainloop()
