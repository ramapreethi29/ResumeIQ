# 💰 Finance RAG Advisor — Source-Grounded Financial Document Assistant

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge\&logo=python\&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge\&logo=fastapi\&logoColor=white)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?style=for-the-badge\&logo=react\&logoColor=black)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Database-5B21B6?style=for-the-badge)
![Gemini](https://img.shields.io/badge/Gemini-LLM-4285F4?style=for-the-badge\&logo=google\&logoColor=white)
![RAG](https://img.shields.io/badge/RAG-Retrieval%20Augmented%20Generation-FF6F00?style=for-the-badge)

**A full-stack RAG-based financial document assistant that lets users upload finance PDFs, perform semantic search, and generate source-grounded answers using FastAPI, React, ChromaDB, sentence-transformers, and Gemini.**

[🚀 Quick Start](#-quick-start) · [🧠 Architecture](#-rag-architecture) · [🌐 Frontend](#-web-application) · [🔌 API](#-api-endpoints) · [📸 Screenshots](#-screenshots)

</div>

---

## 📌 Overview

Finance RAG Advisor is a full-stack AI application built to answer questions from uploaded finance-related PDF documents using Retrieval-Augmented Generation (RAG).

Instead of relying only on the general knowledge of a language model, the system first extracts text from uploaded PDFs, splits the content into chunks, creates semantic embeddings, stores them in ChromaDB, retrieves the most relevant chunks for a user question, and then uses Gemini to generate a source-grounded response.

The project focuses on building a practical AI document assistant with transparent retrieval, source visibility, fallback behavior, and a clean React frontend.

> **Key Idea:** The model should answer from the uploaded document context, not from unsupported assumptions.

---

## 🎯 Why I Built This

I built this project to understand how production-style AI applications answer questions from domain-specific documents.

The main goal was to explore:

* PDF ingestion and text extraction
* Text chunking for retrieval
* Embedding generation using `sentence-transformers`
* Vector storage and semantic search using ChromaDB
* Source-grounded answer generation using Gemini
* API fallback handling when LLM generation is unavailable
* Full-stack integration between FastAPI and React

This project helped me understand that RAG quality depends heavily on retrieval quality, chunking strategy, and prompt design — not only on the LLM.

---

## ✨ Features

* 📄 Upload finance-related PDF documents
* 🧾 Extract readable text using `pypdf`
* ✂️ Split PDF content into searchable chunks
* 🧠 Generate embeddings using `sentence-transformers`
* 🗄️ Store document chunks in ChromaDB
* 🔍 Perform semantic search using natural language queries
* 🤖 Generate source-grounded answers using Gemini
* 📌 Display source chunks used for each answer
* 🔁 Reset indexed documents during testing
* 🛡️ Fallback retrieval mode when Gemini is unavailable or quota-limited
* 🌐 React frontend for upload, question answering, sources, and reset flow
* 🔗 CORS-enabled frontend-backend integration for local development

---

## 🧠 RAG Architecture

```text
PDF Upload
   │
   ▼
Text Extraction using pypdf
   │
   ▼
Text Chunking
   │
   ▼
Embedding Generation using sentence-transformers
   │
   ▼
ChromaDB Vector Storage
   │
   ▼
Semantic Retrieval
   │
   ▼
Gemini Prompt with Retrieved Context
   │
   ▼
Source-Grounded Answer + Source Chunks
```

### Core RAG Flow

| Stage             | Component             | Purpose                                        |
| ----------------- | --------------------- | ---------------------------------------------- |
| PDF Upload        | FastAPI               | Accept finance-related PDF documents           |
| Text Extraction   | pypdf                 | Extract readable text from uploaded PDFs       |
| Chunking          | Custom splitter       | Break large text into retrievable chunks       |
| Embeddings        | sentence-transformers | Convert text chunks into vector embeddings     |
| Vector Storage    | ChromaDB              | Store and retrieve semantically similar chunks |
| Retrieval         | ChromaDB query        | Fetch top relevant document chunks             |
| Answer Generation | Gemini                | Generate answer using retrieved context        |
| Frontend Display  | React                 | Show answer and source chunks to user          |

---

## 🌐 Web Application

The React frontend provides a simple interface for testing the complete RAG workflow.

### Frontend Capabilities

* Upload a PDF document
* Ask natural language questions
* View AI-generated answers
* View source chunks used for the answer
* Reset indexed document data during testing
* Display success and error states clearly

---

## 🔌 API Endpoints

| Method | Endpoint           | Purpose                           |
| ------ | ------------------ | --------------------------------- |
| GET    | `/health`          | Check backend health              |
| POST   | `/upload`          | Upload and index a PDF            |
| POST   | `/search`          | Retrieve relevant document chunks |
| POST   | `/ask`             | Ask a source-grounded question    |
| DELETE | `/documents/reset` | Reset indexed documents           |

---

## 🛠️ Tech Stack

| Layer                  | Technology            |
| ---------------------- | --------------------- |
| Backend                | FastAPI, Uvicorn      |
| Frontend               | React, Vite           |
| LLM                    | Gemini API            |
| Embeddings             | sentence-transformers |
| Vector Database        | ChromaDB              |
| PDF Processing         | pypdf                 |
| Environment Management | python-dotenv         |
| Language               | Python, JavaScript    |

---

## 📁 Project Structure

```text
Finance-rag-advisor/
│
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI routes and middleware
│   │   ├── config.py            # Environment and app configuration
│   │   ├── pdf_loader.py        # PDF text extraction
│   │   ├── text_splitter.py     # Document chunking logic
│   │   ├── vector_store.py      # ChromaDB storage and retrieval
│   │   ├── rag_pipeline.py      # Gemini prompt and RAG answer generation
│   │   └── schemas.py           # Pydantic request/response schemas
│   │
│   ├── uploads/                 # Local uploaded PDFs ignored by Git
│   ├── chroma_db/               # Local ChromaDB storage ignored by Git
│   ├── requirements.txt
│   ├── .env.example
│   └── .gitignore
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # React application logic
│   │   ├── App.css              # Main UI styling
│   │   ├── index.css
│   │   └── main.jsx
│   │
│   ├── package.json
│   └── vite.config.js
│
├── screenshots/
│   ├── frontend-upload-success.png
│   ├── frontend-answer-with-sources.png
│   ├── health-check-success.png
│   ├── upload-success.png
│   ├── semantic-search-sip.png
│   └── reset-vector-database.png
│
├── README.md
└── .gitignore
```

---

## 🚀 Quick Start

### Prerequisites

* Python 3.10+
* Node.js and npm
* Gemini API key
* Git

---

### 1. Clone the Repository

```bash
git clone https://github.com/aadi090204/Finance-rag-advisor.git
cd Finance-rag-advisor
```

---

### 2. Backend Setup

Go to the backend folder:

```bash
cd backend
```

Create and activate a virtual environment:

```bash
python -m venv venv
venv\Scripts\activate
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file inside the `backend` folder:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Start the FastAPI backend:

```bash
uvicorn app.main:app --reload
```

Open the backend API docs:

```text
http://127.0.0.1:8000/docs
```

---

### 3. Frontend Setup

Open a new terminal and go to the frontend folder:

```bash
cd Finance-rag-advisor/frontend
```

Install frontend dependencies:

```bash
npm install
```

Start the React development server:

```bash
npm run dev
```

Open the frontend:

```text
http://localhost:5173
```

---

## 💬 Example Questions

After uploading a finance-related PDF, try questions such as:

```json
{
  "question": "What is an emergency fund and why is it important?"
}
```

```json
{
  "question": "What does the document say about SIP?"
}
```

```json
{
  "question": "What investment risks are mentioned?"
}
```

---

## 📸 Screenshots

### Frontend Upload Flow

![Frontend Upload](screenshots/frontend-upload-success.png)

### Frontend Source-Grounded Answer

![Frontend Answer](screenshots/frontend-answer-with-sources.png)

### API Health Check

![Health Check](screenshots/health-check-success.png)

### API PDF Upload

![PDF Upload](screenshots/upload-success.png)

### API Semantic Search

![Semantic Search](screenshots/semantic-search-sip.png)

### API Reset Vector Database

![Reset Vector Database](screenshots/reset-vector-database.png)

---

## ⚠️ What Went Wrong

While building the project, I ran into a few practical issues:

1. The first Gemini model name used was not available for the configured API version.
2. Another Gemini model returned a quota error, so the backend needed fallback handling.
3. Raw character-based chunking sometimes split sentences awkwardly.
4. PDF extraction quality depended on whether the uploaded PDF contained real text or scanned images.
5. Retrieval and generation needed to be tested separately to debug answer quality.

---

## ✅ How I Fixed It

* Added error handling around Gemini answer generation.
* Added fallback retrieval mode that returns relevant source chunks if LLM generation fails.
* Added a `/search` endpoint to debug retrieval separately from answer generation.
* Added `/documents/reset` to clear indexed data during testing.
* Added source chunk references to make answers more transparent.
* Added CORS middleware so the React frontend can communicate with the FastAPI backend.

---

## 📚 What I Learned

* RAG quality depends heavily on retrieval quality, not only on the LLM.
* Chunking strategy affects how accurately relevant information is retrieved.
* A separate semantic search endpoint makes debugging easier.
* LLM APIs can fail due to quota, model availability, or provider changes.
* Fallback behavior is important for AI applications.
* Source-grounded answers are more trustworthy than generic chatbot responses.
* Full-stack AI applications need clean API contracts between backend and frontend.

---

## 🗺️ Future Work

* [ ] Improve chunking using paragraph-aware or sentence-aware splitting
* [ ] Add document deletion by filename
* [ ] Add support for multiple uploaded documents with document-level filtering
* [ ] Add authentication for uploaded documents
* [ ] Add downloadable answer reports
* [ ] Add Dockerfile and Docker Compose after local Docker testing
* [ ] Deploy backend and frontend with environment-based configuration
* [ ] Add Prometheus metrics for request latency and error count
* [ ] Add evaluation dataset for testing answer quality
* [ ] Add support for multiple LLM providers

---

## 🔐 Security Notes

* The `.env` file is ignored by Git and should never be committed.
* Uploaded PDFs are stored locally only during development.
* The app should not be used with sensitive financial documents unless proper authentication, encryption, and storage controls are added.

---

## 📄 Disclaimer

This project is for educational and portfolio purposes only. It does not provide investment advice, financial planning advice, or product recommendations. Answers are generated from uploaded document context and may still require human verification.

---

## 👤 Author

**Adithya Anil**
AI Engineer / DevOps Engineer
GitHub: [aadi090204](https://github.com/aadi090204)

---

<div align="center">
<i>Built as a full-stack AI portfolio project exploring RAG, semantic search, vector databases, and source-grounded financial document question answering.</i>
</div>
