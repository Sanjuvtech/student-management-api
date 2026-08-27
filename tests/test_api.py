"""
Test suite for the Student Management REST API.

Run with:
    pytest -v
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db as db_module  # noqa: E402
import app as app_module  # noqa: E402


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    db_module.DB_PATH = path
    db_module.init_db(path)

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as test_client:
        yield test_client

    os.remove(path)


def create_student(client, name="Ada Lovelace", email="ada@example.com", age=28):
    return client.post("/students", json={"name": name, "email": email, "age": age})


def create_course(client, title="Intro to CS", code="CS101", credits=3):
    return client.post("/courses", json={"title": title, "code": code, "credits": credits})


# --------------------------------------------------------------------
# Students
# --------------------------------------------------------------------

def test_create_student_success(client):
    resp = create_student(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["name"] == "Ada Lovelace"
    assert body["email"] == "ada@example.com"


def test_create_student_missing_fields(client):
    resp = client.post("/students", json={"name": "No Email"})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_create_student_invalid_email(client):
    resp = client.post("/students", json={"name": "Bad", "email": "not-an-email", "age": 20})
    assert resp.status_code == 400


def test_create_student_invalid_age(client):
    resp = client.post("/students", json={"name": "Bad", "email": "bad@example.com", "age": -5})
    assert resp.status_code == 400


def test_create_student_duplicate_email_conflict(client):
    create_student(client)
    resp = create_student(client)
    assert resp.status_code == 409


def test_get_student_not_found(client):
    resp = client.get("/students/999")
    assert resp.status_code == 404


def test_list_get_update_delete_student(client):
    created = create_student(client).get_json()
    sid = created["id"]

    resp = client.get("/students")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1

    resp = client.get(f"/students/{sid}")
    assert resp.status_code == 200

    resp = client.put(f"/students/{sid}", json={"age": 30})
    assert resp.status_code == 200
    assert resp.get_json()["age"] == 30

    resp = client.delete(f"/students/{sid}")
    assert resp.status_code == 204

    resp = client.get(f"/students/{sid}")
    assert resp.status_code == 404


# --------------------------------------------------------------------
# Courses
# --------------------------------------------------------------------

def test_create_course_success(client):
    resp = create_course(client)
    assert resp.status_code == 201
    assert resp.get_json()["code"] == "CS101"


def test_create_course_duplicate_code_conflict(client):
    create_course(client)
    resp = create_course(client)
    assert resp.status_code == 409


def test_create_course_invalid_credits(client):
    resp = client.post("/courses", json={"title": "X", "code": "X1", "credits": 0})
    assert resp.status_code == 400


def test_course_not_found(client):
    resp = client.get("/courses/42")
    assert resp.status_code == 404


# --------------------------------------------------------------------
# Enrollments (many-to-many)
# --------------------------------------------------------------------

def test_enroll_student_in_course(client):
    sid = create_student(client).get_json()["id"]
    cid = create_course(client).get_json()["id"]

    resp = client.post("/enrollments", json={"student_id": sid, "course_id": cid})
    assert resp.status_code == 201

    resp = client.get(f"/students/{sid}/courses")
    assert resp.status_code == 200
    courses = resp.get_json()
    assert len(courses) == 1
    assert courses[0]["code"] == "CS101"

    resp = client.get(f"/courses/{cid}/students")
    assert resp.status_code == 200
    students = resp.get_json()
    assert len(students) == 1
    assert students[0]["email"] == "ada@example.com"


def test_enroll_duplicate_conflict(client):
    sid = create_student(client).get_json()["id"]
    cid = create_course(client).get_json()["id"]
    client.post("/enrollments", json={"student_id": sid, "course_id": cid})

    resp = client.post("/enrollments", json={"student_id": sid, "course_id": cid})
    assert resp.status_code == 409


def test_enroll_nonexistent_student_404(client):
    cid = create_course(client).get_json()["id"]
    resp = client.post("/enrollments", json={"student_id": 999, "course_id": cid})
    assert resp.status_code == 404


def test_enroll_nonexistent_course_404(client):
    sid = create_student(client).get_json()["id"]
    resp = client.post("/enrollments", json={"student_id": sid, "course_id": 999})
    assert resp.status_code == 404


def test_delete_enrollment(client):
    sid = create_student(client).get_json()["id"]
    cid = create_course(client).get_json()["id"]
    eid = client.post(
        "/enrollments", json={"student_id": sid, "course_id": cid}
    ).get_json()["id"]

    resp = client.delete(f"/enrollments/{eid}")
    assert resp.status_code == 204

    resp = client.get(f"/students/{sid}/courses")
    assert resp.get_json() == []


def test_list_enrollments_joined_fields(client):
    sid = create_student(client).get_json()["id"]
    cid = create_course(client).get_json()["id"]
    client.post("/enrollments", json={"student_id": sid, "course_id": cid})

    resp = client.get("/enrollments")
    assert resp.status_code == 200
    row = resp.get_json()[0]
    assert row["student_name"] == "Ada Lovelace"
    assert row["course_code"] == "CS101"
