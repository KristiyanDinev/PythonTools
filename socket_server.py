import socket
import json
import time
import requests as rq
import threading
import subprocess
import platform
import select

is_windows = platform.system().lower() == 'windows'

"""
Client connects
- After a successful connection
 it is expected of the client to send a JSON
 text that represent the username. like: {"username": "Bob"}
 
- Then the client can do whatever it wants until it closes the connection.
"""



class ChatServer:
    def __init__(self, port=5555):
        self.message_server_prefix: str = "SERVER: "
        self.encoding = "utf-8"

        self.server_socket: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.host: str = socket.gethostbyname(socket.gethostname())
        self.port: int = port

        try:
            self.public_ip: str = rq.get('https://api.ipify.org', timeout=3).content.decode(self.encoding)
            print(f"----------------------\n" +
                  " Server Started on:\n" +
                  f" Public IP: {self.public_ip}\n" +
                  f" Host: {self.host}\n" +
                  f" Port: {self.port}\n" +
                  f"----------------------\n")
        except:
            print(f"----------------------\n" +
                  " Server Started on:\n" +
                  f" Host: {self.host}\n" +
                  f" Port: {self.port}\n" +
                  f"----------------------\n")

        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.lock = threading.RLock()
        
        # client connections {connection: (address, username)}
        self.clients: dict = {}

        # list of client_sockets
        self.disconnected_clients: list = []

    def clean_up_disconnected_clients(self):
        # Clean up any dead clients
        with self.lock:
            for client in self.disconnected_clients:
                if client not in self.clients.keys():
                    continue
                address, username = self.clients.get(client)
                client.close()
                self.clients.pop(client)
                self.broadcast_message(f"{self.message_server_prefix}{username} left the session.")
            self.disconnected_clients.clear()

    def send_message_to_client(self, client: socket, message: str) -> bool:
        try:
            # Ensure message ends with a newline
            if not message.endswith('\n'):
                message += '\n'

            client.send(message.encode(self.encoding))
            return True

        except Exception:
            with self.lock:
                if client not in self.disconnected_clients:
                    self.disconnected_clients.append(client)
                return False

    def broadcast_message(self, message, exclude_client: list = None):
        if exclude_client is None:
            exclude_client = []

        for client in self.clients:
            if client in exclude_client:
                continue

            self.send_message_to_client(client, message)

        self.clean_up_disconnected_clients()


    def auth(self, data: dict, client_socket: socket, client_address) -> bool:
        if client_socket in self.clients.keys() or "username" not in data.keys():
            return False

        username: str = data["username"]
        with self.lock:
            self.clients[client_socket] = (client_address, username)
        self.broadcast_message(
            f"{self.message_server_prefix}{username} has joined the session.",
             [client_socket])

        # Send welcome message to the new client
        self.send_message_to_client(client_socket, f"{self.message_server_prefix}Welcome {username}!")
        return True

    def _windows_send_out_command_output(self, process, client_socket: socket):
        while process.poll() is None:
            # Read from stdout
            stdout_line = process.stdout.readline()
            if stdout_line and (not self.send_message_to_client(client_socket, stdout_line.rstrip())):
                process.kill()
                return

            # Read from stderr
            stderr_line = process.stderr.readline()
            if stderr_line and (not self.send_message_to_client(client_socket, f"ERROR: {stderr_line.rstrip()}")):
                process.kill()
                return

            # Small delay to avoid CPU thrashing
            if not stdout_line and not stderr_line:
                time.sleep(0.01)

    def _linux_send_out_command_output(self, process, client_socket: socket):
        try:
            # Use select to handle both stdout and stderr non-blockingly
            while process.poll() is None:  # While the process is still running
                # Check if stdout or stderr has data to read
                readable, _, _ = select.select([process.stdout, process.stderr], [], [], 0.1)

                for stream in readable:
                    line = stream.readline()
                    if line:
                        # Send each output line to the client
                        prefix = "ERROR: " if stream == process.stderr else ""
                        if not self.send_message_to_client(client_socket, f"{prefix}{line.rstrip()}"):
                            # Client disconnected, kill process
                            process.kill()
                            return

        except Exception as e:
            self.send_message_to_client(client_socket,
                                        f"{self.message_server_prefix}Error with select: {str(e)}")

    def _send_out_the_rest_of_command_output(self, process, client_socket: socket):
        # Get any remaining output after process completes
        stdout, stderr = process.communicate()

        if stdout:
            for line in stdout.splitlines():
                if line.strip():  # Only send non-empty lines
                    self.send_message_to_client(client_socket, line)

        if stderr:
            for line in stderr.splitlines():
                if line.strip():  # Only send non-empty lines
                    self.send_message_to_client(client_socket, f"ERROR: {line}")

        # Send completion message with return code
        self.send_message_to_client(
            client_socket,
            f"{self.message_server_prefix}Command completed with exit code: {process.returncode}"
        )

    def execute_command(self, command: str, client_socket: socket):
        """Execute a command and stream output to the client in real-time"""
        try:
            # Get the username for logging
            with self.lock:
                if client_socket not in self.clients:
                    return

            # Notify client that command execution is starting
            self.send_message_to_client(client_socket, f"{self.message_server_prefix}Executing: {command}")

            # Start the process with pipes for stdout and stderr
            process = subprocess.Popen(
                command,
                shell=True,  # Use shell to handle complex commands
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,  # Line buffered
                universal_newlines=True,  # Text mode
                text = True  # Ensure text mode for Python 3.7+
            )

            if is_windows:
                self._windows_send_out_command_output(process, client_socket)

            else:
                self._linux_send_out_command_output(process, client_socket)

            self._send_out_the_rest_of_command_output(process, client_socket)

        except Exception as e:
            self.send_message_to_client(client_socket,
                                        f"{self.message_server_prefix}Error executing command: {str(e)}")

    def client_messages(self, data: dict, client_socket: socket):
        message = data.get("say")
        command = data.get("cmd")

        with self.lock:
            client_address, username = self.clients.get(client_socket)

        if message is not None:
            self.broadcast_message(f"{username}: {message}", [])

        elif command is not None:
            threading.Thread(
                target=self.execute_command,
                args=(command, client_socket),
                daemon=True
            ).start()

    def handle_client(self, client_socket: socket, address):
        """Handle a single client connection"""
        # First message should be the username

        # address[0] = IP
        # address[1] = PORT

        try:
            while True:
                data_received = client_socket.recv(1024).decode(self.encoding)
                if not data_received:  # Client disconnected
                    break

                data: dict = json.loads(data_received)

                if self.auth(data, client_socket, address):
                    continue

                self.client_messages(data, client_socket)

        except Exception:
            pass

        finally:
            # Clean up when client disconnects
            with self.lock:
                self.disconnected_clients.append(client_socket)
            self.clean_up_disconnected_clients()

    def run(self):
        """Run the server and accept connections"""
        try:
            while True:
                # Accept new connections
                client_socket, address = self.server_socket.accept()

                # Start a new thread to handle this client
                #Process(target=self.handle_client, args=(client_socket, address), daemon=True).start()
                threading.Thread(target=self.handle_client, args=(client_socket, address), daemon=True).start()
        
        except KeyboardInterrupt:
            print("Server is shutting down...")

        finally:
            # Clean up
            with self.lock:
                self.disconnected_clients.extend(self.clients)
            self.clean_up_disconnected_clients()
            self.server_socket.close()

if __name__ == "__main__":
    ChatServer().run()