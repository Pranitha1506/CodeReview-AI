# CodeReview AI – Intelligent Code Review & Fixing Platform

An AI-powered code review platform that analyzes source code, identifies potential bugs and security issues, evaluates code quality, and generates improved code with clear explanations.

## Overview

**CodeReview AI** is a web-based developer tool that combines Generative AI and static code analysis to simplify code review and debugging.

Built using Python, FastAPI, MySQL, and Google's Gemini API, the platform provides two independent workflows:

- **Analyze Code:** Performs an AI-powered review to identify potential bugs, logical errors, security concerns, performance issues, and code quality improvements.
- **Fix My Code:** Evaluates submitted code, determines whether corrections are necessary, and generates an improved version with explanations when required.

The application also maintains separate review and fix histories in MySQL, allowing users to revisit, search, filter, and manage previous results.

## Key Features

### 1. AI-Powered Code Analysis
- Analyzes source code using the Gemini API.
- Identifies potential bugs and logical errors.
- Highlights possible security vulnerabilities.
- Recommends performance optimizations.
- Generates an overall code quality score.
- Provides structured review findings and suggestions.

### 2. Intelligent Code Fixing
- Evaluates source code before recommending changes.
- Classifies submitted code into three categories:
  - `NO_FIX_NEEDED` – No significant correction required.
  - `IMPROVEMENT` – Code can be optimized or made cleaner.
  - `BUG_FIX_REQUIRED` – Potential bugs or errors require correction.
- Generates corrected code when necessary.
- Explains the modifications made.
- Displays original and corrected code side by side.
- Provides code differences, remaining issues, and recommended tests.

### 3. Offline Static Analysis Fallback
- Provides a fallback mechanism for the Fix My Code workflow when AI services are unavailable.
- Uses Python's built-in AST module for syntax validation.
- Performs supported static checks without executing submitted code.
- Helps maintain basic code analysis functionality during AI service interruptions.

### 4. Interactive Dashboard
Provides an overview of application activity through:
- Total code reviews.
- Total fix operations.
- Average code review score.
- Total identified bugs.

### 5. Review and Fix History
- Stores review and fix operations separately in MySQL.
- Displays previously saved analysis results.
- Supports searching and filtering by programming language.
- Provides sorting options for history records.
- Allows users to delete saved records.

### 6. Code Management
- Copy corrected code directly.
- Download corrected source code.
- Compare original and corrected versions.
- Inspect modifications through a difference viewer.

## Application Workflow

1. Select the programming language.
2. Enter or paste the source code.
3. Choose the required operation:
   - Analyze Code
   - Fix My Code
4. The backend processes the submitted code using the appropriate AI or static analysis workflow.
5. View the analysis, suggestions, or corrected code.
6. Compare changes and review explanations.
7. Save and revisit previous operations through history.

## System Architecture

The application follows a simple frontend-backend-database architecture.

| Layer | Responsibility | Technology |
|---|---|---|
| Frontend | User interface and interactions | HTML, CSS, JavaScript, Bootstrap |
| Backend | API endpoints and application logic | Python, FastAPI |
| AI Service | Code analysis and correction | Google Gemini API |
| Static Analysis | Syntax validation and supported checks | Python AST |
| Code Comparison | Identifying modifications | Python difflib |
| Database | Persistent review and fix history | MySQL |

## Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Backend Framework | FastAPI |
| Frontend | HTML, CSS, JavaScript, Bootstrap |
| Database | MySQL |
| Generative AI | Google Gemini API |
| Static Analysis | Python AST |
| Code Difference | Python difflib |
| Development Tools | VS Code, MySQL Workbench |
| Version Control | Git, GitHub |

## Project Structure

```text
CodeReview-AI/
│
├── main.py
├── database.py
├── routes.py
├── requirements.txt
├── .env
├── .gitignore
│
├── templates/
│   └── index.html
│
└── static/
    ├── css/
    │   └── style.css
    │
    └── js/
        └── app.js
```

*Note: The structure above represents the current documented layout. Update it if additional files or folders exist in the repository.*

## Installation and Setup

### Prerequisites

- Python 3.10 or later (subject to dependency compatibility).
- MySQL Server.
- Google Gemini API key for AI-powered features.
- Git.

### 1. Clone the Repository

```bash
git clone YOUR_REPOSITORY_URL
cd CodeReview-AI
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate the environment on Windows:

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root directory.

Add the configuration expected by your application:

```env
GEMINI_API_KEY=your_gemini_api_key

DB_HOST=localhost
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_NAME=your_database_name
```

Replace the placeholder values with your actual credentials. Never commit API keys or database passwords to GitHub.

### 5. Configure MySQL

- Start the MySQL server.
- Create the database specified in your environment configuration.
- Ensure the database credentials match your application settings.

### 6. Start the Application

```bash
uvicorn main:app --reload
```

Open the application in your browser:

**http://127.0.0.1:8000**

## Security Considerations

- Sensitive credentials are configured through environment variables.
- Submitted source code is analyzed without intentionally executing it.
- The offline fallback uses static analysis rather than running submitted programs.
- AI-generated code should be reviewed and tested before production use.
- Static analysis and AI-based reviews cannot guarantee the absence of all bugs or vulnerabilities.
- AI-powered functionality depends on Gemini API availability and configuration.

## Future Enhancements

- Extend support for additional programming languages.
- Introduce more advanced language-specific static analysis.
- Generate downloadable code review reports.
- Improve automated test case recommendations.
- Add additional code quality metrics.
- Introduce more detailed security analysis.

## Author

Developed as a software engineering project using **Python, FastAPI, MySQL, JavaScript, and Generative AI**.

