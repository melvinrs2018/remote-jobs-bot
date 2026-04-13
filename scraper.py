import requests
from bs4 import BeautifulSoup
import os
import time
import random

WP_USER = os.getenv('WP_USERNAME')
WP_PASS = os.getenv('WP_PASSWORD')
WP_URL  = os.getenv('WP_URL')

# Usando RSS feeds públicos que não bloqueiam
FEEDS = [
    ("https://remotive.com/remote-jobs/feed", "Engineering"),
    ("https://weworkremotely.com/categories/remote-programming-jobs.rss", "Engineering"),
    ("https://weworkremotely.com/categories/remote-design-jobs.rss", "Design"),
    ("https://weworkremotely.com/categories/remote-marketing-jobs.rss", "Marketing"),
    ("https://weworkremotely.com/categories/remote-customer-support-jobs.rss", "Customer Service"),
    ("https://weworkremotely.com/remote-jobs.rss", "General"),
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; RSS Reader)',
    'Accept': 'application/rss+xml, application/xml, text/xml',
}

def scrape_jobs():
    all_jobs = []
    for feed_url, category in FEEDS:
        print(f"Lendo feed: {feed_url}")
        try:
            response = requests.get(feed_url, headers=HEADERS, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            items = soup.find_all('item')[:8]

            for item in items:
                try:
                    title = item.find('title')
                    title = title.get_text(strip=True) if title else ''
                    if not title or len(title) < 3:
                        continue

                    link = item.find('link')
                    apply_url = link.get_text(strip=True) if link else feed_url

                    desc = item.find('description')
                    description_raw = desc.get_text(strip=True) if desc else ''

                    # Tenta extrair empresa do título (formato comum: "Company - Job Title")
                    company = "Remote Company"
                    if ' - ' in title:
                        parts = title.split(' - ')
                        company = parts[0].strip()
                        title = parts[-1].strip()
                    elif ' at ' in title.lower():
                        parts = title.lower().split(' at ')
                        company = parts[-1].strip().title()

                    description = f'''<p>Remote opportunity at <strong>{company}</strong>.</p>
<p>📍 Remote Worldwide</p>
<p>{description_raw[:300]}...</p>
<p><a href="{apply_url}" target="_blank" rel="nofollow">View full job description and apply here →</a></p>'''

                    all_jobs.append({
                        'title': title[:100],
                        'company': company,
                        'location': 'Remote',
                        'apply_url': apply_url,
                        'category': category,
                        'is_remote': 'yes',
                        'job_type': 'Full-time',
                        'source': feed_url,
                        'description': description
                    })
                except Exception as e:
                    print(f"  Erro num item: {e}")
                    continue

            print(f"  ✅ {len(items)} vagas em {category}")
            time.sleep(random.uniform(1, 3))

        except Exception as e:
            print(f"  ❌ Erro em {feed_url}: {e}")

    print(f"\nTotal coletado: {len(all_jobs)}")
    return all_jobs


def get_existing_titles():
    if not WP_URL:
        return set()
    try:
        resp = requests.get(
            f"{WP_URL}/wp-json/wp/v2/job",
            params={'per_page': 100, '_fields': 'title'},
            auth=(WP_USER, WP_PASS),
            timeout=10
        )
        if resp.status_code == 200:
            titles = {item['title']['rendered'].lower() for item in resp.json()}
            print(f"Vagas já no site: {len(titles)}")
            return titles
    except Exception as e:
        print(f"Aviso duplicatas: {e}")
    return set()


def post_to_wordpress(job):
    if not WP_URL or not WP_USER or not WP_PASS:
        print("❌ Credenciais não encontradas!")
        return False

    data = {
        'title':   job['title'],
        'content': job['description'],
        'status':  'publish',
        'meta': {
            '_job_location':    job['location'],
            '_company_name':    job['company'],
            '_application':     job['apply_url'],
            '_job_type':        'full-time',
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
            print(f"  ✅ Postado: {job['title']}")
            return True
        else:
            print(f"  ❌ Erro ({resp.status_code}): {resp.text[:300]}")
            return False

    except Exception as e:
        print(f"  ❌ Exceção: {e}")
        return False


def run():
    print("=" * 50)
    print("🤖 OpportunityFinds Bot iniciando...")
    print("=" * 50)

    vagas = scrape_jobs()
    if not vagas:
        print("⚠️ Nenhuma vaga encontrada.")
        return

    existing = get_existing_titles()
    novas = [v for v in vagas if v['title'].lower() not in existing]
    print(f"\nVagas novas: {len(novas)}")

    if not novas:
        print("✅ Todas as vagas já estão no site.")
        return

    sucesso = 0
    for vaga in novas[:20]:
        print(f"\n→ Postando: {vaga['title']}")
        if post_to_wordpress(vaga):
            sucesso += 1
        time.sleep(1)

    print(f"\n{'=' * 50}")
    print(f"✅ Concluído! {sucesso}/{len(novas)} vagas postadas.")
    print("=" * 50)


if __name__ == "__main__":
    run()
