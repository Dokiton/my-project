# Деректер моделі (6-сабақ)

## Кестелер
- **users:** id, email, full_name, role, created_at
- **courses:** id, title, description, teacher_id, created_at
- **enrollments:** id, course_id, student_id, enrolled_at
- **assignments:** id, title, description, deadline, course_id, created_at
- **submissions:** id, code, file_name, status, grade, feedback, assignment_id, student_id, submitted_at, graded_at
- **ai_hints:** id, prompt, response, assignment_id, user_id, created_at

---

## Байланыстар
- **users 1 — көп courses:** бір оқытушы (`teacher`) көптеген курстарды басқарады (`teacher_id`)
- **users 1 — көп enrollments:** бір студент (`student`) көптеген курстарға жазылады (`student_id`)
- **courses 1 — көп enrollments:** бір курста көптеген студенттер оқиды (`course_id`)
- **courses 1 — көп assignments:** бір курс көптеген тапсырмалардан тұрады (`course_id`)
- **assignments 1 — көп submissions:** бір тапсырмаға көптеген студенттер өз шешімдерін жібереді (`assignment_id`)
- **users 1 — көп submissions:** бір студент көптеген тапсырма шешімдерін жүктейді (`student_id`)
- **users 1 — көп ai_hints:** бір пайдаланушы (студент немесе оқытушы) AI көмекшісіне көп сұраныс жасайды (`user_id`)
- **assignments 1 — көп ai_hints:** бір тапсырма бойынша бірнеше AI кеңестері немесе сұрақ үлгілері сақталуы мүмкін (`assignment_id`, nullable)

---

## ER диаграммасы

```mermaid
erDiagram
    users ||--o{ courses : "teaches (teacher)"
    users ||--o{ enrollments : "enrolled (student)"
    courses ||--o{ enrollments : "has"
    courses ||--o{ assignments : "contains"
    assignments ||--o{ submissions : "receives"
    users ||--o{ submissions : "submits (student)"
    users ||--o{ ai_hints : "requests (student or teacher)"
    assignments ||--o{ ai_hints : "references (optional)"

    users {
        uuid id PK
        string email UK
        string full_name
        string role
        datetime created_at
    }

    courses {
        uuid id PK
        string title
        string description
        uuid teacher_id FK
        datetime created_at
    }

    enrollments {
        uuid id PK
        uuid course_id FK
        uuid student_id FK
        datetime enrolled_at
    }

    assignments {
        uuid id PK
        string title
        string description
        datetime deadline
        uuid course_id FK
        datetime created_at
    }

    submissions {
        uuid id PK
        text code
        string file_name
        string status
        int grade
        text feedback
        uuid assignment_id FK
        uuid student_id FK
        datetime submitted_at
        datetime graded_at
    }

    ai_hints {
        uuid id PK
        text prompt
        text response
        uuid assignment_id FK
        uuid user_id FK
        datetime created_at
    }
```

---

## Ұсыныстар мен талдау (Агент есебі)

1. **Көп — көп байланыс шешілді:** `users` (student) және `courses` арасындағы байланыс `enrollments` аралық кестесі арқылы толық үйлестірілді.
2. **Файл және код үйлесімділігі:** Студенттің жүктеген файлының атауы `file_name` бағанында, ал мазмұны `code` мәтіндік өрісінде сақталады.
3. **Әмбебап ЖИ сақтау:** `ai_hints` кестесі `user_id` арқылы студенттің де (hint), оқытушының да (generate-questions) ЖИ-ге жасаған сұрауларын бірыңғай сақтауға бейімделді.
4. **Қауіпсіздік:** Құпиясөздер Keycloak (OIDC) арқылы сақталады, деректер қорында құпиясөз өрісі жоқ.
