import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup
from ..models.vaga import Vaga, Curriculo
import time
import random
import requests
import os
import re
from collections import Counter
from urllib.parse import quote, urljoin

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
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
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
    """Configura o driver VISÍVEL com PERFIL PERSISTENTE para salvar logins."""
    browser_path = find_browser_executable()
    
    # Caminho para salvar o perfil (cookies, logins, etc)
    profile_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "selenium_profile")
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir)

    def get_options():
        options = uc.ChromeOptions()
        if browser_path:
            options.binary_location = browser_path
        
        # ESSENCIAL: Aponta para a pasta onde o login ficará salvo
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument("--profile-directory=Default")
        
        # User-Agent Realista para evitar logout imediato
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
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
                print(f"\n[!] Conflito de versão. Forçando driver {v_main}...")
                driver = uc.Chrome(options=get_options(), version_main=v_main, browser_executable_path=browser_path)
            else:
                raise e
        elif "user data directory is already in use" in error_msg.lower():
            print("\n[!] ERRO: O Chrome do bot já está aberto ou travado.")
            print("[!] Feche todas as janelas do Chrome abertas pelo bot e tente novamente.")
            raise e
        else:
            if not browser_path:
                print("\n[!] ERRO: Nenhum navegador Chromium encontrado!")
            raise e

    driver.set_window_size(1366, 768)
    return driver

def extract_keywords(text: str) -> str:
    """Extrai palavras-chave simples de um texto (ATS light)."""
    if not text: return ""
    words = re.findall(r'\w+', text.lower())
    stop_words = {'o', 'a', 'os', 'as', 'de', 'do', 'da', 'em', 'um', 'uma', 'e', 'com', 'para', 'que', 'se', 'do', 'da'}
    keywords = [w for w in words if len(w) > 3 and w not in stop_words]
    most_common = [w for w, count in Counter(keywords).most_common(15)]
    return ", ".join(most_common)

def calculate_semantic_score(job_text: str, resume_text: str) -> float:
    """Calcula a similaridade entre a vaga e o currículo usando TF-IDF (Local)."""
    if not job_text or not resume_text: return 0.0
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    try:
        vectorizer = TfidfVectorizer()
        tfidf = vectorizer.fit_transform([job_text, resume_text])
        similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])
        return float(similarity[0][0]) * 100
    except:
        return 0.0

def analyze_vaga_match(db: Session, titulo: str, localizacao: str = "", descricao: str = ""):
    """IA LOCAL OTIMIZADA com Match Heurístico e Semântico."""
    weights = {
        "stack_principal": 25, "stack_secundaria": 15, "area_foco": 10, "senioridade_alvo": 30,
    }
    techs_main = ["python", "react", "javascript", "js", "typescript", "ts"]
    techs_sec = ["sql", "fastapi", "node", "git", "css", "html", "docker", "aws", "nosql", "postgres"]
    areas = ["dados", "web", "dev", "software", "frontend", "backend", "fullstack", "computação"]
    target_seniority = ["estágio", "estagio", "intern", "trainee"]
    junior_seniority = ["junior", "jr", "júnior"]
    penalties = ["sênior", "senior", "pleno", "pl", "sr", "lead", "gerente", "manager", "especialista"]

    score = 20
    highlights = []
    title_lower = titulo.lower()
    
    # Heurística de Título
    if any(kw in title_lower for kw in target_seniority):
        score += weights["senioridade_alvo"]
        highlights.append("🎓 Estágio")
    elif any(kw in title_lower for kw in junior_seniority):
        score += weights["senioridade_alvo"] // 2
        highlights.append("🌱 Junior")

    found_main = [t for t in techs_main if t in title_lower]
    if found_main:
        score += weights["stack_principal"]
        highlights.extend([t.upper() for t in found_main[:2]])

    if any(kw in title_lower for kw in areas):
        score += weights["area_foco"]

    for p in penalties:
        if f" {p} " in f" {title_lower} " or title_lower.endswith(p):
            score -= 40

    # Match Semântico se tiver Currículo
    curriculos_ativos = db.query(Curriculo).filter(Curriculo.is_active == True).all()
    
    matching_profile = ""
    if curriculos_ativos and descricao:
        best_semantic_score = 0
        
        for curr in curriculos_ativos:
            s_score = calculate_semantic_score(descricao, curr.texto_extraido)
            if s_score > best_semantic_score:
                best_semantic_score = s_score
                matching_profile = curr.nome.split('.')[0] # Pega o nome sem extensão
        
        # 40% Título / 60% Descrição
        score = (score * 0.4) + (best_semantic_score * 0.6)
    elif curriculos_ativos:
        # Se não tem descrição para o match semântico, ainda tentamos identificar o perfil ativo principal
        matching_profile = curriculos_ativos[0].nome.split('.')[0]

    if matching_profile:
        # Insere o perfil no INÍCIO dos highlights para garantir visibilidade
        highlights.insert(0, f"👤 {matching_profile[:10]}...")

    score = max(0, min(score, 100))
    
    if score >= 80: insight_text = "🔥 Match de Elite! Perfil altamente compatível."
    elif score >= 60: insight_text = "⭐ Boa compatibilidade com seus requisitos."
    elif score >= 40: insight_text = "📈 Potencial detectado. Confira a descrição."
    else: insight_text = "🔍 Afinidade baixa identificada pela IA."
        
    # Aumentamos para 4 itens para não cortar o perfil
    return int(score), " • ".join(highlights[:4]) + " | " + insight_text

def get_full_description(driver, link: str, site_name: str) -> str:
    """Tenta navegar até o link da vaga e extrair o texto completo."""
    try:
        selectors = {
            "RioVagas": ".entry-content, .post-content",
            "Indeed": "#jobDescriptionText, .jobsearch-JobComponent-description",
            "Catho": ".job-description, [class*='JobDescription']",
            "LinkedIn": ".description__text, .show-more-less-html__markup"
        }
        
        # Para simplificar, o scraper vai tentar pegar a descrição quando já estiver no card (se possível)
        # ou fará uma navegação rápida se for Hot Match.
        try:
            element = driver.find_element(By.CSS_SELECTOR, selectors.get(site_name, "body"))
            return element.text.strip()
        except: return ""
    except: return ""

def scrape_selenium_sites(db: Session, driver):
    """Busca em camadas sequenciais para máxima precisão com expansão de termos."""
    vagas_novas = 0
    
    # Palavras-chave proibidas para evitar ruído não-tech
    FORBIDDEN_KEYWORDS = [
        "direito", "advogado", "jurídico", "administração", "adm", "vendas", 
        "telemarketing", "atendimento", "comercial", "psicologia", "pedagogia", 
        "jornalismo", "marketing", "financeiro", "contabilidade", "rh", 
        "recursos humanos", "culinária", "gastronomia", "enfermagem", "médico"
    ]

    # Configuração dos sites movida para dentro da função para evitar NameError
    config_sites = [
        {"name": "RioVagas", "base_url": "https://riovagas.com.br/?s={query}", "selectors": ["article h2 a"], "loc_selector": ".post-city"},
        {"name": "Indeed", "base_url": "https://br.indeed.com/jobs?q={query}&l=Rio+de+Janeiro%2C+RJ&sort=date", "selectors": ["h2.jobTitle a"], "loc_selector": ".companyLocation"},
        {"name": "Catho", "base_url": "https://www.catho.com.br/vagas/{query_slug}-rj/?q={query_encoded}", "selectors": ["h2 a"], "loc_selector": ".sc-kgOKUu a"},
        {"name": "LinkedIn", "base_url": "https://www.linkedin.com/jobs/search?keywords={query_encoded}&location=Rio%20de%20Janeiro%2C%20Brasil", "selectors": ["h3.base-search-card__title, .job-search-card__title, h4.base-search-card__title"], "loc_selector": ".job-search-card__location"}
    ]

    # Termos base
    base_termos = ["estagio python", "estagio desenvolvimento", "estagio dados", "estagio react"]
    
    # Expansão de Sinônimos para o Scraper
    expansao = {
        "python": ["py", "django", "fastapi", "flask"],
        "dados": ["data", "sql", "bi", "analytics"],
        "desenvolvimento": ["dev", "software", "web", "programador"],
        "react": ["frontend", "front", "js", "javascript"]
    }

    # Gera lista final de termos (Base + 1 variação aleatória de cada para diversificar)
    termos_finais = list(base_termos)
    for b in base_termos:
        for k, v in expansao.items():
            if k in b:
                termos_finais.append(b.replace(k, random.choice(v)))
    
    # Remove duplicatas mantendo a ordem
    termos_finais = list(dict.fromkeys(termos_finais))

    for termo in termos_finais:
        print(f"\n[🔍] BUSCA AMPLIADA: {termo.upper()}")
        area_vaga = termo.split()[-1].capitalize()
        for site in config_sites:
            try:
                print(f"   -> Pesquisando no {site['name']}...")
                url = site['base_url'].format(query=termo, query_encoded=quote(termo), query_slug=termo.replace(" ", "-"))
                driver.get(url)
                time.sleep(random.uniform(5, 7))

                items = driver.find_elements(By.CSS_SELECTOR, site['selectors'][0])
                num_encontrados = len(items)
                print(f"      [i] {num_encontrados} elementos de vaga detectados.")
                
                vagas_site_count = 0
                for index, item in enumerate(items[:15]): # Aumentado para 15 para maior cobertura
                    try:
                        title = item.text.strip()
                        link = item.get_attribute("href")
                        
                        if not title or not link:
                            continue
                        
                        # FILTRO DE RUÍDO: Ignorar se contiver palavras proibidas
                        if any(fk in title.lower() for fk in FORBIDDEN_KEYWORDS):
                            # print(f"      [!] Pulando Ruído: {title[:30]}...")
                            continue

                        clean_link = link.split('?')[0]
                        existing_vaga = db.query(Vaga).filter(Vaga.link == clean_link).first()
                        
                        if not existing_vaga:
                            # Se for um Hot Match provável, pegamos a descrição
                            desc = ""
                            if site['name'] == "RioVagas":
                                try: desc = item.find_element(By.XPATH, "./ancestor::article").text
                                except: pass
                            
                            score, insight = analyze_vaga_match(db, title, "", desc)
                            db.add(Vaga(
                                titulo=title, empresa=site['name'], link=clean_link,
                                localizacao="RJ", area=area_vaga, status="Novo",
                                match_score=score, insights=insight, 
                                descricao_completa=desc, keywords_ats=extract_keywords(desc)
                            ))
                            db.commit()
                            vagas_novas += 1
                            vagas_site_count += 1
                            print(f"      [{index+1}/{min(num_encontrados, 15)}] [+] NOVA: {title[:40]}... | Match: {score}%")
                        else:
                            print(f"      [{index+1}/{min(num_encontrados, 15)}] [-] Repetida: {title[:30]}...")
                            
                    except Exception as e:
                        # print(f"      [!] Erro no item {index+1}: {e}")
                        continue
                
                if vagas_site_count == 0 and num_encontrados > 0:
                    print(f"      [✓] Todos os resultados do {site['name']} já estavam no banco.")
            except Exception as e:
                print(f"   [!] Erro crítico no site {site['name']}: {e}")
                continue
    return vagas_novas

# Outras funções (GitHub, Amostras, Real_Scrape) permanecem similares, mas adaptadas
def scrape_github(db: Session):
    vagas_novas = 0
    repos = ["backend-br/vagas", "frontendbr/vagas", "pythonbrasil/vagas"]
    keywords = ["estágio", "estagio", "intern", "junior"]
    print("[GitHub] Verificando...")
    for repo in repos:
        try:
            res = requests.get(f"https://api.github.com/repos/{repo}/issues?state=open", timeout=10)
            if res.status_code == 200:
                for issue in res.json():
                    title = issue['title']
                    link = issue['html_url']
                    desc = issue.get('body', "")
                    if any(kw in title.lower() for kw in keywords):
                        if not db.query(Vaga).filter(Vaga.link == link).first():
                            score, insight = analyze_vaga_match(db, title, "Remoto", desc)
                            db.add(Vaga(
                                titulo=title, empresa="GitHub", link=link, localizacao="Remoto",
                                area="Comunidade", status="Novo", match_score=score, insights=insight,
                                descricao_completa=desc[:2000], keywords_ats=extract_keywords(desc)
                            ))
                            vagas_novas += 1
                db.commit()
        except: continue
    return vagas_novas

def real_scrape(db: Session):
    total = scrape_github(db)
    driver = None
    try:
        driver = get_driver()
        total += scrape_selenium_sites(db, driver)
    except Exception as e: print(f"Erro: {e}")
    finally:
        if driver: driver.quit()
    return total
