import os
import datetime
import sqlite3
from flask import Flask, request, jsonify, redirect, url_for, render_template
from werkzeug.utils import secure_filename
from docx import Document
import random


app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["DATABASE"] = "database.db"

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# db
def init_db():
    conn = sqlite3.connect(app.config["DATABASE"])
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_id INTEGER,
        text TEXT,
        FOREIGN KEY(test_id) REFERENCES tests(id)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS variants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER,
        text TEXT,
        is_correct INTEGER DEFAULT 0,
        FOREIGN KEY(question_id) REFERENCES questions(id)
    )
    """)

    conn.commit()
    conn.close()

# parse docx
def parse_docx(path):
    doc = Document(path)
    questions = []
    current_question = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if text.startswith("<question>"):
            current_question = {
                "question": text.replace("<question>", "").strip(),
                "variants": []
            }
            questions.append(current_question)
        elif text.startswith("<variant>") and current_question:
            current_question["variants"].append(text.replace("<variant>", "").strip())

    return questions

# route
@app.route("/", methods=["GET"])
def index():
    conn = sqlite3.connect(app.config["DATABASE"])
    c = conn.cursor()
    c.execute("SELECT id, name, created_at FROM tests")
    tests = c.fetchall()
    conn.close()
    return render_template("index.html", tests=tests)

@app.route("/add_test", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        test_name = request.form.get("test_name")
        file = request.files.get("file")

        if not file or not file.filename.endswith(".docx"):
            return "Только .docx файлы", 400
        if not test_name:
            return "Название теста обязательно", 400

        filename = secure_filename(file.filename)
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(path)

        parsed = parse_docx(path)

        conn = sqlite3.connect(app.config["DATABASE"])
        c = conn.cursor()


        c.execute("INSERT INTO tests (name, created_at) VALUES (?, ?)", 
                  (test_name, datetime.datetime.now().isoformat()))
        test_id = c.lastrowid  

        
        for q in parsed:
            c.execute("INSERT INTO questions (test_id, text) VALUES (?, ?)", 
                      (test_id, q["question"]))
            question_id = c.lastrowid
            for idx, v in enumerate(q["variants"]):
                is_correct = 1 if idx == 0 else 0
                c.execute("INSERT INTO variants (question_id, text, is_correct) VALUES (?, ?, ?)", 
                          (question_id, v, is_correct))

        conn.commit()
        conn.close()  

        return redirect(url_for("index"))

    return render_template("upload.html")




@app.route("/tests", methods=["GET"])
def list_tests():
    conn = sqlite3.connect(app.config["DATABASE"])
    c = conn.cursor()
    c.execute("SELECT id, name, created_at FROM tests")
    tests = c.fetchall()
    conn.close()
    return jsonify([
        {"id": row[0], "name": row[1], "created_at": row[2]} for row in tests
    ])

@app.route("/test/<int:test_id>")
def view_test(test_id):
    conn = sqlite3.connect(app.config["DATABASE"])
    c = conn.cursor()

    c.execute("SELECT text, id FROM questions WHERE test_id=?", (test_id,))
    questions = c.fetchall()
    result = []

    for q_text, q_id in questions:
        c.execute("SELECT text FROM variants WHERE question_id=?", (q_id,))
        variants = [row[0] for row in c.fetchall()]
        result.append({"question": q_text, "variants": variants})

    conn.close()
    return jsonify(result)



@app.route("/tests/html")
def list_tests_html():
    conn = sqlite3.connect(app.config["DATABASE"])
    c = conn.cursor()
    c.execute("SELECT id, name FROM tests ORDER BY id DESC")
    tests = c.fetchall()
    conn.close()
    return render_template("tests.html", tests=tests)

@app.route("/test/<int:test_id>/html", methods=["GET"])
def take_test_html(test_id):
    conn = sqlite3.connect(app.config["DATABASE"])
    c = conn.cursor()

    c.execute("SELECT name FROM tests WHERE id=?", (test_id,))
    test_name = c.fetchone()[0] 

    c.execute("SELECT text, id FROM questions WHERE test_id=?", (test_id,))
    q_raw = c.fetchall()
    questions = []

    for q_text, q_id in q_raw:
        c.execute("SELECT text, is_correct FROM variants WHERE question_id=?", (q_id,))
        variants = [{"text": row[0], "is_correct": bool(row[1])} for row in c.fetchall()]
        random.shuffle(variants)
        questions.append({
            "question_id": q_id,
            "question": q_text,
            "variants": variants
        })

    random.shuffle(questions)

    conn.close()
    return render_template("take_test.html", test_id=test_id, test_name=test_name, questions=questions)




if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
