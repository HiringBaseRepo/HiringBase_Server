import http.client
import json

def test():
    conn = http.client.HTTPSConnection("hiringbase-server.onrender.com")
    # Query ticket track
    conn.request("GET", "/api/v1/tickets/track/TKT-2026-37899")
    resp = conn.getresponse()
    print("Status:", resp.status)
    print("Reason:", resp.reason)
    data = resp.read().decode('utf-8')
    print("Response body:")
    try:
        print(json.dumps(json.loads(data), indent=2))
    except:
        print(data)

if __name__ == "__main__":
    test()
