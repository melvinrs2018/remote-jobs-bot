import requests
import os
import time

WP_USER = os.getenv('WP_USERNAME')
WP_PASS = os.getenv('WP_PASSWORD')
WP_URL  = os.getenv('WP_URL')

def get_jobs():
    print("Buscando vagas na API do Remotive...")
    try:
        resp = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"limit": 50},
            timeout=20
        )
        jobs = resp.json().get("jobs", [])
        print(f"Total encontrado: {len(jobs)}")
        return jobs
    except Exception as e:
        print(f"ERRO ao buscar vagas: {e}")
        return []

def get_existing_titles():
    try:
        resp = requests.get(
            f"{WP_URL}/wp-json/wp/v2/job_listing",
            params={"per_page": 100, "_fields": "title"},
            auth=(WP_USER, WP_PASS),
            timeout=10
        )
        if resp.status_code == 200:
            titles = {i["title"]["rendered"].lower() for i in resp.json()}
            print(f"Vagas ja no site: {len(titles)}")
            return titles
    except Exception as e:
        print(f"Aviso: {e}")
    return set()

def post_job(job):
    title = job.get("title", "")
    company = job.get("company_name", "Remote Company")
    location = job.get("candidate_required_location", "Remote Worldwide")
    apply_url = job.get("url", "")
    salary = job.get("salary", "")
    description = f"""
<p><strong>{company}</strong> — {location}</p>
{"<p>💰 " + salary + "</p>" if salary else ""}
<p>{job.get("description", "")[:500]}</p>
<p><a href="{apply_url}" target="_blank">Apply here →</a></p>
"""
    data = {
        "title": title,
        "content": description,
        "status": "publish",
        "meta": {
            "_job_location": location,
            "_company_name": company,
            "_application": apply_url,
            "_job_type": "full-time",
        }
    }
    try:
        resp = requests.post(
            f"{WP_URL}/wp-json/wp/v2/job_listing",
            json=data,
            auth=(WP_USER, WP_PASS),
            timeout=15
        )
        if resp.status_code == 201:
            print(f"  OK: {title}")
            return True
        else:
            print(f"  ERRO {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"  EXCECAO: {e}")
        return False

def run():
    print("=" * 48)
    print("OpportunityFinds Bot — API Remotive")
    print("=" * 48)

    jobs = get_jobs()
    if not jobs:
        print("Nenhuma vaga encontrada.")
        return

    existing = get_existing_titles()
    novas = [j for j in jobs if j.get("title","").lower() not in existing]
    print(f"Vagas novas para postar: {len(novas)}")

    sucesso = 0
    for job in novas[:20]:
        if post_job(job):
            sucesso += 1
        time.sleep(1)

    print(f"Concluido! {sucesso} vagas postadas.")

if __name__ == "__main__":
    run()
