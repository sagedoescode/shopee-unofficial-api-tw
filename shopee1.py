import requests
import json
import pandas as pd
from bs4 import BeautifulSoup
import sys
from time import sleep

# Configuração da API ScrapingAnt
API_TOKEN = "9554373bed744de08e57c1fcb25c8b59"  # Use seu token da ScrapingAnt
BASE_URL = "https://api.scrapingant.com/v2/general"


def fetch_page(url, use_browser=True):
    """Faz uma requisição para a API ScrapingAnt e retorna o conteúdo da página"""
    params = {
        'url': url,
        'x-api-key': API_TOKEN,
        'browser': 'true' if use_browser else 'false',
    }

    try:
        response = requests.get(BASE_URL, params=params)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Erro na requisição: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Erro ao acessar a API: {str(e)}")
        return None


def extract_product_details(product_url):
    """Extrai os detalhes de um produto da Shopee (funciona com qualquer domínio da Shopee)"""
    print(f"Extraindo dados do produto: {product_url}")
    html_content = fetch_page(product_url)

    if not html_content:
        return None

    soup = BeautifulSoup(html_content, 'html.parser')

    # Detectar domínio
    domain = "shopee"
    if "shopee.tw" in product_url:
        print("Detectado: Shopee Taiwan")
        domain = "shopee.tw"
    elif "shopee.com.br" in product_url:
        print("Detectado: Shopee Brasil")
        domain = "shopee.com.br"

    # Extrair informações do produto
    try:
        # Tentar vários seletores possíveis para cada elemento
        # Esses seletores são uma combinação que deve funcionar em diferentes domínios

        # Nome do produto
        name_selectors = [
            '.product-briefing .qaNIZv',
            '.attM6y span',
            'h1.product-detail__name',
            '.page-product__title',
            '.product-briefing h1',
            '.product-detail-page__header__name',
            '.PVuNPp'
        ]

        name = None
        for selector in name_selectors:
            name_elem = soup.select_one(selector)
            if name_elem:
                name = name_elem.text.strip()
                break

        # Preço
        price_selectors = [
            '.product-briefing .Ybrg9j',
            '.AJyN7v',
            '.product-detail__price',
            '.page-product__detail .product-detail__price',
            '.price-container .price',
            '._22ilFY',
            '._1v8Ixb'
        ]

        price = None
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price = price_elem.text.strip()
                break

        # Avaliações (rating)
        rating_selectors = [
            '.product-rating-overview__rating-score',
            '.product-rating__rating-score',
            '.rating-with-count__rating',
            '._1mYa1t',
            '.HlRyAJ'
        ]

        rating = None
        for selector in rating_selectors:
            rating_elem = soup.select_one(selector)
            if rating_elem:
                rating = rating_elem.text.strip()
                break

        # Vendedor
        seller_selectors = [
            '.seller-name-wrapper .seller-name__text',
            '.seller-name__wrapper .seller-name__text',
            '.product-detail__seller-name',
            '.seller-info-content__name',
            '._3uf2ae',
            '.hVzXS4'
        ]

        seller = None
        for selector in seller_selectors:
            seller_elem = soup.select_one(selector)
            if seller_elem:
                seller = seller_elem.text.strip()
                break

        # Quantidade vendida
        sold_count_selectors = [
            '.product-detail__sold-count',
            '.wGBjtA',
            '.Efpd3B',
            '.item-status__text',
            '._22sp0A',
            '.kHGNrE'
        ]

        sold_count = None
        for selector in sold_count_selectors:
            sold_elem = soup.select_one(selector)
            if sold_elem:
                sold_count = sold_elem.text.strip()
                break

        # Descrição
        description_selectors = [
            '.product-detail__description-content',
            '.kIUnrY',
            '.page-product__detail .product-detail__description',
            '.product-detail__description',
            '.f7AU53',
            '._1Qtf7G'
        ]

        description = None
        for selector in description_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                description = desc_elem.text.strip()
                break

        # Obter imagens
        image_selectors = [
            '.product-detail__gallery img',
            '.XBKtMI img',
            '.page-product__detail .product-detail__gallery img',
            '.product-briefing img[src]',
            '.dR8kXc img',
            '.PTr7E- img'
        ]

        images = []
        for selector in image_selectors:
            image_containers = soup.select(selector)
            if image_containers:
                images = [img.get('src') for img in image_containers if img.has_attr('src')]
                if images:
                    break

        # Obter especificações
        specs = {}
        spec_selectors = [
            '.product-detail__specification-table tbody tr',
            '.page-product__detail .product-detail__specs-table tr',
            '.kIUnrY table tr',
            '.product-detail__attributes div',
            '.bQVbQH',
            '.dR8kXc'
        ]

        for selector in spec_selectors:
            spec_items = soup.select(selector)
            if spec_items:
                for item in spec_items:
                    # Tentar extrair como tabela
                    key_elem = item.select_one('td:nth-child(1), th:nth-child(1)')
                    value_elem = item.select_one('td:nth-child(2), th:nth-child(2)')

                    # Se não encontrar como tabela, tentar como div
                    if not key_elem or not value_elem:
                        label_elem = item.select_one('label, span:nth-child(1)')
                        value_elem = item.select_one('div:nth-child(2), span:nth-child(2)')

                    if key_elem and value_elem:
                        specs[key_elem.text.strip()] = value_elem.text.strip()
                    elif label_elem and value_elem:
                        specs[label_elem.text.strip()] = value_elem.text.strip()

                if specs:
                    break

        # Extrair avaliações
        reviews = []
        review_selectors = [
            '.shopee-product-rating',
            '.product-rating',
            '.page-product__detail .product-ratings__list-item',
            '.rating-comment-container',
            '._14DAT_',
            '.EXI9SU'
        ]

        for selector in review_selectors:
            review_items = soup.select(selector)
            if review_items:
                for j, review in enumerate(review_items):
                    if j >= 5:  # Limitar a 5 avaliações
                        break

                    reviewer_selectors = [
                        '.shopee-product-rating__author-name',
                        '.rating-author__name',
                        '.username',
                        '._7wHgNd',
                        '.SbCpSo'
                    ]

                    rating_selectors = [
                        '.shopee-product-rating__rating',
                        '.rating-stars',
                        '.rating-stars__stars',
                        '._1Bj6iq',
                        '.OALo0B'
                    ]

                    comment_selectors = [
                        '.shopee-product-rating__content',
                        '.rating-comment',
                        '.comment',
                        '._3F1-5M',
                        '.CUDGNS'
                    ]

                    reviewer = None
                    for sel in reviewer_selectors:
                        elem = review.select_one(sel)
                        if elem:
                            reviewer = elem.text.strip()
                            break

                    rating = None
                    for sel in rating_selectors:
                        elem = review.select_one(sel)
                        if elem:
                            rating = elem.get('aria-label') or elem.text.strip()
                            break

                    comment = None
                    for sel in comment_selectors:
                        elem = review.select_one(sel)
                        if elem:
                            comment = elem.text.strip()
                            break

                    if reviewer or comment:
                        reviews.append({
                            'reviewer': reviewer or 'Anônimo',
                            'rating': rating or 'N/A',
                            'comment': comment or 'N/A'
                        })

                if reviews:
                    break

        # Consolidar dados
        product_data = {
            'url': product_url,
            'nome': name or 'N/A',
            'preco': price or 'N/A',
            'avaliacao': rating or 'N/A',
            'vendedor': seller or 'N/A',
            'vendidos': sold_count or 'N/A',
            'descricao': description or 'N/A',
            'imagens': images,
            'especificacoes': specs,
            'avaliacoes': reviews
        }

        return product_data

    except Exception as e:
        print(f"Erro ao extrair detalhes do produto: {str(e)}")
        return None


def save_product_data(product_data, output_file=None):
    """Salva os dados do produto em CSV e JSON"""
    if not product_data:
        print("Nenhum dado de produto para salvar.")
        return

    # Criar nome de arquivo a partir do nome do produto se não for especificado
    if not output_file:
        product_name = product_data['nome']
        if product_name and product_name != 'N/A':
            # Limitar o tamanho e remover caracteres inválidos para nome de arquivo
            safe_name = ''.join(c if c.isalnum() or c in ' -_' else '_' for c in product_name)
            safe_name = safe_name[:30].strip()  # Limitar tamanho
            output_file = f"{safe_name}.csv"
        else:
            output_file = "produto_shopee.csv"

    # Garantir que o arquivo termina com .csv
    if not output_file.lower().endswith('.csv'):
        output_file += '.csv'

    # Criar DataFrame com dados básicos
    df = pd.DataFrame([{
        'URL': product_data['url'],
        'Nome': product_data['nome'],
        'Preço': product_data['preco'],
        'Avaliação': product_data['avaliacao'],
        'Vendedor': product_data['vendedor'],
        'Vendidos': product_data['vendidos'],
        'Descrição': product_data['descricao'][:200] + '...' if len(product_data['descricao']) > 200 else product_data[
            'descricao']
    }])

    # Salvar em CSV
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"Dados básicos salvos em {output_file}")

    # Salvar especificações em CSV separado
    if product_data['especificacoes']:
        specs_file = output_file.replace('.csv', '_specs.csv')
        specs_df = pd.DataFrame([{'Atributo': k, 'Valor': v} for k, v in product_data['especificacoes'].items()])
        specs_df.to_csv(specs_file, index=False, encoding='utf-8-sig')
        print(f"Especificações salvas em {specs_file}")

    # Salvar avaliações em CSV separado
    if product_data['avaliacoes']:
        reviews_file = output_file.replace('.csv', '_reviews.csv')
        reviews_df = pd.DataFrame(product_data['avaliacoes'])
        reviews_df.to_csv(reviews_file, index=False, encoding='utf-8-sig')
        print(f"Avaliações salvas em {reviews_file}")

    # Salvar dados completos em JSON
    json_file = output_file.replace('.csv', '.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(product_data, f, ensure_ascii=False, indent=2)

    print(f"Dados completos salvos em {json_file}")

    # Exibir um resumo dos dados extraídos
    print("\n--- RESUMO DO PRODUTO ---")
    print(f"Nome: {product_data['nome']}")
    print(f"Preço: {product_data['preco']}")
    print(f"Avaliação: {product_data['avaliacao']}")
    print(f"Vendedor: {product_data['vendedor']}")
    print(f"Vendidos: {product_data['vendidos']}")
    print(f"Especificações: {len(product_data['especificacoes'])} itens")
    print(f"Avaliações: {len(product_data['avaliacoes'])} comentários")
    print(f"Imagens: {len(product_data['imagens'])} encontradas")


def main():
    # Se nenhum argumento for fornecido, solicitar a URL do produto
    if len(sys.argv) < 2:
        product_url = input("Digite a URL do produto da Shopee: ").strip()
    else:
        product_url = sys.argv[1].strip()

    # Verificar se a URL é válida
    if not product_url.startswith('http'):
        print("URL inválida. Certifique-se de fornecer uma URL completa começando com http:// ou https://")
        return

    # Verificar se é uma URL da Shopee
    if not ('shopee.' in product_url):
        print("A URL fornecida não parece ser da Shopee. Este script é específico para a Shopee.")
        continue_anyway = input("Deseja continuar mesmo assim? (s/n): ").strip().lower()
        if continue_anyway != 's':
            return

    # Extrair os dados do produto
    product_data = extract_product_details(product_url)

    if product_data:
        # Se houver mais de um argumento, o segundo é o nome do arquivo de saída
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        save_product_data(product_data, output_file)
    else:
        print("Não foi possível extrair os dados do produto.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário.")
    except Exception as e:
        print(f"\nErro inesperado: {str(e)}")

    input("\nPressione Enter para sair...")