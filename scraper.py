import requests
from bs4 import BeautifulSoup
import os

# Configurações do WordPress vindas dos Secrets
WP_USER = os.getenv('WP_USERNAME')
WP_PASS = os.getenv('WP_PASSWORD')
WP_URL = os.getenv('WP_URL')

def scrape_jobs():
    # URL do site de vagas (exemplo)
    url = "https://remote.co/remote-jobs/it"
    
    # DISFARCE: Isso faz o site achar que é um navegador Chrome real
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
        
        # Aqui o bot procura os títulos das vagas (ajustado para o site remote.co)
        for job_card in soup.find_all('a', class_='card'):
            title_tag = job_card.find('span', class_='font-weight-bold')
            if title_tag:
                jobs.append({
                    'title': title_tag.get_text(strip=True),
                    'content': f"Vaga encontrada no site original. Confira no link: {url}"
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
    
    response = requests.post(WP_URL, json=data, auth=(WP_USER, WP_PASS))
    
    if response.status_code == 201:
        print(f"Postado com sucesso: {title}")
    else:
        print(f"Erro ao postar: {response.status_code} - {response.text}")

def run():
    print("Iniciando busca de vagas...")
    vagas = scrape_jobs()
    if not vagas:
        print("Nenhuma vaga nova encontrada ou site bloqueou o acesso.")
        return
        
    for vaga in vagas[:3]: # Posta apenas as 3 primeiras para testar
        post_to_wordpress(vaga['title'], vaga['content'])

if __name__ == "__main__":
    run()
