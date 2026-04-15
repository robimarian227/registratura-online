# 🏛️ Registratură Digitală Internă

![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100.0+-green.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite-blue.svg)
![Docker](https://img.shields.io/badge/Deployment-Docker-informational.svg)

Aceasta este o aplicație internă pentru gestiunea și arhivarea electronică a documentelor administrative (Registratură). Proiectul este construit pe o arhitectură ușoară și eficientă, rulând local, cu un accent deosebit pe **utilizarea minimă a memoriei RAM** la transferul fișierelor masive și pe o structură a bazei de date **strict normalizată**.

---

## 🔬 Logica Soluției (Input -> Procesare -> Output)

### 📥 Input
*   **Metadate Extrase:** Data de înregistrare, informații despre expeditor, subiectul documentului, și o listă dinamică de etichete (tags).
*   **Flux Binar:** Documentul fizic selectat pe front-end, expediat serverului prin POST de tip `multipart/form-data`.

### ⚙️ Procesare
1.  **Receptarea Asincronă:** API-ul creat cu **FastAPI** interceptează fișierul.
2.  **Streaming I/O pe Disc:** În loc să încarce tot documentul în memorie, acesta este scris parțial pe disc, în blocuri de 4 MB (configurabile). Acest algoritm previne sufocarea RAM-ului (*Out of Memory*), vital atunci când se procesează fișiere multimedia / PDF-uri de dimensiuni mari (> 100 MB).
3.  **Alocare Dinamică:** Documentul este integrat ierarhic în arhiva principală (ex. `D:/Registratura_Archive/2026/04/`), cu redenumire securizată împotriva atacurilor de tip path-traversal.
4.  **Normalizare Relatională:** Metadatele sunt înregistrate în baza de date locală **SQLite**, respectând riguros standardele de normalizare:
    *   **Forma Normală 1 (1NF):** Atribute complet atomice.
    *   **Forma Normală 2 (2NF):** Extragerea categoriilor repetitive (tag-uri) spre un tabel de referință (`tags`), cuplat prin `document_tags` la tabela principală `documents`. Astfel, evităm dependențele parțiale.
5.  **Căutare Multicriterială:** Motoarele de interogare permit conjuncția logică de filtre multiple (dată, expeditor, subiect și tag exact).

### 📤 Output
*   **Interfață Web (Jinja2):** Listarea inteligentă a colecțiilor documentare cu facilitate de filtrare rapidă.
*   **Static Endpoint:** Funcția care leagă interfața de fișierul fizic menținut în partiția locală, prin răspuns `FileResponse`.

---

## 🏗️ Arhitectura Proiectului

*   `app/main.py`: Controller-ul principal; rute FastAPI și configurarea Jinja2 pentru randarea dinamică a paginilor (fără framekwork-uri front-end greoaie).
*   `app/database.py`: Modelul nivelului de persistență și tranzacții SQLite.
*   `app/storage.py`: Modul specializat pentru path-allocation și I/O optimizat.
*   `templates/` & `static/`: Views-urile și fișierul CSS responsive, structurate ierarhic.
*   `requirements.txt`: Setul minimal de dependențe.

---

## 🚀 Instalare și Configurare

Variabilele principale sunt administrate prin fișierul `.env` sau prin variabile vizibile în nivelul OS / Docker.

### 1️⃣ Rulare via Docker (Portainer Ready) - Recomandat
Implementarea a luat în considerare infrastructurile tip Docker/Portainer.
1. Maparea adreselor locale se regăsește în fișierul `docker-compose.yml`.
2. Rulează suita:
   ```bash
   docker compose up --build -d
   ```
3. Accesează browserul: `http://localhost:8000`

### 2️⃣ Rulare Locală (Python Natival)
Dacă preferi o execuție nativă pe Host (Windows via PowerShell):
```powershell
# 1. Inițializează un mediu virtual
python -m venv .venv
.venv\Scripts\activate

# 2. Instalează dependențele din repo
pip install -r requirements.txt

# 3. Pornește server-ul
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 🔒 Considerații de Securitate și Integritate

*   Nicio parolă sau literă hardcodată de mediu nu apare vizibil în nucleul aplicației - absolut totul fiind manipulat prin `pathlib` și variabile OS pentru maximă abstractizare.
*   Interfețele blochează prelucrarea documentelor dacă lipsesc argumentele indispensabile.
*   Recomandat ca, pentru uz public sau instanțe de producție, serverul să fie izolat prin intermediul unui Reverse Proxy suplimentar (ex: Nginx/Traefik cu TLS).
