# API жобасы

> **Аутентификация:** Барлық қорғалған эндпоинттер Keycloak арқылы берілген Bearer JWT токенін талап етеді.  
> Жүйеге кіру және токен алу Keycloak OIDC протоколы арқылы орындалады (`POST /auth/realms/edu-realm/protocol/openid-connect/token`).

---

## 1. Маршруттар кестесі

| Метод | Жол | Кім | Не істейді | Story | Кесте |
|---|---|---|---|---|---|
| POST | /api/v1/courses | teacher, admin | Жаңа курс құру | US-2.2 | courses |
| GET | /api/v1/courses | student, teacher, admin | Барлық курстар тізімін алу | - | courses |
| GET | /api/v1/courses/{id} | student, teacher, admin | Нақты бір курстың мәліметін көру | - | courses |
| POST | /api/v1/courses/{id}/enroll | student | Курсқа тіркелу / жазылу | US-1.4 | enrollments |
| GET | /api/v1/courses/my | student | Студенттің өзі жазылған курстарының тізімі | US-1.4 | enrollments |
| POST | /api/v1/assignments | teacher | Жаңа тапсырма немесе зертханалық жұмыс құру | US-2.3 | assignments |
| GET | /api/v1/assignments | student, teacher | Тапсырмалар тізімін қарау | US-1.1 | assignments |
| GET | /api/v1/assignments/{id} | student, teacher | Нақты бір тапсырманың толық шартын көру | US-1.1 | assignments |
| POST | /api/v1/submissions | student | Тапсырма шешімін (код немесе файл) жүктеу | US-1.1 | submissions |
| GET | /api/v1/submissions/my | student | Студенттің өз тапсырған жұмыстарының тізімі | US-1.3 | submissions |
| GET | /api/v1/submissions/{id} | student, teacher | Жіберілген жұмыстың нәтижесі мен бағасын көру | US-1.3 | submissions |
| GET | /api/v1/assignments/{id}/submissions | teacher | Тапсырма бойынша барлық студенттердің шешімдерін көру | US-2.1 | submissions |
| PATCH | /api/v1/submissions/{id}/grade | teacher | Студент жұмысын бағалау және кері байланыс қалдыру | US-2.1 | submissions |
| POST | /api/v1/ai/hints | student | Кодтағы қате бойынша AI-дан нұсқаулық (hint) алу | US-1.2 | ai_hints |
| GET | /api/v1/ai/hints/my | student | Студенттің AI көмекшісінен алған кеңестер тарихын көру | US-1.2 | ai_hints |
| POST | /api/v1/ai/generate-questions | teacher | Сабақ материалынан AI арқылы сұрақтар үлгілерін алу | US-2.4 | ai_hints |
| GET | /api/v1/users/me | authenticated | Өз профилінің мәліметтерін көру | - | users |
| PATCH | /api/v1/users/{id}/role | admin | Пайдаланушыға жаңа рөл тағайындау | US-3.1 | users |

---

## 2. Жауап кодтары («Сервер не дейді»)

| Статус коды | Атауы | Сервер не дейді (мағынасы және жобадағы қолданылуы) |
|---|---|---|
| **200** | OK | Сұраныс сәтті өтті (деректер алынды немесе жаңартылды). |
| **201** | Created | Жаңа ресурс сәтті құрылды (курс ашылды, тіркелді, тапсырма құрылды, шешім жүктелді). |
| **400** | Bad Request | Бизнес-логика талабы бұзылды (дедлайн өтіп кеткен, курсқа бұрыннан жазылған, соңғы админді өшіруге болмайды). |
| **401** | Unauthorized | Токен жоқ немесе жарамсыз (Keycloak арқылы жүйеге кіру қажет). |
| **403** | Forbidden | Рұқсат шектелген (рөл сәйкес келмейді немесе бөтен студенттің жұмысы). |
| **404** | Not Found | Сұралған ресурс табылмады (тапсырма, жұмыс, курс немесе пайдаланушы базада жоқ). |
| **422** | Unprocessable Entity | Деректер тексеруден (валидациядан) өтпеді (балл 0-100 арасында емес, атауы 3-200 таңба емес, рұқсат етілмеген файл форматы). |
| **503** | Service Unavailable | Қызмет уақытша қолжетімсіз (жергілікті Ollama AI модулі өшіп тұр немесе жауап бермейді). |
