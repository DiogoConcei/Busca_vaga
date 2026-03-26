import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from sqlalchemy.orm import Session
import models
import time
import random
import requests
import os
from urllib.parse import quote

def find_browser_executable():
    """Procura Chrome, Edge ou Brave nos locais padrão ou no registro do Windows."""
    # 1. Lista de caminhos comuns para navegadores baseados em Chromium
    paths = [
        # Google Chrome
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        # Microsoft Edge (Padrão no Windows 10/11 e baseado em Chromium)
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        # Brave Browser
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe")
    ]
    
    for path in paths:
        if os.path.exists(path):
            return path

    # 2. Tenta descobrir o navegador padrão via Registro do Windows
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice") as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\shell\open\command") as cmd_key:
                command, _ = winreg.QueryValueEx(cmd_key, "")
                # O comando costuma ser '"C:\Caminho\navegador.exe" --args'
                if '"' in command:
                    return command.split('"')[1]
                return command.split(' ')[0]
    except:
        pass

    return None

def get_driver():
    """Configura o driver VISÍVEL para máxima compatibilidade."""
    browser_path = find_browser_executable()
    
    def get_options():
        options = uc.ChromeOptions()
        if browser_path:
            options.binary_location = browser_path
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        return options
    
    try:
        # Tenta iniciar normalmente
        driver = uc.Chrome(options=get_options(), browser_executable_path=browser_path)
    except Exception as e:
        error_msg = str(e)
        if "session not created" in error_msg.lower() and "version" in error_msg.lower():
            import re
            match = re.search(r"Current browser version is ([\d.]+)", error_msg)
            if match:
                v_full = match.group(1)
                v_main = int(v_full.split('.')[0])
                print(f"\n[!] Conflito de versão. Forçando driver {v_main} para o navegador em {browser_path}...")
                driver = uc.Chrome(options=get_options(), version_main=v_main, browser_executable_path=browser_path)
            else:
                raise e
        else:
            if not browser_path:
                print("\n[!] ERRO: Nenhum navegador Chromium (Chrome, Edge, Brave) foi encontrado!")
            raise e

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

def save_page_sample(site_name, termo, html_content):
    """Salva o HTML da página atual para refinamento posterior."""
    try:
        amostras_dir = os.path.join(os.path.dirname(__file__), "amostras")
        if not os.path.exists(amostras_dir):
            os.makedirs(amostras_dir)
        
        # Nome do arquivo amigável: site_termo_timestamp.html
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        termo_slug = termo.replace(" ", "_").lower()
        filename = f"{site_name.lower()}_{termo_slug}_{timestamp}.html"
        filepath = os.path.join(amostras_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        # print(f"      [v] Amostra salva: {filename}")
    except Exception as e:
        print(f"      [!] Erro ao salvar amostra: {e}")

def scrape_selenium_sites(db: Session, driver):
    """Busca em camadas sequenciais para máxima precisão."""
    vagas_novas = 0
    
    # Termos de busca específicos
    termos = ["estagio python", "estagio desenvolvimento", "estagio ti", "estagio dados", "estagio react"]

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
            "loc_selector": ".companyLocation"
        },
        {
            "name": "Catho",
            "base_url": "https://www.catho.com.br/vagas/{query_slug}-rj/?q={query_encoded}",
            "selectors": ["h2 a", ".Title-module__title___3S2cv a"],
            "loc_selector": ".sc-kgOKUu a"
        },
        {
            "name": "LinkedIn",
            "base_url": "https://www.linkedin.com/jobs/search?keywords={query_encoded}&location=Rio%20de%20Janeiro%2C%20Brasil&f_TPR=r604800",
            "selectors": ["h3.base-search-card__title", ".base-card__full-link"],
            "loc_selector": ".job-search-card__location"
        }
    ]

    kw_tech = ["estágio", "estagio", "intern", "computação", "ti", "python", "dev", "software", "dados", "react"]

    for termo in termos:
        print(f"\n{'='*20}\nBUSCA REAL: {termo.upper()}\n{'='*20}")
        
        for site in config_sites:
            try:
                query_encoded = quote(termo)
                query_slug = termo.replace(" ", "-")
                url = site['base_url'].format(query=termo, query_encoded=query_encoded, query_slug=query_slug)

                print(f"[{site['name']}] Pesquisando...")
                driver.get(url)
                time.sleep(random.uniform(5, 8))

                # SALVAMENTO DE AMOSTRA: Guarda o que o bot está vendo agora
                save_page_sample(site['name'], termo, driver.page_source)

                if "login" in driver.current_url or "authwall" in driver.current_url:
                    print(f"[!] Bloqueio em {site['name']} detectado. Resolva e pressione ENTER...")
                    input(">>>")

                found_in_site = 0
                for selector in site['selectors']:
                    items = driver.find_elements(By.CSS_SELECTOR, selector)
                    if items:
                        for item in items[:15]:
                            try:
                                title = item.text.strip()
                                link = item.get_attribute("href")
                                if not title or not link: continue
                                
                                # LIMPEZA DE LINK (Remove parâmetros de rastreio que causam falsas duplicatas)
                                clean_link = link.split('?')[0].split(';')[0]
                                
                                if any(kw in title.lower() for kw in kw_tech):
                                    # VERIFICAÇÃO DE DUPLICIDADE: Busca pelo link limpo no banco
                                    exists = db.query(models.Vaga).filter(
                                        (models.Vaga.link == clean_link) | (models.Vaga.link == link)
                                    ).first()

                                    if not exists:
                                        loc = "Rio de Janeiro, RJ"
                                        try:
                                            card = item.find_element(By.XPATH, "./ancestor::li | ./ancestor::article | ./ancestor::div[contains(@class, 'card')]")
                                            loc_element = card.find_element(By.CSS_SELECTOR, site['loc_selector'])
                                            loc = loc_element.text.strip()
                                        except: pass

                                        print(f"   [+] Nova Vaga: {title[:40]}...")
                                        db.add(models.Vaga(
                                            titulo=title, empresa=site['name'], link=clean_link,
                                            localizacao=loc, area=termo.split()[-1].capitalize(), status="Novo"
                                        ))
                                        vagas_novas += 1
                                        found_in_site += 1
                            except: continue
                        if found_in_site > 0: break
                
                db.commit()
                time.sleep(random.uniform(2, 4))

            except Exception as e:
                print(f"   [!] Erro em {site['name']}: {e}")
                continue
            
    return vagas_novas

def scrape_local_samples(db: Session, driver):
    """
    MODO REFINAMENTO: Processa arquivos HTML locais na pasta 'amostras'.
    Isso permite testar seletores sem ser bloqueado pelos sites reais.
    """
    import glob
    vagas_novas = 0
    amostras_dir = os.path.join(os.path.dirname(__file__), "amostras")
    
    if not os.path.exists(amostras_dir):
        print(f"\n[!] Pasta de amostras não encontrada em: {amostras_dir}")
        return 0

    arquivos = glob.glob(os.path.join(amostras_dir, "*.html"))
    if not arquivos:
        print("\n[i] Nenhuma amostra (.html) encontrada para processar.")
        return 0

    print(f"\n{'='*30}\nMODO REFINAMENTO: PROCESSANDO {len(arquivos)} AMOSTRAS\n{'='*30}")

    # Configurações de sites (mesmas do scrape_selenium_sites para consistência)
    config_sites = {
        "riovagas": {
            "name": "RioVagas",
            "selectors": ["article h2 a", "h2.entry-title a", ".post-title a"],
            "loc_selector": ".post-city"
        },
        "indeed": {
            "name": "Indeed",
            "selectors": ["h2.jobTitle a", "a.jcs-JobTitle"],
            "loc_selector": ".companyLocation, [data-testid='text-location']"
        },
        "catho": {
            "name": "Catho",
            "selectors": ["h2 a", ".Title-module__title___3S2cv a"],
            "loc_selector": ".sc-kgOKUu a, [data-testid='job-location']"
        },
        "linkedin": {
            "name": "LinkedIn",
            "selectors": ["h3.base-search-card__title", ".base-card__full-link"],
            "loc_selector": ".job-search-card__location"
        }
    }

    kw_tech = ["estágio", "estagio", "intern", "computação", "ti", "python", "dev", "junior", "software"]

    for arquivo_path in arquivos:
        nome_arquivo = os.path.basename(arquivo_path).lower()
        site_key = None
        
        # Identifica o site pelo nome do arquivo
        for key in config_sites.keys():
            if key in nome_arquivo:
                site_key = key
                break
        
        if not site_key:
            print(f"[?] Arquivo ignorado (site não identificado): {nome_arquivo}")
            continue

        site = config_sites[site_key]
        print(f"\n[Amostra] Testando seletores de {site['name']} em: {nome_arquivo}")
        
        # Carrega o arquivo local no navegador
        file_url = "file:///" + os.path.abspath(arquivo_path).replace("\\", "/")
        driver.get(file_url)
        time.sleep(2)

        achados_nesta_amostra = 0
        for selector in site['selectors']:
            items = driver.find_elements(By.CSS_SELECTOR, selector)
            if items:
                for item in items:
                    try:
                        title = item.text.strip()
                        link = item.get_attribute("href")
                        if not title: continue
                        
                        # Se achou algo, vamos logar para o usuário ver que o seletor funcionou
                        if any(kw in title.lower() for kw in kw_tech):
                            achados_nesta_amostra += 1
                            if not db.query(models.Vaga).filter(models.Vaga.link == link).first():
                                db.add(models.Vaga(
                                    titulo=f"[AMOSTRA] {title}", empresa=site['name'], link=link,
                                    localizacao="Local/Amostra", area="Refinamento", status="Novo"
                                ))
                                vagas_novas += 1
                    except: continue
                if achados_nesta_amostra > 0:
                    print(f"   [OK] Seletor '{selector}' funcionou! Achou {achados_nesta_amostra} vagas.")
                    break
        
        if achados_nesta_amostra == 0:
            print(f"   [!] ALERTA: Nenhum seletor funcionou para esta amostra de {site['name']}!")

    db.commit()
    print(f"\n{'='*30}\nFIM DO REFINAMENTO: {vagas_novas} vagas importadas das amostras.\n{'='*30}")
    return vagas_novas

def real_scrape(db: Session):
    total = 0
    total += scrape_github(db)
    
    driver = None
    try:
        driver = get_driver()
        
        # 1. Primeiro tenta as amostras locais (ajuda a verificar se o código está bom)
        total += scrape_local_samples(db, driver)
        
        # 2. Depois vai para a internet real
        total += scrape_selenium_sites(db, driver)
        
    except Exception as e:
        print(f"Erro no Driver: {e}")
    finally:
        if driver: driver.quit()

    print(f"\n=== PROCESSO COMPLETO: {total} NOVAS VAGAS NO TOTAL ===")

def mock_scrape(db: Session):
    real_scrape(db)
