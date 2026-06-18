<a id="readme-top"></a>
<div align="center">
  <a href="https://github.com/AI-Sign-Language-ESL/ASL-api">
    <img src="https://avatars.githubusercontent.com/u/228776460?s=400&u=c69294e3b9a90eed4ef31dc37ee3ced57c2add89&v=4"
         alt="TAFAHOM Logo"
         height="150"
         style="border-radius: 12px">
  </a>
  <h2 align="center">Tafahom API</h2>
  <p align="center">
    Real-time Sign Language Translation Platform 🤟🧠<br />
    Graduation Project – Computer Science
    <br />
    <p align="center">
      <a href="https://techforpalestine.org/learn-more"><img alt="StandWithPalestine" src="https://raw.githubusercontent.com/Safouene1/support-palestine-banner/master/StandWithPalestine.svg"></a>
      <img alt="GitHub License" src="https://img.shields.io/github/license/AI-Sign-Language-ESL/ASL-api">
      <img alt="GitHub issues" src="https://img.shields.io/github/issues/AI-Sign-Language-ESL/ASL-api">
      <img alt="Python Version" src="https://img.shields.io/badge/python-3.12%2B-blue">
      <img alt="Docker" src="https://img.shields.io/badge/docker-ready-blue">
    </p>
</div>

## About The Project ✨

**Tafahom ASL API** is a backend system designed to bridge communication gaps by translating **Egyptian Sign Language (ESL)** into text and voice, and vice versa.  
It powers real-time and batch translation pipelines using computer vision, NLP, and speech technologies.

The system is built with scalability and real-time performance in mind, supporting both **REST APIs** and **WebSocket streaming**.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Key Features 🚀

- 🤟 **Sign → Text Translation** (real-time & batch)
- 📝 **Text → Sign Translation** with generated sign videos
- 🎙️ **Voice → Sign** and **Sign → Voice**
- ⚡ **WebSocket Streaming** for live sign recognition
- 🔐 **JWT Authentication & Google OAuth**
- 🧠 **AI-powered pipeline** (CV, NLP, TTS, STT)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Tech Stack 🛠️

| Technology | Purpose |
|------------|---------|
| **Python** | Primary Language |
| **Django** | Web Framework |
| **Django Channels** | WebSocket Support |
| **PostgreSQL** | Relational Database |
| **Redis** | Message Broker & Cache |
| **Docker** | Containerization |
| **MediaPipe** | Computer Vision Framework |
| **Transformers** | AI & NLP Models |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Getting Started 🚀

Follow these steps to set up the project locally.

### Prerequisites 📦

- Python 3.12+

```sh
sudo apt install python3
```

### Installation ⚙️

1. Clone the repo

```sh
git clone https://github.com/AI-Sign-Language-ESL/ASL-api.git
```

2. Navigate to the project directory

```sh
cd ASL-api
```

3. Set up a virtual environment and activate it

```sh
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

4. Install dependencies

```sh
pip install -r requirements.txt
```

5. Configure Environment Variables

Ensure you have a `.env.dev` file present in the `ASL-api` directory. It will be loaded automatically by Django for local development since the default mode is set to `DEV`.

6. Apply database migrations

Before migrating, make sure to set `DJANGO_ENV=development` so it uses your local settings and isolated environment.

```sh
# Windows (CMD)
set DJANGO_ENV=development
python src/manage.py makemigrations sign_language
python src/manage.py migrate

# Windows (PowerShell)
$env:DJANGO_ENV="development"
python src/manage.py makemigrations sign_language
python src/manage.py migrate

# macOS/Linux
export DJANGO_ENV=development
python src/manage.py makemigrations sign_language
python src/manage.py migrate
```

7. Create a superuser for creating the first user

```sh
python src/manage.py createsuperuser
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Usage 🔧

Here is how to run the project locally without affecting the production deployment:

1. Start the development server with the environment flag active

```sh
# Windows (CMD)
set DJANGO_ENV=development
python src/manage.py runserver

# Windows (PowerShell)
$env:DJANGO_ENV="development"
python src/manage.py runserver

# macOS/Linux
export DJANGO_ENV=development
python src/manage.py runserver
```

2. Visit `http://127.0.0.1:8000` in your browser.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Deployment 🚀

The project is configured for easy deployment using Docker.

```sh
docker-compose up --build -d
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Contributing 👥

Contributions are welcome! To get started:

1. Fork the repository
2. Create a branch for your feature (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing-feature'`)
4. Push the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## License 📜

Distributed under the GPL v3 License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
