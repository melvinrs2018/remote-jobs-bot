import requests
from bs4 import BeautifulSoup
import os
import time

# Secrets do GitHub Actions
WP_USER = os.getenv('WP_USERNAME')
WP_PASS = os.getenv('WP_PASSWORD')
WP_URL  = os.getenv('WP_URL')  # ex: https://opportunityfinds.com

# URLs do remote.co para scraping
CATEGORIES = [
    ("https://remote.co/remote-jobs/it",             "Engineering"),
    ("https://remote.co/remote-jobs/developer",      "Engineering"),
    ("https://remote.co/remote-jobs/design",         "Design"),
    ("https://remote.co/remote-jobs/marketing",      "Marketing"),
    ("https://remote.co/remote-jobs/customer-service","Sales"),
    ("https://remote.co/remote-jobs/writing",        "Writing"),
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
}

def scrape_jobs():
    all_jobs = []
    for url, category in CATEGORIES:
        print(f"Scraping: {url}")
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Pega todos os cards de vagas
            cards = soup.select('a[href*="/job-details/"]')
            if not cards:
                # fallback: qualquer link com job-details
                cards = [a for a in soup.find_all('a', href=True) if '/job-details/' in a['href']]

            for card in cards[:10]:  # max 10 por categoria
                try:
                    href = card.get('href', '')
                    job_url = href if href.startswith('http') else "https://remote.co" + href

                    # Título
                    title_tag = (
                        card.find('h2') or
                        card.find('h3') or
                        card.find(class_=lambda c: c and 'title' in c.lower()) or
                        card.find('span', class_='font-weight-bold')
                    )
                    title = title_tag.get_text(strip=True) if title_tag else card.get_text(strip=True)[:80]
                    if not title or len(title) < 3:
                        continue

                    # Empresa
                    company_tag = card.find(class_=lambda c: c and 'company' in c.lower())
                    company = company_tag.get_text(strip=True) if company_tag else "Remote.co"

                    # Localização
                    loc_tag = card.find(class_=lambda c: c and ('location' in c.lower() or 'region' in c.lower()))
                    location = loc_tag.get_text(strip=True) if loc_tag else "Remote"

                    all_jobs.append({
                        'title':     title,
                        'company':   company,
                        'location':  location,
                        'apply_url': job_url,
                        'category':  category,
                        'is_remote': 'yes',
                        'job_type':  'Full-time',
                        'source':    'remote.co',
                        'description': f'<p>Remote opportunity at <strong>{company}</strong>.</p><p>📍 {location}</p><p><a href="{job_url}" target="_blank" rel="nofollow">View full job description and apply here →</a></p>'
                    })
                except Exception as e:
                    print(f"  Erro num card: {e}")
                    continue

            print(f"  ✅ {len(cards[:10])} vagas encontradas em {category}")
            time.sleep(2)  # respeitar o servidor

        except Exception as e:
            print(f"  ❌ Erro em {url}: {e}")

    print(f"\nTotal de vagas coletadas: {len(all_jobs)}")
    return all_jobs


def get_existing_titles():
    """Busca títulos já postados para evitar duplicatas."""
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
        print(f"Aviso: não foi possível checar duplicatas: {e}")
    return set()


def post_to_wordpress(job):
    """Posta a vaga como custom post type 'job'."""
    if not WP_URL or not WP_USER or not WP_PASS:
        print("❌ Credenciais não encontradas!")
        return False

    data = {
        'title':   job['title'],
        'content': job['description'],
        'status':  'publish',
        'type':    'job',
        'meta': {
            'company':   job['company'],
            'location':  job['location'],
            'apply_url': job['apply_url'],
            'job_type':  job['job_type'],
            'is_remote': job['is_remote'],
            'source':    job['source'],
        }
    }

    try:
        # Posta o job
        resp = requests.post(
            f"{WP_URL}/wp-json/wp/v2/job",
            json=data,
            auth=(WP_USER, WP_PASS),
            timeout=15
        )

        if resp.status_code == 201:
            post_id = resp.json().get('id')
            print(f"  ✅ Postado: {job['title']} (ID: {post_id})")

            # Salva os meta fields separadamente
            meta_fields = {
                'company':   job['company'],
                'location':  job['location'],
                'apply_url': job['apply_url'],
                'job_type':  job['job_type'],
                'is_remote': job['is_remote'],
                'source':    job['source'],
            }
            for key, value in meta_fields.items():
                requests.post(
                    f"{WP_URL}/wp-json/wp/v2/job/{post_id}",
                    json={'meta': {key: value}},
                    auth=(WP_USER, WP_PASS),
                    timeout=10
                )

            # Associa categoria
            if job.get('category'):
                # Busca ou cria o termo
                term_resp = requests.get(
                    f"{WP_URL}/wp-json/wp/v2/job_category",
                    params={'slug': job['category'].lower()},
                    auth=(WP_USER, WP_PASS),
                    timeout=10
                )
                if term_resp.status_code == 200 and term_resp.json():
                    term_id = term_resp.json()[0]['id']
                else:
                    create_term = requests.post(
                        f"{WP_URL}/wp-json/wp/v2/job_category",
                        json={'name': job['category'], 'slug': job['category'].lower()},
                        auth=(WP_USER, WP_PASS),
                        timeout=10
                    )
                    term_id = create_term.json().get('id') if create_term.status_code == 201 else None

                if term_id:
                    requests.post(
                        f"{WP_URL}/wp-json/wp/v2/job/{post_id}",
                        json={'job_category': [term_id]},
                        auth=(WP_USER, WP_PASS),
                        timeout=10
                    )
            return True

        else:
            print(f"  ❌ Erro ({resp.status_code}): {resp.text[:200]}")
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

    # Evitar duplicatas
    existing = get_existing_titles()
    novas = [v for v in vagas if v['title'].lower() not in existing]
    print(f"\nVagas novas para postar: {len(novas)}")

    if not novas:
        print("✅ Todas as vagas já estão no site.")
        return

    sucesso = 0
    for vaga in novas[:20]:  # max 20 por execução
        print(f"\n→ Postando: {vaga['title']}")
        if post_to_wordpress(vaga):
            sucesso += 1
        time.sleep(1)

    print(f"\n{'=' * 50}")
    print(f"✅ Concluído! {sucesso}/{len(novas)} vagas postadas.")
    print("=" * 50)


if __name__ == "__main__":
    run()
