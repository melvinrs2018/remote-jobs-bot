import requests
from bs4 import BeautifulSoup
import base64
import json
from datetime import datetime

# ── CONFIGURAÇÕES ──────────────────────────────────────────
WP_URL      = "https://opportunityfinds.com"
WP_USER     = "seu-usuario-editor"
WP_APP_PASS = "xxxx xxxx xxxx xxxx xxxx xxxx"  # Application Password do WP

REMOTE_CO_URL = "https://remote.co/remote-jobs/"
# ──────────────────────────────────────────────────────────

def get_auth_header():
    token = base64.b64encode(f"{WP_USER}:{WP_APP_PASS}".encode()).decode()
    return {"Authorization": f"Basic {token}"}

def scrape_jobs():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(REMOTE_CO_URL, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    
    jobs = []
    # Seleciona os cards de vagas
    for card in soup.select(".job_listing"):
        title    = card.select_one(".position h2")
        company  = card.select_one(".company_name")
        link     = card.get("data-href") or card.select_one("a")["href"]
        category = card.select_one(".job-type")
        
        if title:
            jobs.append({
                "title":    title.get_text(strip=True),
                "company":  company.get_text(strip=True) if company else "N/A",
                "link":     link,
                "category": category.get_text(strip=True) if category else "Remote",
            })
    return jobs

def post_job_to_wp(job):
    endpoint = f"{WP_URL}/wp-json/wp/v2/job-listings"
    
    payload = {
        "title":   job["title"],
        "status":  "publish",
        "content": f"""
            <p><strong>Empresa:</strong> {job['company']}</p>
            <p><strong>Tipo:</strong> {job['category']}</p>
            <p><strong>Candidatar-se:</strong> 
               <a href='{job['link']}' target='_blank'>Ver vaga completa no Remote.co</a>
            </p>
        """,
        "meta": {
            "_job_location":    "Remote",
            "_application":     job["link"],
            "_company_name":    job["company"],
            "_job_expires":     "",
        }
    }
    
    r = requests.post(
        endpoint,
        headers={**get_auth_header(), "Content-Type": "application/json"},
        data=json.dumps(payload)
    )
    return r.status_code, r.json().get("id", "erro")

def run():
    print(f"[{datetime.now()}] Iniciando coleta de vagas...")
    jobs = scrape_jobs()
    print(f"  → {len(jobs)} vagas encontradas")
    
    for job in jobs:
        status, job_id = post_job_to_wp(job)
        print(f"  ✓ '{job['title']}' → status {status}, ID {job_id}")

if __name__ == "__main__":
    run()
