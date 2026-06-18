import httpx
import json

def test_apply_valid():
    """
    Script ini menunjukkan payload dan data valid yang harus dikirim ke server
    agar pelamar TIDAK di-reject oleh screening AI untuk Lowongan Pekerjaan ID 698 (Software Engineering).
    """
    
    # URL Endpoint Apply Public
    url = "http://127.0.0.1:8000/api/v1/applications/public/apply"
    
    # 1. FORM DATA (Data Pelamar)
    # PENTING: Nama Lengkap pelamar harus SAMA PERSIS dengan nama yang tertera di dalam dokumen yang diunggah.
    full_name = "John Test" 
    email = "johntest@test.com"
    phone = "081234567890"
    job_id = 698
    
    # 2. ANSWERS JSON
    # PENTING: Untuk meloloskan kriteria kualifikasi pekerjaan (Job ID 698),
    # Anda harus memasukkan jawaban yang memenuhi syarat:
    # - Skill wajib: python, flutter, node.js, DWH
    # - Minimal Pengalaman: 3-5 Years (contoh: 5 years)
    # - Minimal Pendidikan: Bachelor's
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
    
    # 3. DOKUMEN (MULTIPART FILES)
    # - Karena Job 698 tidak memiliki Knockout Rule dokumen wajib (KTP, Ijazah, SKCK), 
    #   cara paling aman untuk menghindari penolakan adalah CUKUP mengunggah portfolio (CV/Resume).
    # - Jika Anda hanya mengunggah file_portfolio, sistem tidak akan memicu pengecekan nama di dokumen KTP/Ijazah, 
    #   sehingga risiko reject otomatis akibat salah baca OCR/LLM menjadi 0%.
    files = {
        "file_portfolio": ("portfolio.pdf", b"%PDF-1.4 mock cv pdf content for John Test", "application/pdf")
    }
    
    # Catatan: Jika Anda MEMANG HARUS mengunggah KTP, Ijazah, atau SKCK, gunakan field name berikut:
    # - file_identity_card (untuk KTP)
    # - file_degree (untuk Ijazah)
    # - file_criminal_record (untuk SKCK)
    # PENTING: File PDF/Gambar yang diunggah di atas harus berupa dokumen asli/valid yang di dalamnya
    # tertulis nama yang cocok dengan form_data["full_name"] (yaitu "John Test").
    
    print(f"Mengirimkan POST ke {url}...")
    try:
        response = httpx.post(url, data=data, files=files, timeout=30.0)
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Gagal melakukan request (pastikan server FastAPI sudah berjalan di port 8000): {e}")

if __name__ == "__main__":
    test_apply_valid()
