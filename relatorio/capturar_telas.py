"""Gera as capturas de tela dos 8 formulários para o relatório.
Uso: python relatorio/capturar_telas.py antes|depois [base] [arquivo_token]
(app rodando com TESTING=1 e seed aplicado; o token de redefinição de senha só existe no "depois")"""
import sys
from playwright.sync_api import sync_playwright

FASE = sys.argv[1]
BASE = sys.argv[2] if len(sys.argv) > 2 else 'http://127.0.0.1:5000'
TOKEN = open(sys.argv[3]).read().strip() if len(sys.argv) > 3 else ''
OUT = 'relatorio/img/'

INVALIDOS = {'email': 'abc', 'cep': '123', 'ddd': '8', 'celular': '9999', 'cnpj': '123', 'numero': 'dez',
             'senha': '123', 'senhaConfirmar': '321', 'idade': '40', 'data_nascimento': '2015-01-01'}
ONG_VALIDA = {'nome_Ong': 'ONG Duplicada', 'cnpj': '12345678000199', 'rua': 'Rua B', 'cep': '58400000',
              'numero': '20', 'ddd': '83', 'celular': '988887777', 'dados_bancarios': 'Banco 001 Ag 1 CC 2',
              'instagram': '@dup', 'email': 'ong@teste.com', 'senha': 'Senha123', 'senhaConfirmar': 'Senha123',
              'descricao_foto_perfil_Logo': 'Logo da ONG', 'descricao_fotoqrCode': 'QR code'}


def preencher(page, dados):
    for nome, valor in dados.items():
        campo = page.locator(f'[name="{nome}"]')
        if campo.count() and campo.first.get_attribute('type') not in ('radio', 'checkbox', 'file'):
            campo.first.fill(valor)


def enviar_sem_validacao_nativa(page):
    page.evaluate("document.querySelectorAll('form').forEach(f => f.noValidate = true)")
    page.locator('input[type=submit], button[type=submit]').first.click()
    page.wait_for_load_state()


def foto(page, nome):
    page.screenshot(path=f'{OUT}{FASE}_{nome}.png', full_page=True)


def login(page, email, senha):
    page.goto(f'{BASE}/logout')
    page.goto(f'{BASE}/login')
    page.fill('[name=email]', email)
    page.fill('[name=senha]', senha)
    page.locator('input[type=submit]').first.click()
    page.wait_for_load_state()


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/google-chrome')
    page = browser.new_page(viewport={'width': 1280, 'height': 900})

    page.goto(f'{BASE}/cadastro'); foto(page, 'usuario_vazio')
    preencher(page, INVALIDOS); enviar_sem_validacao_nativa(page); foto(page, 'usuario_erros')

    login(page, 'admin@teste.com', '123')
    page.goto(f'{BASE}/admin_dashboard/ongs_register'); foto(page, 'ong_vazio')
    preencher(page, INVALIDOS); enviar_sem_validacao_nativa(page); foto(page, 'ong_erros')
    page.goto(f'{BASE}/admin_dashboard/ongs_register')
    preencher(page, ONG_VALIDA); enviar_sem_validacao_nativa(page); foto(page, 'ong_email_duplicado')

    login(page, 'ong@teste.com', '123')
    page.goto(f'{BASE}/ong_dashboard/pets_register'); foto(page, 'animal_vazio')
    preencher(page, INVALIDOS); enviar_sem_validacao_nativa(page); foto(page, 'animal_erros')

    # telas de edição: dados atuais e envio com erros
    page.goto(f'{BASE}/ong_dashboard/pets_edit/4001'); foto(page, 'animal_editar')
    preencher(page, {**INVALIDOS, 'nome': ''}); enviar_sem_validacao_nativa(page); foto(page, 'animal_editar_erros')

    login(page, 'ana@teste.com', '123')
    page.goto(f'{BASE}/profile/edit'); foto(page, 'perfil_editar')
    preencher(page, INVALIDOS); enviar_sem_validacao_nativa(page); foto(page, 'perfil_editar_erros')

    # acesso: login, recuperar e redefinir senha
    page.goto(f'{BASE}/logout'); page.goto(f'{BASE}/login'); foto(page, 'login_vazio')
    preencher(page, {'email': 'ana@teste.com', 'senha': 'errada'}); enviar_sem_validacao_nativa(page); foto(page, 'login_erros')
    page.goto(f'{BASE}/recuperar'); foto(page, 'recuperar_vazio')
    preencher(page, INVALIDOS); enviar_sem_validacao_nativa(page); foto(page, 'recuperar_erros')
    page.goto(f'{BASE}/redefinir' + (f'?token={TOKEN}' if TOKEN else '')); foto(page, 'redefinir_vazio')
    preencher(page, INVALIDOS); enviar_sem_validacao_nativa(page); foto(page, 'redefinir_erros')
    browser.close()
