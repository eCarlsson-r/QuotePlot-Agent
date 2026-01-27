# 🤖 Lucy AI: Predictive Market Intelligence & Agentic Router

Lucy AI is a modernized, full-stack machine learning ecosystem designed for real-time market analysis and intent classification. Originally a legacy Python 2 system, it has been re-engineered into a high-performance FastAPI service featuring a robust SVM Pipeline and a dynamic React/amCharts 5 frontend.

## 🚀 Key Features

- **Intent Intelligence**: A modernized Scikit-Learn SVC pipeline that classifies user queries with 86% accuracy and provides real-time confidence scores.
- **Predictive Market Insights**: Automagically identifies bullish/bearish trends using historical stock data via a custom Lucy Brain logic bridge.
- **Modernized Infrastructure**: Successfully migrated from legacy pickle formats to efficient joblib pipelines, ensuring Python 3.10+ compatibility.
- **Dynamic Visualization**: High-fidelity financial charts powered by amCharts 5, featuring real-time data streaming and responsive "Insight Overlays."
- **Scalable Routing**: An intelligent Agent Router that handles Web3-ready requests and balances model predictions with probability-based guardrails.

## 🛠️ Tech Stack

### Backend (The Brain)

- **FastAPI**: High-performance asynchronous API framework.
- **SQLAlchemy**: ORM for robust data persistence and historical trend analysis.
- **Scikit-Learn**: Feature engineering (TF-IDF equivalent) and Linear SVM classification.
- **Joblib**: Optimized model serialization for fast cold-starts.

### Frontend (The Interface)

- **React + TypeScript**: Type-safe UI components for mission-critical reliability.
- **amCharts 5**: Advanced data visualization for complex time-series data.
- **Tailwind CSS**: Modern, responsive styling with glassmorphic UI elements.

## 📈 Model Performance

Lucy was evaluated using a 10-fold Stratified Cross-Validation to ensure reliability across imbalanced datasets.

| Metric | Class 0 (Closed) | Class 1 (Open) | Combined |
| Precision | 0.56 | 0.91 | 0.86 (Weighted) |
| Recall | 0.52 | 0.92 | 0.86 (Weighted) |
| F1-Score | 0.54 | 0.92 | 0.86 (Weighted) |

The model utilizes class_weight='balanced' to ensure the minority "Closed Question" class is handled with maximum sensitivity.

## 📂 Project Structure

├── lucy/               # Legacy Feature Engineering Bridge (Modernized)
├── models/             # Serialized Joblib Pipelines & Vocabularies
├── routers/            # FastAPI Agent Logic & Insight Endpoints
├── data/               # Feature-engineered training sets
├── buildmodel.py       # ML Pipeline training & Balancing logic
└── evalmodel.py        # ROC Curve & Classification performance scripts

## 🛠️ Installation & Setup

1. Clone & Install Dependencies
```bash
pip install -r requirements.txt
```
2. Seed the Market Brain
```bash
python seed_data.py
```
3. Launch the Agent
```bash
uvicorn main:app --reload
```

## 👨‍💻 Recruitment & Business Inquiries

This project demonstrates expertise in **Legacy Code Modernization, MLOps (Model Deployment),** and **Full-Stack Financial Dashboarding**.

**Available for:**
- Machine Learning Engineering roles
- Full-Stack AI Development
- Custom Trading Bot / Dashboard consultations