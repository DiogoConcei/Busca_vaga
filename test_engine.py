
import sys
import os

# Adiciona o diretório atual ao path para permitir imports relativos/locais
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.services.scraper_service import get_driver
    print("[+] Importação de get_driver bem-sucedida.")
except ImportError as e:
    print(f"[-] Erro ao importar get_driver: {e}")
    sys.exit(1)

def test_browser():
    driver = None
    try:
        print("[*] Tentando iniciar o driver Selenium...")
        driver = get_driver()
        print("[+] Driver iniciado com sucesso.")
        
        url_teste = "https://www.riovagas.com.br/"
        print(f"[*] Acessando {url_teste}...")
        driver.get(url_teste)
        
        title = driver.title
        print(f"[+] Título da página: {title}")
        
        if "RioVagas" in title:
            print("[SUCCESS] O motor de busca consegue acessar portais de vagas.")
        else:
            print("[WARNING] A página foi acessada, mas o título não contém 'RioVagas'. Verifique se houve bloqueio ou redirecionamento.")
            
    except Exception as e:
        print(f"[-] Erro durante a execução do teste: {e}")
    finally:
        if driver:
            print("[*] Fechando o driver...")
            driver.quit()

if __name__ == "__main__":
    test_browser()
