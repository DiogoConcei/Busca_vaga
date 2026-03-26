import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from sqlalchemy.orm import Session
import models
import time
import random
import requests
from urllib.parse import quote

def get_driver():
    """Configura o driver VISÍVEL para máxima compatibilidade."""
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = uc.Chrome(options=options)
    driver.set_window_size(1366, 768)
    return driver

def scrape_github(db: Session):
    """Busca no GitHub (Rápido)."""
    vagas_novas = 0
    repos = ["backend-br/vagas", "frontendbr/vagas", "react-brasil/vagas", "pythonbrasil/vagas"]
    keywords = ["estágio", "estagio", "intern", "computação", "junior", "jr"]
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Bot-Vagas-Intern"}

    print("\n[GitHub] Verificando comunidades...")
    for repo in repos:
        try:
            url = f"https://api.github.com/repos/{repo}/issues?state=open&per_page=30"
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                for issue in res.json():
                    title = issue.get('title')
                    link = issue.get('html_url')
                    if any(kw in title.lower() for kw in keywords):
                        if not db.query(models.Vaga).filter(models.Vaga.link == link).first():
                            db.add(models.Vaga(
                                titulo=title, empresa="GitHub Community", link=link,
                                localizacao="Remoto", area=repo.split('/')[0], status="Novo"
                            ))
                            vagas_novas += 1
                db.commit()
        except: continue
    print(f"   [i] GitHub: {vagas_novas} novas.")
    return vagas_novas

def scrape_selenium_sites(db: Session, driver):
    """Busca em camadas sequenciais para máxima precisão."""
    vagas_novas = 0
    
    # Termos de busca específicos para o Rio de Janeiro
    termos = [
        "estagio python",
        "estagio desenvolvimento",
        "estagio ti",
        "estagio front end",
        "estagio back end",
        "estagio dados",
        "estagio software",
        "estagio react",
        "estagio computação"
    ]

    config_sites = [
        {
            "name": "RioVagas",
            "base_url": "https://riovagas.com.br/?s={query}",
            "selectors": ["article h2 a", "h2.entry-title a", ".post-title a"],
            "loc_selector": ".post-city"
        },
        {
            "name": "Indeed",
            "base_url": "https://br.indeed.com/jobs?q={query}&l=Rio+de+Janeiro%2C+RJ&sort=date",
            "selectors": ["h2.jobTitle a", "a.jcs-JobTitle"],
            "loc_selector": ".companyLocation, [data-testid='text-location']"
        },
        {
            "name": "Catho",
            "base_url": "https://www.catho.com.br/vagas/{query_slug}-rj/?q={query_encoded}",
            "selectors": ["h2 a", ".Title-module__title___3S2cv a"],
            "loc_selector": ".sc-kgOKUu a, [data-testid='job-location']"
        },
        {
            "name": "LinkedIn",
            "base_url": "https://www.linkedin.com/jobs/search?keywords={query_encoded}&location=Rio%20de%20Janeiro%2C%20Brasil&f_TPR=r604800",
            "selectors": ["h3.base-search-card__title", ".base-card__full-link"],
            "loc_selector": ".job-search-card__location"
        }
    ]

    kw_tech = [
        "estágio", "estagio", "intern", "computação", "ti", "python", "dev", 
        "junior", "jr", "software", "dados", "analista", "desenvolvimento",
        "frontend", "backend", "fullstack", "react", "web", "engenharia"
    ]

    for termo in termos:
        print(f"\n{'='*20}\nINICIANDO BUSCA: {termo.upper()}\n{'='*20}")
        
        for site in config_sites:
            try:
                # Gerar URL específica para o termo
                query_encoded = quote(termo)
                query_slug = termo.replace(" ", "-")
                url = site['base_url'].format(
                    query=termo, 
                    query_encoded=query_encoded, 
                    query_slug=query_slug
                )

                print(f"[{site['name']}] Pesquisando '{termo}'...")
                driver.get(url)
                time.sleep(random.uniform(6, 10))

                # Lógica de Login/Bloqueio (Especialmente LinkedIn)
                if "login" in driver.current_url or "checkpoint" in driver.current_url or "authwall" in driver.current_url:
                    print("\n" + "!"*60)
                    print(f"[!] BLOQUEIO EM {site['name'].upper()} DETECTADO!")
                    print("[!] Por favor, resolva o login/captcha manualmente.")
                    print("[!] Garanta que você está vendo a lista de vagas antes de continuar.")
                    print("!"*60)
                    input(">>> Após resolver, pressione ENTER aqui no terminal para continuar...")
                    time.sleep(3)

                found_any = False
                for selector in site['selectors']:
                    items = driver.find_elements(By.CSS_SELECTOR, selector)
                    if items:
                        found_any = True
                        for item in items[:15]:
                            try:
                                title = item.text.strip()
                                link = item.get_attribute("href")
                                if not title or not link: continue
                                
                                if any(kw in title.lower() for kw in kw_tech):
                                    if not db.query(models.Vaga).filter(models.Vaga.link == link).first():
                                        # Identificação de Localização
                                        loc = "Rio de Janeiro, RJ" if site['name'] == "RioVagas" else "Brasil"
                                        try:
                                            card = item.find_element(By.XPATH, "./ancestor::li | ./ancestor::article | ./ancestor::div[contains(@class, 'card')]")
                                            loc_element = card.find_element(By.CSS_SELECTOR, site['loc_selector'])
                                            loc_text = loc_element.text.strip()
                                            if loc_text: loc = loc_text
                                        except:
                                            # Fallback textual
                                            text_context = card.text.lower() if 'card' in locals() else title.lower()
                                            if "rio" in text_context or "rj" in text_context: loc = "Rio de Janeiro, RJ"
                                            elif "remoto" in text_context: loc = "Remoto"

                                        print(f"   [+] {site['name'].upper()}: {title[:35]}... ({loc})")
                                        db.add(models.Vaga(
                                            titulo=title, empresa=site['name'], link=link,
                                            localizacao=loc, area=termo.split()[-1].capitalize(), status="Novo"
                                        ))
                                        vagas_novas += 1
                            except: continue
                        break # Se funcionou um seletor, pula para o próximo site/termo
                
                db.commit()
                time.sleep(random.uniform(3, 6)) # Descanso entre buscas para evitar bloqueio

            except Exception as e:
                print(f"   [!] Erro em {site['name']} ({termo}): {e}")
                continue
            
    return vagas_novas

def real_scrape(db: Session):
    total = 0
    total += scrape_github(db)
    
    driver = None
    try:
        driver = get_driver()
        total += scrape_selenium_sites(db, driver)
    except Exception as e:
        print(f"Erro no Driver: {e}")
    finally:
        if driver: driver.quit()

    print(f"\n=== PROCESSO COMPLETO: {total} NOVAS VAGAS NO TOTAL ===")

def mock_scrape(db: Session):
    real_scrape(db)
