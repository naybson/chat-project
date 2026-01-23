import socket
import threading

# Server Configuration
HOST = "127.0.0.1"
PORT = 12345

# clients: maps username (lowercase) -> socket
# lock: protects access to shared state across threads

clients = {}
lock = threading.Lock()

# Usernames that are not allowed (commands / system names)
BLACKLISTED_NAMES = {
    "system", "admin", "server",
    "global", "everyone",
    "who", "dm", "bye"
}
# Utility Functions

def broadcast(message):
    # Send a message to all connected clients.
    # Errors are ignored so one broken client
    # does not crash the server.
    for sock in list(clients.values()):
        try:
            # we add \n to mark the end of the message
            sock.send((message + "\n").encode())
        except:
            pass


def send_to(username, message):
    # Send a message to a specific user (if online).
    sock = clients.get(username)
    if sock:
        # we add \n to mark the end of the message
        sock.send((message + "\n").encode())


def broadcast_user_list():
    # Sends the current online user list to all clients.
    # Format is parsed by the client UI.
    users = ", ".join(sorted(clients.keys()))
    broadcast(f"[system] Online: {users}")

def recv_line(sock):
    # Reads one byte at a time until we see a \n
    # this marks the end of the message
    data = ""
    while not data.endswith("\n"):
        chunk = sock.recv(1).decode()
        if not chunk:
            return None
        data += chunk
    return data.strip()

# ============================================================
# Client Handling
# ============================================================

def handle_client(client_socket, address):
    # Handles a single client connection.
    # Runs in its own thread.
    username = None
    try:
        # Initial handshake: receive username
        username = recv_line(client_socket)
        if not username:
            return

        clean = username.strip().lower()
        # Username validation
        if " " in clean:
            client_socket.send(
                "[system] ERROR: Username cannot contain spaces\n".encode()
            )
            client_socket.close()
            return

        # if username contains "/" send an error
        if clean.startswith("/"):
            client_socket.send(
                "[system] ERROR: Name cannot start with '/'\n".encode()
            )
            client_socket.close()
            return

        # if username does not contian acsii chacters send an error
        if not clean.isalnum():
            client_socket.send(
                "[system] ERROR: Name must be letters/numbers only\n".encode()
            )
            client_socket.close()
            return
        
        # if the username is one of the blacklisted ones
        if clean in BLACKLISTED_NAMES:
            client_socket.send(
                "[system] ERROR: Name is reserved\n".encode()
            )
            client_socket.close()
            return

        # Register client (thread-safe)
        with lock:
            if clean in clients:
                client_socket.send(
                    "[system] ERROR: Name already taken\n".encode()
                )
                client_socket.close()
                return

            clients[clean] = client_socket
        username = clean

        # Welcome + notify others
        send_to(username, "[system] Connected to server")
        broadcast(f"[system] {username} joined the server")
        broadcast_user_list()

        # Main message loop
        while True:
            data = client_socket.recv(1024)
            if not data:
                break

            for msg in data.decode().splitlines():
                msg = msg.strip()
                if not msg:
                    continue

                # Client disconnect command
                if msg == "/bye":
                    return

                # Direct Message: /dm <user> <message>
                if msg.startswith("/dm "):
                    parts = msg.split(" ", 2)

                    if len(parts) < 3:
                        send_to(
                            username,
                            "[system] Usage: /dm <user> <message>"
                        )
                        continue

                    target, text = parts[1], parts[2]

                    if target == username:
                        send_to(
                            username,
                            "[system] Cannot DM yourself"
                        )
                        continue

                    if target not in clients:
                        send_to(
                            username,
                            f"[system] User '{target}' not online"
                        )
                        continue

                    send_to(target, f"[DM from {username}] {text}")
                    send_to(username, f"[DM to {target}] {text}")
                    continue

                # Global message
                broadcast(f"[{username}] {msg}")

    finally:
        # Cleanup on disconnect
        with lock:
            if username in clients:
                del clients[username]

        client_socket.close()

        if username:
            broadcast(f"[system] {username} left the server")
            broadcast_user_list()


# ============================================================
# Server Startup
# ============================================================
def start_server():
    # Starts the TCP server and accepts clients forever.
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    print(f"Server listening on {HOST}:{PORT}")

    while True:
        sock, addr = server.accept()
        threading.Thread(
            target=handle_client,
            args=(sock, addr),
            daemon=True
        ).start()


if __name__ == "__main__":
    start_server()
