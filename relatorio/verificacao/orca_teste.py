"""Percorre os 8 formulários com Tab num Chrome visível enquanto o Orca roda; associa a fala registrada no log a cada passo."""
import json, os, re, sys, time
from playwright.sync_api import sync_playwright

LOG = sys.argv[1]; OUT = sys.argv[2]; BASE = 'http://127.0.0.1:5000'
passos = []


def fala_nova(desde):
    with open(LOG, encoding='utf-8', errors='replace') as f:
        f.seek(desde); txt = f.read()
    return re.findall(r"SPEECH OUTPUT: '(.*?)'", txt), os.path.getsize(LOG)


def passo(pg, desc, acao, espera=2.2):
    ini = os.path.getsize(LOG); acao(); time.sleep(espera)
    falas, _ = fala_nova(ini)
    foco = pg.evaluate("(() => { const e = document.activeElement; return (e.name || e.id || e.tagName) + (e.type ? ':' + e.type : ''); })()")
    passos.append(dict(passo=desc, foco=foco, fala=[f for f in falas if f.strip()]))


def percorrer(pg, nome, ate_submit=True):
    pg.focus('form.form-detail input:not([type=hidden])') if False else None
    passo(pg, f'{nome}: primeiro campo', lambda: pg.locator('form.form-detail input:not([type=hidden]), form.form-detail textarea').first.focus())
    for i in range(45):
        if pg.evaluate("document.activeElement.type") == 'date':
            # Tab automático dentro dos segmentos da data tirou o foco da janela na 1ª rodada: avança por foco programático
            passo(pg, f'{nome}: próximo após data', lambda: pg.evaluate('''(() => { const f = document.querySelector('form.form-detail');
                const els = [...f.querySelectorAll('input:not([type=hidden]),textarea,select,a,button')];
                els[els.indexOf(document.activeElement) + 1].focus(); })()'''), 1.8)
            continue
        pg.bring_to_front()
        passo(pg, f'{nome}: Tab {i+1}', lambda: pg.keyboard.press('Tab'), 1.8)
        if pg.evaluate("document.activeElement.type") == 'submit':
            break


ALVOS = {'Usuário': ['data_nascimento', 'foto_perfil', 'senha', 'declaracao'], 'ONG': ['senha', 'fotoPerfilLogo'],
         'Animal': ['especie-0', 'tamanho-0', 'status-0', 'castrado', 'foto1'],
         'Editar animal': ['especie-0', 'status-0', 'castrado', 'foto1'], 'Editar perfil': ['data_nascimento', 'foto_perfil', 'senha'],
         'Entrar': ['email', 'senha'], 'Recuperar senha': ['email'], 'Redefinir senha': ['senha', 'senhaConfirmar']}


def cadastro(pg, nome, url, invalidos):
    passo(pg, f'{nome}: carregar página', lambda: pg.goto(url), 4)
    percorrer(pg, nome)
    for n, v in invalidos.items():
        e = pg.locator(f'form.form-detail [name="{n}"]')
        if e.count(): e.first.fill(v)
    passo(pg, f'{nome}: enviar inválido', lambda: pg.locator('form.form-detail [type=submit]').click(), 5)
    passo(pg, f'{nome}: 1º link do resumo', lambda: pg.locator('.resumo-erros a').first.click(), 3)
    for i in range(3):
        passo(pg, f'{nome}: Tab após erro {i+1}', lambda: pg.keyboard.press('Tab'), 2.2)
    for alvo in ALVOS[nome]:
        passo(pg, f'{nome}: foco em {alvo} após erro', lambda: pg.focus(f'#{alvo}'), 2.2)


def login(pg, email):
    pg.goto(f'{BASE}/logout'); pg.goto(f'{BASE}/login')
    pg.fill('[name=email]', email); pg.fill('[name=senha]', '123')
    pg.locator('input[type=submit]').first.click(); pg.wait_for_load_state()


INV = {'cep': '123', 'email': 'abc', 'idade': '40', 'senha': '123', 'senhaConfirmar': '321'}
TOKEN = open('token_5000.txt').read().strip()
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=False,
                          args=['--force-renderer-accessibility', '--window-size=1280,900'])
    pg = b.new_page(locale='pt-BR'); pg.bring_to_front()
    cadastro(pg, 'Usuário', f'{BASE}/cadastro', INV)
    login(pg, 'admin@teste.com'); cadastro(pg, 'ONG', f'{BASE}/admin_dashboard/ongs_register', INV)
    login(pg, 'ong@teste.com'); cadastro(pg, 'Animal', f'{BASE}/ong_dashboard/pets_register', INV)
    cadastro(pg, 'Editar animal', f'{BASE}/ong_dashboard/pets_edit/4001', INV)
    login(pg, 'ana@teste.com'); cadastro(pg, 'Editar perfil', f'{BASE}/profile/edit', INV)
    pg.goto(f'{BASE}/logout')
    cadastro(pg, 'Entrar', f'{BASE}/login', INV)
    cadastro(pg, 'Recuperar senha', f'{BASE}/recuperar', INV)
    cadastro(pg, 'Redefinir senha', f'{BASE}/redefinir?token={TOKEN}', INV)
    b.close()
json.dump(passos, open(OUT, 'w'), ensure_ascii=False, indent=1)
print(len(passos), 'passos;', sum(1 for x in passos if x['fala']), 'com fala registrada')
