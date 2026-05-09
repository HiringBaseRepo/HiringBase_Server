import socket
import sys

host = "ep-bitter-forest-aoc1v14g-pooler.c-2.ap-southeast-1.aws.neon.tech"
try:
    print(f"Resolving {host}...")
    addr = socket.gethostbyname(host)
    print(f"Resolved to {addr}")
except socket.gaierror as e:
    print(f"Resolution failed: {e}")
    sys.exit(1)
