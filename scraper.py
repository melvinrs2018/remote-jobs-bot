import requests
from bs4 import BeautifulSoup
import os

# Pega as chaves que você configurou nos Secrets
WP_USER = os.getenv('WP_USERNAME')
WP_PASS = os.getenv('WP_PASSWORD')
WP_URL = os.getenv('WP_URL')

def scrape_jobs():
    url = "https://remote.co/remote-jobs/it"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        jobs = []
        
        # Seletor atualizado e mais forte para o Remote.co
        # Ele procura links que contenham '/remote-jobs/' no endereço
        for link in soup.find_all('a', href=True):
            if '/remote-jobs/' in link['href'] and 'card' in link.get('class', []):
                title_tag = link.find('span', class_='font-weight-bold')
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    job_url = "https://remote.co" + link['href']
                    jobs.append({
                        'title': title,
                        'content': f"Nova vaga remota encontrada!\n\nCandidate-se aqui: {job_url}"
                    })
        
        print(f"Total de vagas encontradas: {len(jobs)}")
        return jobs
    except Exception as e:
        print(f"Erro no Scraper: {e}")
        return []

def post_to_wordpress(title, content):
    if not WP_URL or not WP_USER or not WP_PASS:
        print("Erro: Credenciais do WordPress não encontradas no ambiente!")
        return

    data = {
        'title': title,
        'content': content,
        'status': 'publish'
    }
    
    response = requests.post(WP_URL, json=data, auth=(WP_USER, WP_PASS))
    
    if response.status_code == 201:
        print(f"✅ Sucesso! Postado: {title}")
    else:
        print(f"❌ Erro no WordPress ({response.status_code}): {response.text}")

def run():
    print("Iniciando o robô...")
    vagas = scrape_jobs()
    
    if not vagas:
        print("⚠️ Nenhuma vaga encontrada. O seletor do site pode ter mudado.")
        return
        
    # Tenta postar as 5 primeiras vagas encontradas
    for vaga in vagas[:5]:
        post_to_wordpress(vaga['title'], vaga['content'])

if __name__ == "__main__":
    run()
