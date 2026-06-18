import urllib.request
import json
import ssl

try:
    print("Requesting Render API...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen("https://hiringbase-server.onrender.com/api/v1/applications/public/jobs/712", timeout=10, context=ctx) as response:
        html = response.read().decode('utf-8')
        print("Success! Response body:")
        print(json.dumps(json.loads(html), indent=2))
except Exception as e:
    print(f"Error: {e}")
