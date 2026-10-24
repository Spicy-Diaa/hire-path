from flask import Flask, request, jsonify, render_template_string
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os

app = Flask(__name__)

# تحميل الموديل مرة واحدة أول ما السيرفر يشتغل عشان السرعة
print("Loading AI Model...")
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
print("Model Loaded Successfully!")

# قائمة الوظائف (نفس اللي عندك)
jobs = [
    {"work": "Front-End Developer", "requirements": "HTML, CSS, JavaScript, React, Web Performance"},
    {"work": "Python Back-End Developer", "requirements": "Python, Django, Flask, SQL, REST APIs"},
    {"work": "Data Analyst", "requirements": "Python, Pandas, SQL, Data Visualization, Excel"},
    {"work": "Mobile App Developer", "requirements": "Flutter, Dart, Android, iOS, Firebase, REST APIs"},
    {"work": "DevOps Engineer", "requirements": "Docker, Kubernetes, Linux, CI/CD, AWS, Git"},
    {"work": "Machine Learning Engineer", "requirements": "Python, TensorFlow, PyTorch, Machine Learning, Deep Learning, NLP"},
    {"work": "UI/UX Designer", "requirements": "Figma, User Research, Wireframing, Prototyping, Adobe XD"},
    {"work": "Cybersecurity Analyst", "requirements": "Network Security, Penetration Testing, Linux, Firewalls, SIEM"},
    {"work": "QA Engineer", "requirements": "Manual Testing, Selenium, Test Cases, Bug Tracking, Automation"},
    {"work": "Database Administrator", "requirements": "SQL, MySQL, PostgreSQL, Backup, Performance Tuning"},
    {"work": "Full-Stack Developer", "requirements": "HTML, CSS, JavaScript, React, Node.js, MongoDB, SQL"},
]

skill_priority = {
    "html": 10, "css": 9, "javascript": 10, "react": 9,
    "python": 10, "sql": 9, "flask": 8, "django": 8,
    "rest apis": 8, "git": 8, "docker": 8, "linux": 7,
    "node.js": 8, "mongodb": 7, "pandas": 8,
    "machine learning": 10, "tensorflow": 8, "pytorch": 8,
    "web performance": 4, "ci/cd": 6, "aws": 7,
}
def analyze_ats_and_gaps(student_text, job_requirements):
    job_skills = [skill.strip().lower() for skill in job_requirements.split(",")]
    student_text_lower = student_text.lower()

    matched_skills = [s for s in job_skills if s in student_text_lower]
    missing_skills = [s for s in job_skills if s not in student_text_lower]

    match_score = (len(matched_skills) / len(job_skills)) * 100 if job_skills else 0
    status = "ممتاز (اجتاز الفحص)" if match_score >= 70 else "يحتاج تحسين (خطر الرفض الآلي)"

    return matched_skills, missing_skills, status

def generate_career_roadmap(job_title, missing_skills):
    if not missing_skills:
        return ["جاهز للتقديم مباشرة ✅"]

    sorted_skills = sorted(missing_skills, key=lambda s: skill_priority.get(s, 5), reverse=True)

    steps = []
    for i, skill in enumerate(sorted_skills, start=1):
        steps.append(f"{i}. تعلّم {skill} وطبّقه في مشروع صغير")
    steps.append(f"{len(steps) + 1}. أضف المهارات والمشروع في الـ CV وقدّم على وظيفة {job_title}")
    return steps
    

@app.route('/analyze-cv', methods=['POST'])
def analyze_cv():
    if 'cv_file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['cv_file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # قراءة الـ PDF مباشرة من الـ Request
        reader = PdfReader(file)
        student_skills = ""
        for page in reader.pages:
            student_skills += page.extract_text()

        # تحويل نص الـ CV لأرقام
        student_vec = model.encode([student_skills])

        results = []
        for job in jobs:
            job_vec = model.encode([job["requirements"]])
            score = cosine_similarity(student_vec, job_vec)[0][0]
            ai_similarity = round(float(score) * 100, 2)

            matched, missing, ats_status = analyze_ats_and_gaps(student_skills, job["requirements"])
            total_skills = len(matched) + len(missing)
            skills_match = round(len(matched) / total_skills * 100, 1) if total_skills else 0
            roadmap = generate_career_roadmap(job["work"], missing)

            results.append({
                "job_title": job["work"],
                "match_percentage": f"{skills_match:.1f}%",
                "ai_similarity": f"{ai_similarity:.1f}%",
                "matched_skills": ", ".join(matched) if matched else "لا يوجد",
                "ats_status": ats_status,
                "missing_skills": ", ".join(missing) if missing else "لا يوجد",
                "roadmap": roadmap
            })

        # ترتيب النتائج: مطابقة المهارات أولاً ثم تشابه الموديل
        results = sorted(
            results,
            key=lambda x: (float(x['match_percentage'].replace('%', '')),
                           float(x['ai_similarity'].replace('%', ''))),
            reverse=True
        )
        return jsonify({"status": "success", "results": results})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


HOME_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>Hire Path</title>
<style>
  body { font-family: Arial, sans-serif; max-width: 800px; margin: 30px auto; padding: 0 15px; }
  button { padding: 10px 20px; cursor: pointer; }
  .card { border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin: 10px 0; }
  .pct { font-weight: bold; color: #1a73e8; }
</style>
</head>
<body>
  <h2>Hire Path - تحليل الـ CV</h2>
  <input type="file" id="cv" accept=".pdf">
  <button onclick="analyze()">حلّل الـ CV</button>
  <p id="status"></p>
  <div id="out"></div>

  <script>
    async function analyze() {
      const f = document.getElementById('cv').files[0];
      if (!f) { alert('اختار ملف PDF الأول'); return; }
      document.getElementById('status').innerText = 'جاري التحليل...';
      const fd = new FormData();
      fd.append('cv_file', f);
      const res = await fetch('/analyze-cv', { method: 'POST', body: fd });
      const data = await res.json();
      document.getElementById('status').innerText = '';
      if (data.error) { document.getElementById('out').innerText = data.error; return; }
      document.getElementById('out').innerHTML = data.results.map(r =>
        '<div class="card"><b>' + r.job_title + '</b> - <span class="pct">' + r.match_percentage + '</span><br>' +
        r.ats_status + '<br><b>المهارات الناقصة:</b> ' + r.missing_skills +
        '<br><b>الخطة:</b><br>' + r.roadmap.join('<br>') + '</div>'
      ).join('');
    }
  </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HOME_PAGE)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)