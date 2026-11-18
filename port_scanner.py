#!/usr/bin/env python3
"""
port_scanner.py - Simple TCP port scanner (Midterm Part 2)

Scans a range (or list) of TCP ports on an AUTHORIZED target and reports
which ports are open, closed, or filtered.

AUTHORIZED TARGETS ONLY: localhost, 127.0.0.1, and scanme.nmap.org.
The script refuses to scan anything else, and it adds a delay between
connection attempts so it does not scan aggressively.

Usage examples:
    python port_scanner.py localhost -p 80,443,22,21
    python port_scanner.py 127.0.0.1 -s 4990 -e 5010
    python port_scanner.py scanme.nmap.org -p 22,80,443 --delay 0.5
"""

import argparse
import errno
import socket
import sys
import time
from datetime import datetime

# The only hosts this scanner is allowed to scan (assignment rule).
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "scanme.nmap.org"}
LOCAL_HOSTS = {"localhost", "127.0.0.1"}
MAX_REMOTE_PORTS = 100          # limit how many ports are scanned on a remote host
DEFAULT_DELAY = 0.05            # seconds to pause between connection attempts
DEFAULT_TIMEOUT = 1.0           # seconds to wait for each port to answer

# Error numbers that mean "the port answered and refused", i.e. the port is closed.
REFUSED = {errno.ECONNREFUSED, 10061, 111}
# Error numbers that mean the host cannot be reached at all.
UNREACHABLE = {errno.ENETUNREACH, errno.EHOSTUNREACH, 10051, 10065, 101, 113}


def now():
    """Return the current time for output lines."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_port(value):
    """Convert text to a valid port number (1 to 65535) or raise a friendly error."""
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid port number")
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"port {port} is out of range (use 1 to 65535)")
    return port


def parse_port_list(value):
    """Turn '80,443,22' into a list of valid port numbers."""
    return [parse_port(item.strip()) for item in value.split(",") if item.strip()]


def service_name(port):
    """Look up the common service name for a port (for example 22 is ssh)."""
    try:
        return socket.getservbyport(port, "tcp")
    except OSError:
        return "unknown"


def probe_port(ip, port, timeout):
    """
    Try to connect to one port.
    Returns "open", "closed", or "filtered", or raises OSError if the host is unreachable.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((ip, port))
        except socket.timeout:
            return "filtered"          # no answer within the timeout
        if result == 0:
            return "open"              # connection succeeded
        if result in REFUSED:
            return "closed"            # host answered and refused the connection
        if result in UNREACHABLE:
            raise OSError(result, "host or network unreachable")
        return "filtered"              # anything else, usually no response


def build_port_list(args):
    """Create the list of ports to scan from the command line options."""
    if args.ports:
        ports = sorted(set(args.ports))
    else:
        if args.start > args.end:
            raise ValueError("start port must not be larger than end port")
        ports = list(range(args.start, args.end + 1))
    return ports


def main():
    parser = argparse.ArgumentParser(description="Simple TCP port scanner (authorized targets only)")
    parser.add_argument("host", help="target: localhost, 127.0.0.1, or scanme.nmap.org")
    parser.add_argument("-p", "--ports", type=parse_port_list, help="comma separated ports, for example 22,80,443")
    parser.add_argument("-s", "--start", type=parse_port, default=1, help="first port of a range (default 1)")
    parser.add_argument("-e", "--end", type=parse_port, default=1024, help="last port of a range (default 1024)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="seconds to wait between ports")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="seconds to wait for each port")
    parser.add_argument("--open-only", action="store_true", help="only print open ports")
    args = parser.parse_args()

    # Safety check: never scan anything that is not on the allowed list.
    host = args.host.lower()
    if host not in ALLOWED_HOSTS:
        print(f"Refusing to scan '{args.host}'. Only localhost, 127.0.0.1, and scanme.nmap.org are authorized.")
        sys.exit(2)

    if args.delay < 0 or args.timeout <= 0:
        print("Error: delay cannot be negative and timeout must be greater than zero.")
        sys.exit(2)

    try:
        ports = build_port_list(args)
    except ValueError as error:
        print(f"Error: {error}")
        sys.exit(2)

    # Keep scans of the remote test server small and polite.
    if host not in LOCAL_HOSTS and len(ports) > MAX_REMOTE_PORTS:
        print(f"Error: scans of {args.host} are limited to {MAX_REMOTE_PORTS} ports. Choose a smaller range.")
        sys.exit(2)

    # Turn the host name into an IP address; this fails if the name cannot be found.
    try:
        ip = socket.gethostbyname(args.host)
    except socket.gaierror:
        print(f"Error: could not resolve '{args.host}'. Check your network connection and the host name.")
        sys.exit(1)

    print(f"[{now()}] Starting scan of {args.host} ({ip}), {len(ports)} port(s)")
    open_ports, closed_ports, filtered_ports = [], [], []
    started = time.time()

    try:
        for index, port in enumerate(ports, start=1):
            try:
                status = probe_port(ip, port, args.timeout)
            except OSError as error:
                print(f"Error: {args.host} is unreachable ({error.strerror}). Stopping the scan.")
                sys.exit(1)

            if status == "open":
                open_ports.append(port)
                print(f"[{now()}] Port {port}/tcp OPEN ({service_name(port)})")
            elif status == "closed":
                closed_ports.append(port)
                if not args.open_only:
                    print(f"[{now()}] Port {port}/tcp CLOSED")
            else:
                filtered_ports.append(port)
                if not args.open_only:
                    print(f"[{now()}] Port {port}/tcp FILTERED (no response)")

            # Progress indicator for long scans.
            if len(ports) > 200 and index % 100 == 0:
                print(f"[{now()}] Progress: {index}/{len(ports)} ports checked")

            time.sleep(args.delay)  # pause so the scan is not aggressive
    except KeyboardInterrupt:
        print("\nScan stopped by user (Ctrl+C).")

    elapsed = time.time() - started
    print("-" * 60)
    print(f"[{now()}] Scan finished in {elapsed:.2f} seconds")
    print(f"Open: {len(open_ports)} {open_ports}")
    print(f"Closed: {len(closed_ports)}")
    print(f"Filtered: {len(filtered_ports)}")


if __name__ == "__main__":
    main()
