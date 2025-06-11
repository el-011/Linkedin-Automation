# 🤖 LinkedIn Automation using Gemini & Flask

A Python-based automation system that periodically generates and posts content (ReactJS tips or jokes) to LinkedIn using the Gemini API, with optional analytics tracking and manual triggers.

## 🚀 Features

- ✅ Generates fun and concise ReactJS-related content using **Gemini API**
- ✅ Auto-posts content to **LinkedIn** every minute via **APScheduler**
- ✅ Tracks post history and engagement (likes, comments, shares, views)
- ✅ Exposes REST API for manual generation, posting, and analytics
- ✅ Saves content to a local JSON database for transparency and history

---

## 🔧 Tech Stack

- **Python 3**
- **Flask** – for serving the API
- **APScheduler** – for scheduling automated posts
- **requests** – for HTTP calls to Gemini and LinkedIn
- **dotenv** – for environment variable management

---

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/linkedin-auto-poster.git
   cd linkedin-auto-poster

### 2. Create & Activate a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```
### 5. Run the Application

```bash
python linkedin.py
```
