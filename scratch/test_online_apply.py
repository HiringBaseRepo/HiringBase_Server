import httpx
import json

def test_online():
    # Production backend url
    url = "https://hiringbase-server.onrender.com/api/v1/applications/public/apply"
    
    job_id = 698
    email = "john.valid.test@test.com"
    full_name = "John Test"
    phone = "081234567890"
    
    answers = {
        "education": "Bachelor's Degree in Computer Science",
        "work_experience": "I have 5 years of experience as a software engineer specializing in python, flutter, node.js, and DWH systems.",
        "skills": "Python, Flutter, Node.js, DWH, JavaScript, FastAPI",
        "experience": "5 years"
    }
    
    data = {
        "job_id": str(job_id),
        "email": email,
        "full_name": full_name,
        "phone": phone,
        "answers_json": json.dumps(answers)
    }
    
    # Portfolio file
    files = {
        "file_portfolio": ("portfolio.pdf", b"%PDF-1.4 mock cv pdf content for John Test", "application/pdf")
    }
    
    print(f"Sending POST to {url}...")
    try:
        response = httpx.post(url, data=data, files=files, timeout=60.0)
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_online()
