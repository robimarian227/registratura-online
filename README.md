# Registratură Digitală Internă

Aplicație web pentru înregistrarea, arhivarea și căutarea documentelor administrative într-un mediu local. Proiectul este gândit pentru rulare on-premises, cu stocare fizică pe disc și metadate persistate în SQLite.

## Logică de funcționare

1. Utilizatorul încarcă un document împreună cu metadatele asociate: data intrării, expeditor, subiect și tag-uri.
2. Backend-ul FastAPI primește fișierul prin streaming și îl scrie pe disc în blocuri fixe, pentru a limita consumul de memorie.
3. Documentul este organizat automat în arhivă pe structura an/lună.
4. Metadatele sunt salvate în SQLite într-o schemă normalizată, iar tag-urile sunt gestionate separat pentru a evita redundanța.
5. Documentele pot fi căutate și filtrate după dată, expeditor, subiect și tag.

## Arhitectură

- Backend: FastAPI + Uvicorn
- Frontend: Jinja2, fără framework JavaScript grele
- Bază de date: SQLite
- Stocare fișiere: filesystem local, configurabil prin variabile de mediu
- Deploy: Docker și Docker Compose, compatibile cu Portainer

## Structura proiectului

- `app/main.py` - rute HTTP și integrarea cu șabloanele Jinja2
- `app/config.py` - încărcarea setărilor din mediu
- `app/database.py` - acces SQLite și operații CRUD
- `app/storage.py` - salvarea fișierelor în streaming și organizarea pe an/lună
- `templates/` - interfață server-side pentru listare, upload și editare
- `static/` - stilizare CSS
- `docker-compose.yml` - rulare cu Docker/Portainer
- `requirements.txt` - dependențe Python

## Model de date

Schema bazei de date respectă principiile de normalizare:

- `documents` conține datele atomice ale documentului: ID, data intrării, expeditor, subiect, cale fișier, nume original, dimensiune și timestamp.
- `tags` păstrează lista de etichete unice.
- `document_tags` leagă documentele de etichete prin relație many-to-many.

Această structură respectă 1NF prin eliminarea grupurilor repetitive și 2NF prin separarea atributelor dependente de entități distincte.

## Instalare și rulare

### Rulare locală

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 9010 --reload
```

Aplicația va fi disponibilă la:

```text
http://127.0.0.1:9010
```

### Rulare cu Docker

```bash
docker compose up --build -d
```

În configurația curentă, aplicația expune portul `9010` pe host.

### Deploy în Portainer

1. Creează un stack nou din repository.
2. Setează `docker-compose.yml` ca fișier Compose.
3. Apasă `Pull and redeploy` după fiecare actualizare.

## Configurare

Setările principale sunt controlate prin variabile de mediu:

- `REGISTRY_APP_NAME`
- `REGISTRY_ARCHIVE_ROOT`
- `REGISTRY_DB_PATH`
- `REGISTRY_UPLOAD_CHUNK_BYTES`
- `REGISTRY_LARGE_FILE_THRESHOLD`

Fișierul `.env.example` servește drept model pentru mediu local.

## Securitate și operare

- Nu sunt necesare credentiale sau secrete în cod.
- ID-ul de înregistrare rămâne imutabil după creare.
- Editarea administrativă modifică doar metadatele permise: expeditor, subiect și tag-uri.
- Pentru producție, se recomandă reverse proxy cu TLS și control de acces.

## Observații

Pentru fișiere mari, aplicația folosește scriere în streaming, astfel încât memoria RAM să rămână stabilă chiar și la upload-uri de peste 100 MB.
