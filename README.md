# 🏙️ City Event Aggregator — AI Multi-Agent System

> **B.E. Electronics & Communication · Semester IV End-Semester Project**  
> *Introduction to Agentic AI Systems*

A fully deployed, real-time, multi-agent AI system that discovers events in any city, 
analyses live weather, curates personalised recommendations, and evaluates its own output quality.

[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B)](https://streamlit.io)
[![Groq](https://img.shields.io/badge/LLM-Groq-f55036)](https://groq.com)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)

---

## 🚀 Live Demo

**Deployed URL:** https://city-event-aggregator.up.railway.app/

---

## 🤖 The 5 Agents

| Agent | Role | Tools Used |
|-------|------|-----------|
| **EventDiscoveryAgent** | Finds upcoming events via web search | Tavily Search + DuckDuckGo |
| **WeatherAgent** | Real-time weather + 5-day forecast | OpenWeatherMap API |
| **EventCuratorAgent** | Filters, ranks, and enriches events | Groq |
| **RecommendationAgent** | Builds personalised day plans + dining/transport tips | Groq + DuckDuckGo |
| **JudgeAgent** | Evaluates recommendation quality with a rubric | Groq |

---

## 🏗️ Architecture

```
User Input (City + Preferences)
           │
    ┌──────▼──────────────────────────┐
    │     CityEventOrchestrator       │
    └──────┬────────┬────────┬────────┘
           │        │        │
    ┌──────▼───┐ ┌──▼───┐ ┌──▼──────────┐
    │ Agent 1  │ │Ag. 2 │ │  Agent 3    │
    │ Event    │ │Weath-│ │  Event      │
    │ Discovery│ │ er   │ │  Curator    │
    │Tavily+DDG│ │ OWM  │ │  Groq     │
    └──────┬───┘ └──┬───┘ └──┬──────────┘
           └────────┴─────────┘
                    │
          ┌─────────▼─────────┐
          │     Agent 4       │
          │  Recommendation   │
          │  Groq + DDG       │
          └─────────┬─────────┘
                    │
          ┌─────────▼─────────┐
          │     Agent 5       │
          │   LLM-as-Judge    │
          │    Groq           │
          └─────────┬─────────┘
                    │
          ┌─────────▼─────────┐
          │   Streamlit UI    │
          └───────────────────┘
```

---

## 🛠️ Tech Stack

- **Language:** Python 3.10+
- **UI:** Streamlit
- **LLM:** Groq (Llama 3 70B — Free Tier)
- **Search:** Tavily (primary) + DuckDuckGo (fallback + secondary)
- **Weather:** OpenWeatherMap API (Free tier)
- **Deployment:** Streamlit Cloud / Railway

---

## ⚡ Quick Start

```bash
# 1. Clone
git clone https://github.com/yourusername/city-event-aggregator
cd city-event-aggregator

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up API keys
cp .env.example .env
# Edit .env and add your keys (all free)

# 4. Run
streamlit run app.py
```

---

## 🔑 Free API Keys

| Service | Free Tier | Sign-up URL |
|---------|-----------|-------------|
| Groq | Free Tier varies by model | https://console.groq.com/keys |
| Tavily Search | 1000 calls/month | https://app.tavily.com |
| OpenWeatherMap | 1000 calls/day | https://openweathermap.org/api |
| DuckDuckGo | Unlimited (no key needed) | Built-in |

---

## 📁 Project Structure

```
city-event-aggregator/
├── app.py                     # Streamlit UI
├── orchestrator.py            # Multi-agent coordinator
├── config.py                  # Settings & API keys
├── requirements.txt
├── .env.example
├── agents/
│   ├── base_agent.py          # Base class (Groq + retry)
│   ├── event_discovery_agent.py  # Agent 1
│   ├── weather_agent.py          # Agent 2
│   ├── curator_agent.py          # Agent 3
│   ├── recommendation_agent.py   # Agent 4
│   └── judge_agent.py            # Agent 5
└── tools/
    ├── tavily_tool.py         # Tavily search wrapper
    ├── duckduckgo_tool.py     # DDG search wrapper
    └── weather_tool.py        # OpenWeatherMap wrapper
```

---

## 📊 LLM-as-Judge Rubric

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Relevance | 25% | Events match user interests + city |
| Accuracy | 20% | Information is current and factual |
| Weather Integration | 20% | Weather meaningfully used in recommendations |
| Completeness | 15% | All required info fields present |
| Usefulness | 20% | Real users would find this actionable |

---

## 👥 Team

- **Role A (Architect):** Anvay Khobragade
- **Role B (Builder):** Ankush Sharan
