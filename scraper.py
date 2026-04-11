import requests
from bs4 import BeautifulSoup
import os

# Pega as chaves que você configurou nos Secrets
WP_USER = os.getenv('WP_USERNAME')
WP_PASS = os.getenv('WP_PASSWORD')
WP_URL = os.getenv('WP_URL')

def scrape_jobs():
    url = "https://remote.co/remote-jobs/it"
    
    # Esse é o "disfarce": faz o site achar que você é um humano no Chrome
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://google.com'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        jobs = []
        
        # Procura os títulos das vagas (seletor específico para o remote.co)
        for job_card in soup.find_all('a', class_='card'):
            title_tag = job_card.find('span', class_='font-weight-bold')
            if title_tag:
                jobs.append({
                    'title': title_tag.get_text(strip=True),
                    'content': f"Nova vaga remota encontrada! Detalhes no site original: {url}"
                })
        return jobs
    except Exception as e:
        print(f"Erro ao acessar site de vagas: {e}")
        return []

def post_to_wordpress(title, content):
    data = {
        'title': title,
        'content': content,
        'status': 'publish'
    }
    
    # Envia para o seu site opportunityfinds.com
    response = requests.post(WP_URL, json=data, auth=(WP_USER, WP_PASS))
    
    if response.status_code == 201:
        print(f"Sucesso! Postado: {title}")
    else:
        print(f"Erro no WordPress: {response.status_code} - {response.text}")

def run():
    print("Iniciando o robô...")
    vagas = scrape_jobs()
    if not vagas:
        print("Nenhuma vaga encontrada (pode ser bloqueio ou site mudou).")
        return
        
    for vaga in vagas[:3]: # Posta 3 vagas para testar
        post_to_wordpress(vaga['title'], vaga['content'])

if __name__ == "__main__":
    run()
