from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, JSON
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pymongo import MongoClient
from datetime import datetime
import os, json, io
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

load_dotenv()

# ===== 1. REAL DB LAYER: POSTGRES + MONGODB =====
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

class Search(Base):
    __tablename__ = "searches"
    id = Column(Integer, primary_key=True)
    query = Column(String, index=True)
    city = Column(String, default="Nairobi")
    result_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

mongo_client = MongoClient(os.getenv("MONGO_URL"))
mongo_db = mongo_client["marketlens"]
reviews_col = mongo_db["reviews"]

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# ===== 2. REAL DATA LAYERS: SERPAPI + REDDIT =====
from serpapi import GoogleSearch
import praw
from bs4 import BeautifulSoup
import requests

def get_real_market_data(query: str, city: str):
    """Layer 3: Quantitative Data Layer"""
    params = {"engine": "google_trends", "q": query, "location": "Kenya", "api_key": os.getenv("SERPAPI_KEY")}
    search = GoogleSearch(params)
    trends = search.get_dict().get("interest_over_time", {}).get("timeline_data", [])
    demand = "Rising" if len(trends) > 1 and trends[-1]['values'][0]['value'] > trends[0]['values'][0]['value'] else "Stable"

    params2 = {"engine": "google_shopping", "q": query, "api_key": os.getenv("SERPAPI_KEY")}
    shop = GoogleSearch(params2).get_dict().get("shopping_results", [])
    prices = [float(r['extracted_price']) for r in shop if 'extracted_price' in r][:10]
    price_range = f"Ksh {min(prices):.0f} - {max(prices):.0f}" if prices else "N/A"

    return {
        "query": query, "city": city, "demand_level": demand,
        "market_size": "Requires paid API: Statista/Similarweb",
        "competitors": [r['title'] for r in shop[:5]],
        "price_range": price_range
    }

def get_real_consumer_voice(query: str):
    """Layer 2: Consumer Voice Aggregator"""
    reddit = praw.Reddit(client_id=os.getenv("REDDIT_CLIENT_ID"), client_secret=os.getenv("REDDIT_CLIENT_SECRET"), user_agent="MarketLens")
    posts = [p.title + " + p.selftext for p in reddit.subreddit("Kenya").search(query, limit=20)]

    reviews_col.insert_many([{"source": "reddit", "text": t, "query": query, "created_at": datetime.utcnow()} for t in posts])

    pos_words = ["good","love","best","cheap","fast"]
    neg_words = ["bad","hate","expensive","slow","scam"]
    pos = sum(any(w in t.lower() for w in pos_words) for t in posts)
    neg = sum(any(w in t.lower() for w in neg_words) for t in posts)
    total = len(posts) or 1
    return {"positive": int(pos/total*100), "neutral": 100-int((pos+neg)/total*100), "negative": int(neg/total*100), "summary": " ".join(posts[:3])[:300]}

# ===== 3. REAL AI LAYER: OPENAI =====
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_real_ai_insight(query: str, city: str, data: dict, sentiment: dict):
    """Layer 4: AI Insight Generator"""
    prompt = f"""
    You are a Decision Intelligence AI for MarketLens.
    Idea: {query} in {city}
    Market Data: {json.dumps(data)}
    Consumer Sentiment: {json.dumps(sentiment)}
    Task: Answer all 4 Core Modules:
    1. Market Insight: Demand, Size, Competitors, Pricing.
    2. Consumer Voice: What people like/dislike, complaints.
    3. Risk Analysis: Saturation, viability in {city}.
    4. Recommendation: GO / NO-GO / NEEDS RESEARCH + Pricing strategy.
    Keep under 250 words. Be direct.
    """
    resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=400)
    return resp.choices[0].message.content

# ===== 4. REAL PDF REPORT BUILDER =====
def build_pdf_report(query, city, data, sentiment, ai_text):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    y = 800
    p.setFont("Helvetica-Bold", 18); p.drawString(50, y, f"MarketLens Report: {query}"); y -= 30
    p.setFont("Helvetica", 10); p.drawString(50, y, f"City: {city} | Date: {datetime.utcnow().date()}"); y -= 30
    p.setFont("Helvetica-Bold", 12); p.drawString(50, y, "1. Market Insight"); y -= 20
    p.setFont("Helvetica", 10); p.drawString(50, y, f"Demand: {data['demand_level']} | Price: {data['price_range']}"); y -= 20
    p.drawString(50, y, f"Competitors: {', '.join(data['competitors'])}"); y -= 30
    p.setFont("Helvetica-Bold", 12); p.drawString(50, y, "2. Consumer Sentiment"); y -= 20
    p.setFont("Helvetica", 10); p.drawString(50, y, f"Pos: {sentiment['positive']}% Neg: {sentiment['negative']}%"); y -= 20
    p.drawString(50, y, sentiment['summary'][:200]); y -= 30
    p.setFont("Helvetica-Bold", 12); p.drawString(50, y, "3. AI Analysis"); y -= 20
    for line in ai_text.split('\n'):
        p.drawString(50, y, line[:90]); y -= 15;
        if y < 100: p.showPage(); y = 800
    p.save(); buffer.seek(0)
    return buffer

# ===== 5. REAL GLASS UI - ALL 7 SCREENS YOU LISTED =====
app = FastAPI(title="MarketLens")
BASE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MarketLens</title><script src="https://cdn.tailwindcss.com"></script><script src="https://unpkg.com/lucide@latest"></script><style>body{background:#0F172A;font-family:Inter}.glass{background:rgba(30,41,59,.6);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.1)}.accent{color:#34D399}</style></head><body class="pb-24 text-slate-200"><div class="max-w-2xl mx-auto p-4">{}</div><nav class="fixed bottom-4 left-1/2 -translate-x-1/2 w-[95%] max-w-md glass rounded-2xl flex justify-around py-3">{}</nav><script>lucide.createIcons()</script></body></html>"""
NAV = '<a href="/" class="flex flex-col items-center {}"><i data-lucide="search" class="w-6 h-6"></i><span class="text-xs">Search</span></a><a href="/reports" class="flex flex-col items-center {}"><i data-lucide="file-text" class="w-6 h-6"></i><span class="text-xs">Reports</span></a><a href="/knowledge" class="flex flex-col items-center {}"><i data-lucide="book" class="w-6 h-6"></i><span class="text-xs">KB</span></a><a href="#" class="flex flex-col items-center text-slate-400"><i data-lucide="user" class="w-6 h-6"></i><span class="text-xs">Profile</span></a>'

@app.get("/", response_class=HTMLResponse)
def home():
    content = """<div class="pt-8"><h1 class="text-3xl font-bold">MarketLens <span class="accent">AI</span></h1><p class="text-slate-400 mb-6">Validate before you invest.</p><form action="/analyze" method="post" class="glass p-4 rounded-2xl space-y-3"><input name="query" placeholder="Business idea" required class="w-full px-4 py-3 bg-slate-900 rounded-xl"><input name="city" placeholder="City e.g. Nairobi" value="Nairobi" class="w-full px-4 py-3 bg-slate-900 rounded-xl"><button class="w-full py-3 font-bold bg-emerald-600 rounded-xl">Analyze</button></form><div class="mt-8"><p class="font-semibold mb-2">Categories</p><div class="grid grid-cols-2 gap-3"><a href="/category/Transport" class="glass p-3 rounded-xl">Transport</a><a href="/category/Agriculture" class="glass p-3 rounded-xl">Agriculture</a><a href="/category/Retail" class="glass p-3 rounded-xl">Retail</a><a href="/category/Digital" class="glass p-3 rounded-xl">Digital</a></div></div></div>"""
    return BASE.format(content, NAV.format("accent","text-slate-400","text-slate-400"))

@app.post("/analyze", response_class=HTMLResponse)
def analyze(query: str = Form(...), city: str = Form(...), db: Session = Depends(get_db)):
    data = get_real_market_data(query, city)
    sentiment = get_real_consumer_voice(query)
    ai_text = get_real_ai_insight(query, city, data, sentiment)
    s = Search(query=query, city=city, result_json={"data":data,"sentiment":sentiment,"ai":ai_text}); db.add(s); db.commit()

    content = f"""<div><a href="/" class="flex items-center gap-2 mb-4 text-slate-400"><i data-lucide="arrow-left"></i> Back</a><h1 class="text-2xl font-bold">{query}</h1><p class="text-slate-400 mb-4">{city}</p><div class="space-y-4"><div class="glass p-4 rounded-2xl"><p class="font-semibold mb-2">Market Overview</p><p>Demand: <span class="accent font-bold">{data['demand_level']}</span></p><p>Price: {data['price_range']}</p><p>Competitors: {', '.join(data['competitors'])}</p></div><div class="glass p-4 rounded-2xl"><p class="font-semibold mb-2">Consumer Sentiment</p><p class="text-sm">{sentiment['summary']}</p><div class="flex gap-4 mt-2 text-sm"><span class="text-green-400">Pos: {sentiment['positive']}%</span><span class="text-red-400">Neg: {sentiment['negative']}%</span></div></div><div class="glass p-4 rounded-2xl border-emerald-500/30"><p class="font-semibold mb-2 accent">AI Analysis</p><p class="whitespace-pre-wrap">{ai_text}</p></div><a href="/report/{s.id}" class="block text-center py-3 font-bold bg-emerald-600 rounded-xl">Download PDF Report</a></div></div>"""
    return BASE.format(content, NAV.format("text-slate-400","accent","text-slate-400"))

@app.get("/reports", response_class=HTMLResponse)
def reports(db: Session = Depends(get_db)):
    searches = db.query(Search).order_by(Search.created_at.desc()).limit(20).all()
    items = "".join([f'<a href="/report/{s.id}" class="block glass p-4 rounded-xl"><p class="font-semibold">{s.query} - {s.city}</p><p class="text-sm text-slate-400">{s.created_at.date()}</p></a>' for s in searches]) or '<p class="text-slate-400">No reports yet.</p>'
    return BASE.format(f'<div class="pt-8"><h1 class="text-2xl font-bold mb-4">Saved Reports</h1><div class="space-y-3">{items}</div></div>', NAV.format("text-slate-400","accent","text-slate-400"))

@app.get("/report/{id}")
def report(id: int, db: Session = Depends(get_db)):
    s = db.query(Search).get(id); d=s.result_json
    pdf = build_pdf_report(s.query, s.city, d['data'], d['sentiment'], d['ai'])
    return StreamingResponse(pdf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=MarketLens_{s.query}.pdf"})

@app.get("/knowledge", response_class=HTMLResponse)
def knowledge():
    kbs = {"Transport":"Boda, Matatu, Logistics. High demand urban.","Agriculture":"Maize, Avocado export. Seasonal.","Retail":"Mitumba, Electronics. Saturated CBD.","Digital":"SaaS, Agencies. Rising."}
    items = "".join([f'<div class="glass p-4 rounded-xl"><p class="font-semibold">{k}</p><p class="text-sm text-slate-400">{v}</p></div>' for k,v in kbs.items()])
    return BASE.format(f'<div class="pt-8"><h1 class="text-2xl font-bold mb-4">Knowledge Base</h1><div class="space-y-3">{items}</div></div>', NAV.format("text-slate-400","text-slate-400","accent"))

@app.get("/category/{cat}", response_class=HTMLResponse)
def category(cat:str):
    return BASE.format(f'<div class="pt-8"><h1 class="text-2xl font-bold">{cat}</h1><p class="text-slate-400">Prebuilt insights for {cat}.</p><form action="/analyze" method="post" class="glass p-4 rounded-2xl mt-4"><input type="hidden" name="query" value="{cat}"><input name="city" placeholder="City" value="Nairobi" class="w-full px-4 py-3 bg-slate-900 rounded-xl mb-3"><button class="w-full py-3 font-bold bg-emerald-600 rounded-xl">Analyze {cat}</button></form></div>', NAV.format("accent","text-slate-400","text-slate-400"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
