"""
Student Management REST API
============================

A Flask + SQLite REST API for managing students, courses, and enrollments.

- Raw SQL only (no ORM) via the sqlite3 module.
- Students <-> Courses is a many-to-many relationship modeled through the
  "enrollments" join table, enforced with foreign key constraints.
- Consistent JSON error responses and correct HTTP status codes:
    200 OK, 201 Created, 204 No Content,
    400 Bad Request (validation errors),
    404 Not Found (missing resource),
    409 Conflict (duplicate / constraint violation).
"""

import re
import sqlite3

from flask import Flask, g, jsonify, request

import db

app = Flask(__name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --------------------------------------------------------------------------
# Database lifecycle
# --------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = db.get_connection()
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


# --------------------------------------------------------------------------
# Error helpers
# --------------------------------------------------------------------------

def error_response(message, status_code):
    return jsonify({"error": message}), status_code


@app.errorhandler(404)
def not_found(e):
    return error_response("Resource not found", 404)


@app.errorhandler(405)
def method_not_allowed(e):
    return error_response("Method not allowed", 405)


@app.errorhandler(500)
def server_error(e):
    return error_response("Internal server error", 500)


# --------------------------------------------------------------------------
# Validation helpers
# --------------------------------------------------------------------------

def require_fields(data, fields):
    """Return an error string if data is missing any required fields."""
    if not isinstance(data, dict):
        return "Request body must be a JSON object"
    missing = [f for f in fields if f not in data or data[f] in (None, "")]
    if missing:
        return f"Missing required field(s): {', '.join(missing)}"
    return None


def validate_student_payload(data, partial=False):
    required = [] if partial else ["name", "email", "age"]
    err = require_fields(data, required)
    if err:
        return err

    if "name" in data and not isinstance(data["name"], str):
        return "'name' must be a string"
    if "name" in data and len(data["name"].strip()) == 0:
        return "'name' must not be empty"

    if "email" in data:
        if not isinstance(data["email"], str) or not EMAIL_RE.match(data["email"]):
            return "'email' must be a valid email address"

    if "age" in data:
        if not isinstance(data["age"], int) or isinstance(data["age"], bool):
            return "'age' must be an integer"
        if data["age"] <= 0 or data["age"] > 150:
            return "'age' must be a realistic positive integer"

    return None


def validate_course_payload(data, partial=False):
    required = [] if partial else ["title", "code", "credits"]
    err = require_fields(data, required)
    if err:
        return err

    if "title" in data and not isinstance(data["title"], str):
        return "'title' must be a string"
    if "title" in data and len(data["title"].strip()) == 0:
        return "'title' must not be empty"

    if "code" in data:
        if not isinstance(data["code"], str) or len(data["code"].strip()) == 0:
            return "'code' must be a non-empty string"

    if "credits" in data:
        if not isinstance(data["credits"], int) or isinstance(data["credits"], bool):
            return "'credits' must be an integer"
        if data["credits"] <= 0 or data["credits"] > 20:
            return "'credits' must be a positive integer (1-20)"

    return None


def get_json_body():
    """Parse JSON body, returning None (not raising) on bad input so callers
    can respond with a clean 400 instead of Flask's default error page."""
    try:
        return request.get_json(force=False, silent=True)
    except Exception:
        return None


# --------------------------------------------------------------------------
# Students
# --------------------------------------------------------------------------

@app.route("/students", methods=["POST"])
def create_student():
    data = get_json_body()
    err = validate_student_payload(data)
    if err:
        return error_response(err, 400)

    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO students (name, email, age) VALUES (?, ?, ?)",
            (data["name"].strip(), data["email"].strip().lower(), data["age"]),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return error_response("A student with this email already exists", 409)

    row = conn.execute(
        "SELECT * FROM students WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return jsonify(db.row_to_dict(row)), 201


@app.route("/students", methods=["GET"])
def list_students():
    conn = get_db()
    rows = conn.execute("SELECT * FROM students ORDER BY id").fetchall()
    return jsonify([db.row_to_dict(r) for r in rows]), 200


@app.route("/students/<int:student_id>", methods=["GET"])
def get_student(student_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    if row is None:
        return error_response(f"Student {student_id} not found", 404)
    return jsonify(db.row_to_dict(row)), 200


@app.route("/students/<int:student_id>", methods=["PUT"])
def update_student(student_id):
    data = get_json_body()
    err = validate_student_payload(data, partial=True)
    if err:
        return error_response(err, 400)

    conn = get_db()
    existing = conn.execute(
        "SELECT * FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    if existing is None:
        return error_response(f"Student {student_id} not found", 404)

    name = data.get("name", existing["name"])
    email = data.get("email", existing["email"])
    age = data.get("age", existing["age"])

    try:
        conn.execute(
            "UPDATE students SET name = ?, email = ?, age = ? WHERE id = ?",
            (name.strip() if isinstance(name, str) else name,
             email.strip().lower() if isinstance(email, str) else email,
             age, student_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return error_response("A student with this email already exists", 409)

    row = conn.execute(
        "SELECT * FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    return jsonify(db.row_to_dict(row)), 200


@app.route("/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    if existing is None:
        return error_response(f"Student {student_id} not found", 404)

    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    return "", 204


@app.route("/students/<int:student_id>/courses", methods=["GET"])
def get_student_courses(student_id):
    """List all courses a given student is enrolled in (join across the
    enrollments table)."""
    conn = get_db()
    student = conn.execute(
        "SELECT id FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    if student is None:
        return error_response(f"Student {student_id} not found", 404)

    rows = conn.execute(
        """
        SELECT c.id, c.title, c.code, c.credits, e.enrolled_at
        FROM courses c
        JOIN enrollments e ON e.course_id = c.id
        WHERE e.student_id = ?
        ORDER BY c.id
        """,
        (student_id,),
    ).fetchall()
    return jsonify([db.row_to_dict(r) for r in rows]), 200


# --------------------------------------------------------------------------
# Courses
# --------------------------------------------------------------------------

@app.route("/courses", methods=["POST"])
def create_course():
    data = get_json_body()
    err = validate_course_payload(data)
    if err:
        return error_response(err, 400)

    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO courses (title, code, credits) VALUES (?, ?, ?)",
            (data["title"].strip(), data["code"].strip().upper(), data["credits"]),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return error_response("A course with this code already exists", 409)

    row = conn.execute(
        "SELECT * FROM courses WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return jsonify(db.row_to_dict(row)), 201


@app.route("/courses", methods=["GET"])
def list_courses():
    conn = get_db()
    rows = conn.execute("SELECT * FROM courses ORDER BY id").fetchall()
    return jsonify([db.row_to_dict(r) for r in rows]), 200


@app.route("/courses/<int:course_id>", methods=["GET"])
def get_course(course_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM courses WHERE id = ?", (course_id,)
    ).fetchone()
    if row is None:
        return error_response(f"Course {course_id} not found", 404)
    return jsonify(db.row_to_dict(row)), 200


@app.route("/courses/<int:course_id>", methods=["PUT"])
def update_course(course_id):
    data = get_json_body()
    err = validate_course_payload(data, partial=True)
    if err:
        return error_response(err, 400)

    conn = get_db()
    existing = conn.execute(
        "SELECT * FROM courses WHERE id = ?", (course_id,)
    ).fetchone()
    if existing is None:
        return error_response(f"Course {course_id} not found", 404)

    title = data.get("title", existing["title"])
    code = data.get("code", existing["code"])
    credits = data.get("credits", existing["credits"])

    try:
        conn.execute(
            "UPDATE courses SET title = ?, code = ?, credits = ? WHERE id = ?",
            (title.strip() if isinstance(title, str) else title,
             code.strip().upper() if isinstance(code, str) else code,
             credits, course_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return error_response("A course with this code already exists", 409)

    row = conn.execute(
        "SELECT * FROM courses WHERE id = ?", (course_id,)
    ).fetchone()
    return jsonify(db.row_to_dict(row)), 200


@app.route("/courses/<int:course_id>", methods=["DELETE"])
def delete_course(course_id):
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM courses WHERE id = ?", (course_id,)
    ).fetchone()
    if existing is None:
        return error_response(f"Course {course_id} not found", 404)

    conn.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    conn.commit()
    return "", 204


@app.route("/courses/<int:course_id>/students", methods=["GET"])
def get_course_students(course_id):
    """List all students enrolled in a given course (join across the
    enrollments table)."""
    conn = get_db()
    course = conn.execute(
        "SELECT id FROM courses WHERE id = ?", (course_id,)
    ).fetchone()
    if course is None:
        return error_response(f"Course {course_id} not found", 404)

    rows = conn.execute(
        """
        SELECT s.id, s.name, s.email, s.age, e.enrolled_at
        FROM students s
        JOIN enrollments e ON e.student_id = s.id
        WHERE e.course_id = ?
        ORDER BY s.id
        """,
        (course_id,),
    ).fetchall()
    return jsonify([db.row_to_dict(r) for r in rows]), 200


# --------------------------------------------------------------------------
# Enrollments (the many-to-many join)
# --------------------------------------------------------------------------

@app.route("/enrollments", methods=["POST"])
def create_enrollment():
    data = get_json_body()
    err = require_fields(data, ["student_id", "course_id"])
    if err:
        return error_response(err, 400)

    student_id = data["student_id"]
    course_id = data["course_id"]

    if not isinstance(student_id, int) or isinstance(student_id, bool):
        return error_response("'student_id' must be an integer", 400)
    if not isinstance(course_id, int) or isinstance(course_id, bool):
        return error_response("'course_id' must be an integer", 400)

    conn = get_db()

    student = conn.execute(
        "SELECT id FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    if student is None:
        return error_response(f"Student {student_id} not found", 404)

    course = conn.execute(
        "SELECT id FROM courses WHERE id = ?", (course_id,)
    ).fetchone()
    if course is None:
        return error_response(f"Course {course_id} not found", 404)

    try:
        cur = conn.execute(
            "INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)",
            (student_id, course_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return error_response(
            "This student is already enrolled in this course", 409
        )

    row = conn.execute(
        "SELECT * FROM enrollments WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return jsonify(db.row_to_dict(row)), 201


@app.route("/enrollments", methods=["GET"])
def list_enrollments():
    """List all enrollments with student and course details joined in."""
    conn = get_db()
    rows = conn.execute(
        """
        SELECT
            e.id AS enrollment_id,
            e.enrolled_at,
            s.id AS student_id, s.name AS student_name, s.email AS student_email,
            c.id AS course_id, c.title AS course_title, c.code AS course_code
        FROM enrollments e
        JOIN students s ON s.id = e.student_id
        JOIN courses c ON c.id = e.course_id
        ORDER BY e.id
        """
    ).fetchall()
    return jsonify([db.row_to_dict(r) for r in rows]), 200


@app.route("/enrollments/<int:enrollment_id>", methods=["GET"])
def get_enrollment(enrollment_id):
    conn = get_db()
    row = conn.execute(
        """
        SELECT
            e.id AS enrollment_id,
            e.enrolled_at,
            s.id AS student_id, s.name AS student_name, s.email AS student_email,
            c.id AS course_id, c.title AS course_title, c.code AS course_code
        FROM enrollments e
        JOIN students s ON s.id = e.student_id
        JOIN courses c ON c.id = e.course_id
        WHERE e.id = ?
        """,
        (enrollment_id,),
    ).fetchone()
    if row is None:
        return error_response(f"Enrollment {enrollment_id} not found", 404)
    return jsonify(db.row_to_dict(row)), 200


@app.route("/enrollments/<int:enrollment_id>", methods=["DELETE"])
def delete_enrollment(enrollment_id):
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM enrollments WHERE id = ?", (enrollment_id,)
    ).fetchone()
    if existing is None:
        return error_response(f"Enrollment {enrollment_id} not found", 404)

    conn.execute("DELETE FROM enrollments WHERE id = ?", (enrollment_id,))
    conn.commit()
    return "", 204


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "Student Management REST API",
        "endpoints": {
            "students": ["POST /students", "GET /students",
                          "GET /students/<id>", "PUT /students/<id>",
                          "DELETE /students/<id>", "GET /students/<id>/courses"],
            "courses": ["POST /courses", "GET /courses",
                        "GET /courses/<id>", "PUT /courses/<id>",
                        "DELETE /courses/<id>", "GET /courses/<id>/students"],
            "enrollments": ["POST /enrollments", "GET /enrollments",
                             "GET /enrollments/<id>", "DELETE /enrollments/<id>"],
        },
    }), 200


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True, port=5000)
