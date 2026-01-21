import socket
import threading
import queue

# ============================================================
# Configuration
# ============================================================

HOST = "127.0.0.1"
PORT = 12345

BG = "#1e1e1e"
PANEL = "#252526"
TEXT = "#d4d4d4"
ACCENT = "#0e639c"
ENTRY = "#333333"
INACTIVE = "#555555"

# ============================================================
# Username Dialog (logic + small UI)
# Ask the username for thier name
# connects them to the server
# prformes handshake
# ============================================================

class UsernameDialog:
    def __init__(self, root):
        self.username = None
        self.sock = None
        self._first_server_line = None

        #===========================
        # === PICK A USERNAME UI ===

        import tkinter as tk # a library that handles UI elemts
        
        # Create a window (UI handling)
        win = tk.Toplevel(root)
        win.title("Choose username")
        win.geometry("340x190")
        win.configure(bg="#1e1e1e")
        win.resizable(False, False)
        
        # Creats the Static Text for the box
        tk.Label(win, text="Username:", bg="#1e1e1e", fg="#d4d4d4").pack(pady=(12, 6))

        # Creates the entry box
        entry = tk.Entry(
            win, bg="#333333", fg="#d4d4d4", insertbackground="#d4d4d4"
        )
        entry.pack(fill=tk.X, padx=20)
        entry.focus_set()
        
        # creates the error messages segment
        status = tk.Label(win, text="", bg="#1e1e1e", fg="#ff6666")
        status.pack(pady=(8, 0))

        #===========================
        # This function acts as the handshake handler
        # Loops one byte at a time until we get \n
        def recv_line(sock):
            data = ""
            while not data.endswith("\n"):
                chunk = sock.recv(1).decode(errors="ignore")
                if not chunk:
                    return None
                data += chunk
            return data.strip()

        # Handles username submition
        def submit(_=None):
            name = entry.get().strip()

            # if the user entered nothing
            if not name:
                status.config(text="Error: username required")
                return

            # if there is a space in the name
            if " " in name:
                status.config(text="Error: username cannot contain spaces")
                return
            
            # Creates a TCP socket and connects it to the server
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((HOST, PORT))
                s.send((name + "\n").encode()) # sends the given name the username entered and inserts a \n to mark the end

                # Wait for the server to respond
                first = recv_line(s)
                if not first: # if no respnse, send an error
                    status.config(text="Error: server closed connection")
                    s.close()
                    return

                # if we get an error close the connection
                if first.startswith("[system] ERROR:"):
                    status.config(
                        text=first.replace("[system] ERROR:", "Error:").strip()
                    )
                    s.close()
                    return

                # if all went well set the username and the socket
                self.username = name
                self.sock = s
                self._first_server_line = first
                win.destroy() # close the dialog window

            # if somthing happend and it failed send an error message
            except Exception as e:
                status.config(text=f"Error: {e}")
                try:
                    s.close()
                except:
                    pass
        
        # create the join button and if we press it run submit
        entry.bind("<Return>", submit)
        tk.Button(
            win, text="Join", bg="#0e639c", fg="white", command=submit
        ).pack(pady=12)

        win.grab_set()
        root.wait_window(win)


# ============================================================
# Chat Client Logic (NO widget creation here)
# this class is create after the handshake succeed and 
# the socket is created
# ============================================================

class ChatClientLogic:
    def __init__(self, root, username, sock):
        # Store this values inside this object
        self.root = root
        self.username = username.lower()
        self.sock = sock

        # Chat context (what state am i in?)
        self.current_mode = "global"
        self.current_target = None

        # State
        self.chat_history = {"global": []}
        self.unread_dms = set()
        self.known_users = []

        # UI helpers
        self.member_map = {}
        self.queue = queue.Queue()

        # Build UI (implemented by UI subclass)
        self.build_ui()
        
        # makes a thread that waits for messages in the UI
        threading.Thread(target=self.receive, daemon=True).start()
        self.root.after(100, self.process_messages)

    # ========================================================
    # Networking
    # These function bridges bettwen the UI world and 
    # the network world
    # ========================================================

    def receive(self):
        """
        Background network thread.
        Blocks on socket.recv() and pushes incoming data
        into a thread-safe queue for the UI thread to process.
        """
        while True:
            try:
                data = self.sock.recv(1024) # blocking call (safe in background thread)
                if not data:
                    break
                self.queue.put(data.decode()) # hand off data to UI thread
            except:
                break
            
    def process_messages(self):
        """
        Runs on the Tkinter UI thread.
        Periodically checks the queue for messages received
        by the network thread and updates the UI accordingly.
        """
        while not self.queue.empty():
            for msg in self.queue.get().splitlines():
                self.handle_message(msg.strip())

        # Schedule next non-blocking check on the UI event loop
        self.root.after(100, self.process_messages)

    # ========================================================
    # Message handling
    # ========================================================
    
    # if an empty message is recived skip it
    def handle_message(self, msg):
        if not msg:
            return

        # if we recive [system] Online: message we send again all the
        # users that are online
        if msg.startswith("[system] Online:"):
            users = msg.split(":", 1)[1].strip().split(", ")
            self.known_users = users[:]
            self.update_members(self.known_users)
            self.chat_history["global"].append(msg)
            if self.current_mode == "global":
                self.load_chat("global")
            return

        # if we recive system messages, put them in global chat
        if msg.startswith("[system]"):
            self.chat_history["global"].append(msg)
            if self.current_mode == "global":
                self.load_chat("global")
            return

        # if we get a  private message put it in the recpected user
        # private chat
        if msg.startswith("[DM from"):
            sender = msg.split("]", 1)[0].split()[-1]
            text = msg.split("]", 1)[1].strip()
            self.chat_history.setdefault(sender, []).append(f"[{sender}] {text}")

            # if i am not viewing the private chat with the sender
            # mark thier name as having an unread message
            if self.current_target != sender:
                self.unread_dms.add(sender)
                self.refresh_members()
            else:
                # else update the chat
                self.load_chat(sender)
            return

        # This handles outgoing private messages echoed by the server 
        # and stores them in the local private chat history under the target user
        if msg.startswith("[DM to"):
            target = msg.split("]", 1)[0].split()[-1]
            text = msg.split("]", 1)[1].strip()
            self.chat_history.setdefault(target, []).append(f"[Me] {text}")
            if self.current_target == target:
                self.load_chat(target)
            return

        # Handle standard global chat messages (e.g. "[user] message").
        # Messages are stored in the global chat history and displayed
        # when the user is currently viewing the global chat.
        if msg.startswith("["):
            self.chat_history["global"].append(msg)
            if self.current_mode == "global":
                self.load_chat("global")

    # ========================================================
    # Member handling
    # ========================================================
    def update_members(self, users):
        # clears the members list
        self.members.delete(0, "end")
        self.member_map = {}
        selected_index = None

        # runs for all online users
        for u in users:
            if u == self.username:
                continue  # dont show yourself

            display = u.capitalize()

            # unread DM indicator
            if u in self.unread_dms:
                display = f"● {display}"

            # add the user to the list in the UI
            self.members.insert("end", display)
            idx = self.members.size() - 1
            self.member_map[idx] = u

            # color highlight for unread
            if u in self.unread_dms:
                self.members.itemconfig(idx, fg=ACCENT)
            else:
                self.members.itemconfig(idx, fg=TEXT)

            # if we rebuild the member list, make sure slection would not jump around
            if self.current_mode == "dm" and self.current_target == u:
                selected_index = idx
        # restore selction
        if selected_index is not None:
            self.members.selection_set(selected_index)

    def refresh_members(self):
        self.update_members(self.known_users)

    # runs when we click a name in the listbox
    def select_member(self, _):
        sel = self.members.curselection() #no slection, do nothing
        if not sel:
            return

        # translate the index into name
        name = self.member_map[sel[0]]

        # Switch context to DM
        self.current_mode = "dm"
        self.current_target = name

        # Clear unread flag
        self.unread_dms.discard(name)
        self.refresh_members()

        # Update header
        self.chat_label.config(text=f"Chatting with: {name}")
        self.load_chat(name)


    # if we select the global buttom switch to global mode
    def select_global(self):
        self.current_mode = "global"
        self.current_target = None

        self.global_btn.config(bg=ACCENT)

        self.chat_label.config(text="Chatting with: GLOBAL")
        self.load_chat("global")

    # ========================================================
    # Chat display & sending
    # ========================================================

    # display the chat history given global or DM in the text box
    def load_chat(self, key):
        self.chat_area.config(state="normal") #let tinker update text
        self.chat_area.delete(1.0, "end") # clears the chat box
        for msg in self.chat_history.get(key, []): # pulls all the messages from the history
            self.chat_area.insert("end", msg + "\n")
        self.chat_area.config(state="disabled")#disable tinker for updateing the text
    
    # sends a message (DM or Global)
    def send(self, _=None): 

        # prevents empty message
        msg = self.entry.get().strip()
        if not msg:
            return

        # clear the input from the message box
        self.entry.delete(0, "end")

        # if the message is dm send a command to the server to send a dm to the selected client
        if self.current_mode == "dm":
            self.sock.send(f"/dm {self.current_target} {msg}\n".encode())
        else:
            # if its a global message, the server may broadcast to everyone
            self.sock.send((msg + "\n").encode())
