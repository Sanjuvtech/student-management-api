-- Student Management System schema
-- Models a many-to-many relationship between students and courses
-- through the "enrollments" join table.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE,
    age        INTEGER NOT NULL CHECK (age > 0),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS courses (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    code       TEXT NOT NULL UNIQUE,
    credits    INTEGER NOT NULL CHECK (credits > 0),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Join table implementing the many-to-many relationship.
-- A student can enroll in many courses, a course can have many students,
-- but the same student cannot enroll twice in the same course.
CREATE TABLE IF NOT EXISTS enrollments (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id   INTEGER NOT NULL,
    course_id    INTEGER NOT NULL,
    enrolled_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
    FOREIGN KEY (course_id)  REFERENCES courses (id)  ON DELETE CASCADE,
    UNIQUE (student_id, course_id)
);

CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments (student_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_course ON enrollments (course_id);
