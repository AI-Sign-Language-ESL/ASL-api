<a id="readme-top"></a>

<div align="center">
  <a href="https://github.com/AI-Sign-Language-ESL/ASL-api">
    <img src="https://avatars.githubusercontent.com/u/228776460?s=400&u=c69294e3b9a90eed4ef31dc37ee3ced57c2add89&v=4"
         alt="TAFAHOM Logo"
         height="150"
         style="border-radius: 12px">
  </a>

  <h2 align="center">TAFAHOM Backend API</h2>

  <p align="center">
    Real-time Sign Language Translation Platform 🤟🧠<br />
    Graduation Project – Computer Science
    <br />
    <p align="center">
      <img alt="GitHub License" src="https://img.shields.io/github/license/AI-Sign-Language-ESL/ASL-api">
      <img alt="GitHub issues" src="https://img.shields.io/github/issues/AI-Sign-Language-ESL/ASL-api">
      <img alt="GitHub Tag" src="https://img.shields.io/github/v/tag/AI-Sign-Language-ESL/ASL-api">
      <img alt="Python Version" src="https://img.shields.io/badge/python-3.12%2B-blue">
      <img alt="Docker" src="https://img.shields.io/badge/docker-ready-blue">
</div>

---

## About The Project ✨ <a id="about-the-project"></a>

**TAFAHOM** is a real-time sign language translation backend system designed to enable communication between deaf/hard-of-hearing users and hearing users.  
It provides real-time video frame streaming, buffering and batching, and AI-powered sign translation via gRPC, plus secure authentication and credit management.

The backend is fully decoupled from the AI model — it orchestrates streaming, request handling, and persistence, while the AI service handles inference.

### 🧠 Core Responsibilities

- Handle **live video streaming** via WebSockets (Django Channels)
- **gRPC integration** with an AI translation service
- Frame buffering and batching for efficient inference
- Secure authentication & translation credit management
- Persistent storage of users and translation history

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Key Features 🚀

- 🎥 **Live Video Streaming**
  - WebSocket-based real-time video frame ingestion from clients

- 🧠 **AI Integration via gRPC**
  - Efficient communication with a separate GPU-powered AI service
  - Supports both batch and streaming inference

- ⏱ **Buffered Batching**
  - Configurable frame batching for temporal context in translation

- 🔐 **Authentication & Credit System**
  - Role-based access and translation credit consumption

- 🗄 **PostgreSQL Persistent Storage**
  - Users, translations, partial results stored reliably

- 🐳 **Dockerized Multi-Service Architecture**
  - Backend, AI service, database isolated and orchestrated

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## System Architecture 🏗️

