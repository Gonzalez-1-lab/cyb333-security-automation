#!/usr/bin/env python3
"""
server.py - Simple multi-client TCP server (Midterm Part 1)

The server listens on a host and port, accepts client connections, and
responds to each message it receives. Each client is handled in its own
thread so more than one client can be connected at the same time.

Usage:
    python server.py                 (listens on 127.0.0.1:5000)
    python server.py --port 6000     (listens on a different port)

Commands a client can send: help, time, echo <text>, quit
"""

import argparse
import socket
import sys
import threading
from datetime import datetime

DEFAULT_HOST = "127.0.0.1"   # localhost only, so nothing outside this computer can connect
DEFAULT_PORT = 5000
BUFFER_SIZE = 1024           # maximum number of bytes read from a client at once
ENCODING = "utf-8"


def timestamp():
    """Return the current date and time as text for log messages."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(message):
    """Print a message with a timestamp (the timestamp is useful for screenshots)."""
    print(f"[{timestamp()}] {message}", flush=True)


def build_reply(message):
    """
    Decide how the server answers a client message.
    Returns a tuple: (reply_text, keep_connection_open).
    """
    text = message.strip()
    command = text.lower()

    if command == "quit":
        return "Goodbye! Closing the connection.", False
    if command == "help":
        return "Commands: help, time, echo <text>, quit", True
    if command == "time":
        return f"Server time is {timestamp()}", True
    if command.startswith("echo "):
        return f"Echo: {text[5:]}", True
    return f"Server received: {text}", True


def handle_client(conn, addr):
    """Talk to one connected client until it disconnects or sends 'quit'."""
    client = f"{addr[0]}:{addr[1]}"
    log(f"Client connected from {client}")
    try:
        # Greet the client so it knows the connection worked.
        conn.sendall("Welcome! Type 'help' for commands or 'quit' to disconnect.".encode(ENCODING))

        while True:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                # An empty read means the client closed its side of the connection.
                log(f"Client {client} disconnected")
                break

            message = data.decode(ENCODING, errors="replace").strip()
            log(f"Received from {client}: {message}")

            reply, keep_open = build_reply(message)
            conn.sendall(reply.encode(ENCODING))
            log(f"Sent to {client}: {reply}")

            if not keep_open:
                break
    except ConnectionResetError:
        log(f"Client {client} reset the connection unexpectedly")
    except OSError as error:
        log(f"Socket error with client {client}: {error}")
    finally:
        conn.close()
        log(f"Connection with {client} closed")


def valid_port(value):
    """Check that a command line port is a whole number between 1 and 65535."""
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a number")
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def main():
    parser = argparse.ArgumentParser(description="Simple TCP server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="address to listen on (default 127.0.0.1)")
    parser.add_argument("--port", type=valid_port, default=DEFAULT_PORT, help="port to listen on (default 5000)")
    args = parser.parse_args()

    # A "with" block closes the listening socket automatically when the server stops.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        # Allow the port to be reused right after the server restarts.
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            server.bind((args.host, args.port))
        except OSError as error:
            log(f"Could not start server on {args.host}:{args.port} ({error}). "
                "Is another copy already running?")
            sys.exit(1)

        server.listen()
        # A short timeout lets the loop check for Ctrl+C instead of blocking forever.
        server.settimeout(1.0)
        log(f"Server listening on {args.host}:{args.port} (press Ctrl+C to stop)")

        try:
            while True:
                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    continue  # nobody connected during this second, keep waiting
                # One thread per client so several clients can talk at once.
                thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                thread.start()
        except KeyboardInterrupt:
            log("Shutting down server (Ctrl+C pressed)")


if __name__ == "__main__":
    main()
