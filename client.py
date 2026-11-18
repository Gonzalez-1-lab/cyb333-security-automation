#!/usr/bin/env python3
"""
client.py - Simple TCP client (Midterm Part 1)

Connects to server.py, sends messages typed by the user, and prints the
server's replies. Type 'quit' to disconnect cleanly.

Usage:
    python client.py                 (connects to 127.0.0.1:5000)
    python client.py --port 6000
"""

import argparse
import socket
import sys
from datetime import datetime

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
BUFFER_SIZE = 1024
ENCODING = "utf-8"
CONNECT_TIMEOUT = 5   # seconds to wait when connecting


def log(message):
    """Print a message with a timestamp (useful for screenshots)."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)


def valid_port(value):
    """Check that a command line port is a whole number between 1 and 65535."""
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a number")
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def connect(host, port):
    """Open a connection to the server and return the socket, or exit with a clear message."""
    try:
        return socket.create_connection((host, port), timeout=CONNECT_TIMEOUT)
    except ConnectionRefusedError:
        # This is the error shown when the server is not running.
        log(f"Connection refused: no server is listening on {host}:{port}. Start server.py first.")
    except socket.timeout:
        log(f"Connection timed out after {CONNECT_TIMEOUT} seconds. Check the host and port.")
    except socket.gaierror:
        log(f"Could not find host '{host}'. Check the spelling of the host name.")
    except OSError as error:
        log(f"Could not connect: {error}")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Simple TCP client")
    parser.add_argument("--host", default=DEFAULT_HOST, help="server address (default 127.0.0.1)")
    parser.add_argument("--port", type=valid_port, default=DEFAULT_PORT, help="server port (default 5000)")
    args = parser.parse_args()

    sock = connect(args.host, args.port)
    log(f"Connected to server at {args.host}:{args.port}")

    # "with" makes sure the socket is closed no matter how the loop ends.
    with sock:
        sock.settimeout(10)  # do not wait forever for a reply
        try:
            greeting = sock.recv(BUFFER_SIZE).decode(ENCODING)
            log(f"Server says: {greeting}")

            while True:
                try:
                    message = input("Enter message (quit to exit): ").strip()
                except EOFError:
                    message = "quit"      # input stream ended, disconnect cleanly
                if not message:
                    continue              # ignore empty lines

                sock.sendall(message.encode(ENCODING))
                reply = sock.recv(BUFFER_SIZE)
                if not reply:
                    log("Server closed the connection")
                    break
                log(f"Server replied: {reply.decode(ENCODING)}")

                if message.lower() == "quit":
                    log("Disconnected cleanly")
                    break
        except socket.timeout:
            log("The server took too long to respond")
        except (ConnectionResetError, BrokenPipeError):
            log("The connection to the server was lost")
        except KeyboardInterrupt:
            log("Client stopped (Ctrl+C pressed)")
        except OSError as error:
            log(f"Socket error: {error}")


if __name__ == "__main__":
    main()
