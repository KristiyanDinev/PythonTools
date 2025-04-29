import socket
import json
import threading

class ChatClient:
    def __init__(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        self.lock = threading.RLock()

        self.username_json = {"username": ""}
    
    def connect(self, username: str):
        """Connect to the server and send username"""
        try:
            self.client_socket.connect((self.host, self.port))
            
            # Send username to server
            self.username_json["username"] = username
            self.client_socket.send(json.dumps(self.username_json).encode('utf-8'))

            self.connected = True

            threading.Thread(target=self.receive_messages, daemon=True).start()

            print("Connected! Type 'quit' to exit.")
            return True

        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def send_message(self, message: str):
        """Send a message to the server"""
        if not self.connected:
            print("Not connected to server")
            return False
        
        try:
            self.client_socket.send(message.encode('utf-8'))
            return True

        except Exception as e:
            print(f"Error sending message: {e}")
            self.connected = False
            return False
    
    def receive_messages(self):
        """Continuously receive messages from the server"""
        while self.connected:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                #if not message:
                #    print("Connection to server lost")
                #    self.connected = False
                #    break

                with self.lock:
                    print(message)

            except Exception as e:
                print(f"Error receiving message: {e}")
                self.connected = False
                break

    def input_message(self):
        # Main loop for sending messages
        try:
            while self.connected:
                with self.lock:
                    message = input()

                if message.lower() == 'quit':
                    break

                if not self.send_message(message):
                    print("Message could not be sent")
                    break

        except KeyboardInterrupt:
            print("\nDisconnecting...")

        finally:
            self.disconnect()
            self.connected = False
    
    def disconnect(self):
        """Disconnect from the server"""
        if self.connected:
            self.connected = False
            self.client_socket.close()
            print("Disconnected from server")

def main():

    ip = input("Server IP: ")
    port = None
    try:
        port = int(input("Server PORT: "))
    except Exception:
        return

    client = ChatClient()
    if len(ip) == 0:
        client = ChatClient(port=5555)

    elif port is None:
        client = ChatClient(host=ip)

    else:
        client = ChatClient(host=ip, port=port)
    
    # Get username
    username = input("Enter your username: ")
    print(f"Connecting to server as {username}...")
    
    # Connect to server
    if not client.connect(username):
        print("Failed to connect to server")
        return

    threading.Thread(target=client.input_message(), daemon=True).start()


if __name__ == "__main__":
    main()

# TODO: Fix: Client randomly disconnects.
