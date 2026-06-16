import httpx
import json

def test_apply():
    # Use localhost:8000
    url = "http://127.0.0.1:8000/api/v1/applications/public/apply"
    
    # We will submit for job 698
    job_id = 698
    email = "applicant2@test.com"
    full_name = "John Test"
    phone = "081234567890"
    answers = {
        "linkedin": "https://linkedin.com/in/johntest",
        "experience": "3 years of dev",
        "skills": "Python, Fastapi"
    }
    
    data = {
        "job_id": str(job_id),
        "email": email,
        "full_name": full_name,
        "phone": phone,
        "answers_json": json.dumps(answers)
    }
    
    # Let's create a mock file in memory
    files = {
        "file_portfolio": ("cv.pdf", b"%PDF-1.4 mock cv pdf content", "application/pdf")
    }
    
    print(f"Sending POST to {url}...")
    try:
        response = httpx.post(url, data=data, files=files, timeout=30.0)
        print(f"Status Code: {response.status_code}")
        print("Response headers:", response.headers)
        try:
            print("Response JSON:")
            print(json.dumps(response.json(), indent=2))
        except Exception:
            print("Response Text:", response.text)
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_apply()
