import socket
import json
import threading
import time
import shutil

class ChatClient:
    def __init__(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        self.username = ""
        self.receiving_lock = threading.Lock()
        self.input_lock = threading.Lock()

        # Try to determine terminal width
        try:
            self.terminal_width = shutil.get_terminal_size().columns
        except:
            self.terminal_width = 100  # Default fallback width

    def connect(self, username):
        """Connect to the server and send username"""
        try:
            # Connect to server
            self.client_socket.connect((self.host, self.port))
            self.username = username

            # Send username to server in JSON format as expected by server
            username_data = json.dumps({"username": username})
            self.client_socket.send(username_data.encode('utf-8'))

            self.connected = True

            # Start thread to receive messages
            threading.Thread(target=self.receive_messages, daemon=True).start()

            # Start the input thread
            threading.Thread(target=self.handle_input, daemon=True).start()

            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def send_message(self, message):
        """Send a message to the server"""
        if not self.connected:
            print("Not connected to server")
            return False

        try:
            # Format message as JSON as expected by the server
            message_data = json.dumps(message)
            self.client_socket.send(message_data.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            self.connected = False
            return False

    def clear_line(self):
        """Clear the current terminal line properly"""
        # Update terminal width in case it changed (e.g., window resize)
        try:
            self.terminal_width = shutil.get_terminal_size().columns
        except:
            pass  # Keep the previous value if we can't get a new one

        return f"\r{' ' * self.terminal_width}\r"

    def receive_messages(self):
        """Continuously receive messages from the server"""
        while self.connected:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if not message:
                    with self.receiving_lock:
                        print("\nConnection to server lost")
                    self.connected = False
                    break

                with self.receiving_lock:
                    # Clear the current line properly and print the message
                    print(f"{self.clear_line()}{message}")
                    print("> ", end='', flush=True)  # Show prompt again

            except Exception as e:
                with self.receiving_lock:
                    print(f"\nError receiving message: {e}")
                self.connected = False
                break

    def format_input_message(self, message: str) -> str:
        data: dict = dict()
        if message.startswith("say "):
            data["say"] = message[4:]
        else:
            data["cmd"] = message
        return json.dumps(data, indent=4)

    def handle_input(self):
        """Handle user input in a separate thread"""
        time.sleep(1)  # Short delay to allow initial server messages

        print("Connected! Type 'quit' to exit.")
        print("> ", end='', flush=True)

        while self.connected:
            try:
                with self.input_lock:
                    user_input = input()

                if not self.connected:
                    break

                lower: str = user_input.lower()
                if lower == 'quit':
                    self.connected = False
                    break

                elif lower == "help":
                    print("Write: say Hello (to send a message to all connected clients).")
                    print("Write: help (to get the help menu).")
                    print("Any other inputs are considered a command to execute on the server.")
                    continue


                if user_input:  # Only send non-empty messages
                    self.send_message(self.format_input_message(user_input))

                # Re-display prompt
                print("> ", end='', flush=True)

            except EOFError:
                break
            except KeyboardInterrupt:
                self.connected = False
                break

    def disconnect(self):
        """Disconnect from the server"""
        if hasattr(self, 'client_socket'):
            try:
                self.client_socket.close()
            except:
                pass
        self.connected = False
        print("\nDisconnected from server")


def main():
    # Get server details
    server_ip = input("Server IP (press Enter for default 127.0.0.1): ")
    if not server_ip:
        server_ip = '127.0.0.1'

    server_port = input("Server PORT (press Enter for default 5555): ")
    if not server_port:
        server_port = 5555
    else:
        try:
            server_port = int(server_port)
        except ValueError:
            print("Invalid port. Using default 5555.")
            server_port = 5555

    # Create client instance
    client = ChatClient(host=server_ip, port=server_port)

    # Get username
    username = input("Enter your username: ")
    while not username:
        username = input("Username cannot be empty. Please enter a username: ")

    print(f"Connecting to server at {server_ip}:{server_port} as {username}...")

    # Connect to server
    if not client.connect(username):
        print("Failed to connect to server")
        return

    # Main thread will wait here until user quits
    try:
        while client.connected:
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()