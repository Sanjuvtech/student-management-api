# Student Management REST API

A RESTful API built with **Flask** and **SQLite** for managing students, courses,
and enrollments. Designed to demonstrate raw SQL usage, many-to-many relational
modeling, input validation, and correct HTTP status code semantics — no ORM.

## Features

- Full CRUD for **students** and **courses**
- **Many-to-many** relationship between students and courses via an
  `enrollments` join table
- Raw SQL throughout (`sqlite3` module) — explicit `JOIN`s, `FOREIGN KEY`
  constraints, and `UNIQUE` constraints (e.g. to prevent duplicate enrollments)
- Input validation on every write endpoint (types, required fields, ranges,
  email format)
- Correct HTTP status codes:
  - `200 OK` — successful reads/updates
  - `201 Created` — resource created
  - `204 No Content` — successful delete
  - `400 Bad Request` — validation failure
  - `404 Not Found` — resource does not exist
  - `409 Conflict` — duplicate resource / constraint violation
- 15 endpoints across 3 resources

## Tech Stack

- Python 3
- Flask
- SQLite3 (standard library, raw SQL — no ORM)
- pytest (tests)

## Project Structure

```
student_management_api/
├── app.py               # Flask app & all route handlers
├── db.py                # SQLite connection helper
├── schema.sql            # Table definitions (students, courses, enrollments)
├── requirements.txt
├── tests/
│   └── test_api.py       # pytest test suite
└── README.md
```

## Setup

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd student_management_api

# 2. Create a virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app (creates student_management.db automatically)
python app.py
```

The API will be available at `http://127.0.0.1:5000`.

## Data Model

```
students                courses
---------               --------
id (PK)                 id (PK)
name                     title
email (unique)           code (unique)
age                      credits
created_at               created_at

            enrollments
            -----------
            id (PK)
            student_id (FK -> students.id)
            course_id  (FK -> courses.id)
            enrolled_at
            UNIQUE(student_id, course_id)
```

A student can enroll in many courses, and a course can have many students —
the `enrollments` table is the join table that models this many-to-many
relationship, with foreign keys and a composite unique constraint to prevent
duplicate enrollments.

## API Endpoints

### Students

| Method | Endpoint                     | Description                          |
|--------|-------------------------------|---------------------------------------|
| POST   | `/students`                   | Create a student                      |
| GET    | `/students`                    | List all students                     |
| GET    | `/students/<id>`               | Get a single student                  |
| PUT    | `/students/<id>`               | Update a student                      |
| DELETE | `/students/<id>`               | Delete a student                      |
| GET    | `/students/<id>/courses`       | List courses a student is enrolled in |

### Courses

| Method | Endpoint                     | Description                          |
|--------|-------------------------------|---------------------------------------|
| POST   | `/courses`                    | Create a course                       |
| GET    | `/courses`                     | List all courses                      |
| GET    | `/courses/<id>`                 | Get a single course                   |
| PUT    | `/courses/<id>`                 | Update a course                       |
| DELETE | `/courses/<id>`                 | Delete a course                       |
| GET    | `/courses/<id>/students`        | List students enrolled in a course    |

### Enrollments

| Method | Endpoint                     | Description                          |
|--------|-------------------------------|---------------------------------------|
| POST   | `/enrollments`                 | Enroll a student in a course          |
| GET    | `/enrollments`                  | List all enrollments (joined data)    |
| GET    | `/enrollments/<id>`              | Get a single enrollment               |
| DELETE | `/enrollments/<id>`              | Remove an enrollment                  |

## Example Requests

**Create a student**
```bash
curl -X POST http://127.0.0.1:5000/students \
  -H "Content-Type: application/json" \
  -d '{"name": "Ada Lovelace", "email": "ada@example.com", "age": 28}'
```

**Create a course**
```bash
curl -X POST http://127.0.0.1:5000/courses \
  -H "Content-Type: application/json" \
  -d '{"title": "Intro to Computer Science", "code": "CS101", "credits": 3}'
```

**Enroll a student in a course**
```bash
curl -X POST http://127.0.0.1:5000/enrollments \
  -H "Content-Type: application/json" \
  -d '{"student_id": 1, "course_id": 1}'
```

**List a student's courses**
```bash
curl http://127.0.0.1:5000/students/1/courses
```

## Error Response Format

All errors return a JSON body of the form:

```json
{ "error": "descriptive message" }
```

Examples:
- Missing required field → `400` with `{"error": "Missing required field(s): email"}`
- Duplicate email/course code/enrollment → `409` with a conflict message
- Unknown student/course/enrollment id → `404` with a not-found message

## Running Tests

```bash
pytest -v
```

The test suite spins up a temporary SQLite database per test, so it never
touches your development database, and covers success paths, validation
failures (400), missing resources (404), and constraint violations (409).

## License

MIT
