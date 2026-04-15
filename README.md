# Registratura Digitala Interna

## Logica Solutiei
Input:
- Metadate document: data intrare, expeditor, subiect, tag-uri.
- Fisier document uploadat prin formular web.

Procesare:
1. API-ul FastAPI primeste formularul multipart.
2. Fisierul este scris pe disc in streaming, in blocuri fixe, pentru a limita RAM.
3. Calea de stocare se aloca automat in arhiva, pe ierarhia an/luna.
4. Metadatele se insereaza in SQLite, cu schema normalizata 1NF/2NF.
5. Interogarile de cautare aplica filtre dupa data, expeditor, subiect, tag.

Output:
- Lista documentelor si endpoint de acces la fisierul stocat.
- Baza de date actualizata cu metadate relationale.

## Arhitectura
- `app/main.py`: endpoint-uri FastAPI si integrare Jinja2.
- `app/database.py`: model relational SQLite si operatii CRUD/search.
- `app/storage.py`: alocare cale an/luna si upload streaming.
- `templates/`: randare server-side pentru UI.
- `static/styles.css`: stilizare minima, responsive.

## Normalizare Baza de Date (1NF / 2NF)
- Tabelul `documents` contine atribute atomice per document (1NF).
- Tag-urile sunt extrase in tabelul `tags`.
- Relatia many-to-many este modelata prin `document_tags`, eliminand grupurile repetitive si dependentele partiale (2NF).

## Rulare Locala (Python)
1. Creeaza un mediu virtual.
2. Instaleaza dependintele: `pip install -r requirements.txt`
3. Ruleaza serverul: `uvicorn app.main:app --reload`
4. Deschide: `http://127.0.0.1:8000`

## Rulare cu Docker / Portainer
1. Configureaza volumele pentru persistenta `data` si arhiva.
2. Ruleaza: `docker compose up --build -d`
3. Aplicatia expune portul 8000.

## Observatii de securitate
- Configuratiile sunt livrate prin variabile de mediu.
- Nu sunt stocate credentiale in codul sursa.
- Pentru productie, se recomanda reverse proxy cu TLS si control de acces.
