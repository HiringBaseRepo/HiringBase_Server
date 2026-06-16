import urllib.request
import json
import uuid
from datetime import datetime

# BASE_URL = "http://localhost:8000/api/v1" # Local test server
BASE_URL = "https://hiringbase-server.onrender.com/api/v1" # Production test server

def send_request(method, path, headers=None, data=None, is_json=True):
    if headers is None:
        headers = {}
    
    url = f"{BASE_URL}{path}"
    
    if is_json and data is not None:
        headers["Content-Type"] = "application/json"
        req_data = json.dumps(data).encode("utf-8")
    elif isinstance(data, bytes):
        req_data = data
    else:
        req_data = data
        
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            res_data = response.read().decode("utf-8")
            return response.status, json.loads(res_data)
    except urllib.error.HTTPError as e:
        err_data = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_data)
        except:
            return e.code, {"error": err_data}
    except Exception as e:
        return 0, {"error": str(e)}

def encode_multipart_formdata(fields, files):
    boundary = uuid.uuid4().hex
    body = []
    
    for key, value in fields.items():
        body.append(f"--{boundary}".encode('utf-8'))
        body.append(f'Content-Disposition: form-data; name="{key}"'.encode('utf-8'))
        body.append(b'')
        body.append(str(value).encode('utf-8'))
        
    for key, (filename, content_type, file_bytes) in files.items():
        body.append(f"--{boundary}".encode('utf-8'))
        body.append(f'Content-Disposition: form-data; name="{key}"; filename="{filename}"'.encode('utf-8'))
        body.append(f'Content-Type: {content_type}'.encode('utf-8'))
        body.append(b'')
        body.append(file_bytes)
        
    body.append(f"--{boundary}--".encode('utf-8'))
    body.append(b'')
    
    content = b'\r\n'.join(body)
    headers = {
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'Content-Length': str(len(content))
    }
    return content, headers

def run_test():
    print("=" * 60)
    print("     HIRINGBASE END-TO-END AUTOMATED INTEGRATION TEST      ")
    print("=" * 60)
    
    unique_suffix = uuid.uuid4().hex[:6]
    hr_email = f"recruiter_{unique_suffix}@hiringbase.com"
    hr_password = "SecurePassword123!"
    hr_name = f"Test HR {unique_suffix.upper()}"
    company_name = f"Global Tech {unique_suffix.upper()}"
    
    # 1. Register HR
    print("\n[STEP 1] Registering HR & Company...")
    reg_payload = {
        "email": hr_email,
        "password": hr_password,
        "full_name": hr_name,
        "company_name": company_name
    }
    status, res = send_request("POST", "/auth/register/hr", data=reg_payload)
    print(f"Status: {status}")
    if status != 200 or not res.get("success"):
        print("Registration failed:", res)
        return
    print("Success: Registered HR user & Company!")

    # 2. Login HR
    print("\n[STEP 2] Logging in as HR...")
    login_payload = {
        "email": hr_email,
        "password": hr_password
    }
    status, res = send_request("POST", "/auth/login", data=login_payload)
    print(f"Status: {status}")
    if status != 200 or not res.get("success"):
        print("Login failed:", res)
        return
    token = res["data"]["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    print("Success: Authenticated and retrieved JWT token!")

    # 3. Create Job (Step 1)
    print("\n[STEP 3] Creating new vacancy (Step 1 - Core Info)...")
    job_title = f"Flutter Engineer {unique_suffix.upper()}"
    job_payload = {
        "title": job_title,
        "department": "Engineering",
        "employment_type": "full_time",
        "location": "Jakarta, ID",
        "salary_min": 12000000,
        "salary_max": 18000000,
        "description": "Premium Flutter app development role.",
        "responsibilities": "Write clean code, deploy GetX architecture.",
        "benefits": "Competitive salary, health insurance."
    }
    status, res = send_request("POST", "/jobs/create-step1", headers=auth_headers, data=job_payload)
    print(f"Status: {status}")
    if status != 200 or not res.get("success"):
        print("Job Step 1 failed:", res)
        return
    job_id = res["data"]["job_id"]
    print(f"Success: Vacancy created (ID: {job_id})")

    # 4. Add Job Requirements (Step 2)
    print("\n[STEP 4] Setting requirements (Step 2)...")
    req_payload = {
        "requirements": [
            {"category": "experience", "name": "flutter_years", "value": "2", "is_required": True, "priority": 1},
            {"category": "skills", "name": "state_management", "value": "GetX", "is_required": True, "priority": 1}
        ]
    }
    status, res = send_request("POST", f"/jobs/{job_id}/step2-requirements", headers=auth_headers, data=req_payload)
    print(f"Status: {status}")
    if status != 200 or not res.get("success"):
        print("Job Step 2 failed:", res)
        return
    print("Success: Requirements saved!")

    # 5. Setup Job Custom Form Fields (Step 3)
    print("\n[STEP 5] Configuring custom form fields & documents (Step 3)...")
    form_payload = {
        "fields": [
            {"field_key": "github_portfolio", "field_type": "text", "label": "Link GitHub Portfolio", "is_required": True, "order_index": 0},
            {"field_key": "portfolio", "field_type": "file", "label": "CV & Portfolio PDF", "is_required": True, "order_index": 1}
        ]
    }
    status, res = send_request("POST", f"/jobs/{job_id}/step3-form", headers=auth_headers, data=form_payload)
    print(f"Status: {status}")
    if status != 200 or not res.get("success"):
        print("Job Step 3 failed:", res)
        return
    print("Success: Custom form setup saved!")

    # 6. Publish Job (Step 4)
    print("\n[STEP 6] Publishing vacancy (Step 4)...")
    publish_payload = {
        "mode": "public"
    }
    status, res = send_request("POST", f"/jobs/{job_id}/step4-publish", headers=auth_headers, data=publish_payload)
    print(f"Status: {status}")
    if status != 200 or not res.get("success"):
        print("Job Step 4 failed:", res)
        return
    apply_code = res["data"]["apply_code"]
    print(f"Success: Job published! Apply Code: {apply_code}")

    # 7. Candidate - View Public Vacancy List
    print("\n[STEP 7] Verifying job appears in public list...")
    status, res = send_request("GET", f"/applications/public/jobs?q={apply_code}")
    print(f"Status: {status}")
    if status != 200 or not res.get("success") or not res["data"]["data"]:
        print("Public list check failed:", res)
        return
    print("Success: Job found in public vacancy list!")

    # 8. Candidate - Submit Application
    print("\n[STEP 8] Submitting new candidate application (Multipart File Upload)...")
    app_fields = {
        "job_id": str(job_id),
        "email": f"candidate_{unique_suffix}@example.com",
        "full_name": f"Kandidat {unique_suffix.upper()}",
        "phone": "+628123456789",
        "answers_json": json.dumps({
            "github_portfolio": f"https://github.com/candidate-{unique_suffix}",
            "experience": "3 years Flutter experience",
            "education": "Bachelor of Computer Science"
        })
    }
    dummy_cv = b"%PDF-1.4 mock pdf contents for candidate cv"
    files = {
        "file_portfolio": (f"cv_{unique_suffix}.pdf", "application/pdf", dummy_cv)
    }
    content, headers = encode_multipart_formdata(app_fields, files)
    status, res = send_request("POST", "/applications/public/apply", headers=headers, data=content, is_json=False)
    print(f"Status: {status}")
    if status != 200 or not res.get("success"):
        print("Application submission failed:", res)
        return
    ticket_code = res["data"]["ticket_code"]
    app_id = res["data"]["application_id"]
    print(f"Success: Application submitted! Ticket Code: {ticket_code}")

    # 9. Candidate - Track Ticket Status
    print("\n[STEP 9] Tracking ticket status...")
    status, res = send_request("GET", f"/tickets/track/{ticket_code}")
    print(f"Status: {status}")
    if status != 200 or not res.get("success"):
        print("Tracking failed:", res)
        return
    print(f"Success: Ticket found! Candidate: {res['data']['applicant_name']}, Status: {res['data']['application_status_label']}")

    # 10. HR - Schedule Interview
    print("\n[STEP 10] Scheduling Interview for Candidate...")
    interview_payload = {
        "application_id": app_id,
        "scheduled_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_minutes": 45,
        "location": "Virtual",
        "meeting_link": "https://meet.google.com/abc-defg-hij",
        "interview_type": "video"
    }
    status, res = send_request("POST", "/interviews", headers=auth_headers, data=interview_payload)
    print(f"Status: {status}")
    if status != 200 or not res.get("success"):
        print("Interview scheduling failed:", res)
        return
    print("Success: Interview scheduled!")

    # 11. HR - Get Candidate Ranking
    print("\n[STEP 11] Getting Candidate Ranking for Job...")
    status, res = send_request("GET", f"/ranking/jobs/{job_id}", headers=auth_headers)
    print(f"Status: {status}")
    if status != 200 or not res.get("success"):
        print("Ranking check failed:", res)
        return
    print("Success: Candidate Ranking loaded successfully!")

    # 12. HR - Verify Profile Activity/Audit Logs
    print("\n[STEP 12] Loading Audit Logs...")
    status, res = send_request("GET", "/audit-logs", headers=auth_headers)
    print(f"Status: {status}")
    if status != 200 or not res.get("success"):
        print("Audit logs check failed:", res)
        return
    print("Success: Audit Logs retrieved successfully!")

    print("\n" + "=" * 60)
    print("   CONGRATULATIONS! ALL E2E API INTEGRATION TESTS PASSED!   ")
    print("=" * 60)

if __name__ == "__main__":
    run_test()
