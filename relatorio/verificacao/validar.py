"""Validação independente dos requisitos R01–R28 no navegador (app em 127.0.0.1:5000, TESTING=1, seed aplicado)."""
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5000'
import os; TOKEN = 'token_5000.txt'
res = {}  # id -> lista de (form, ok, detalhe)


def reg(rid, form, ok, det=''):
    res.setdefault(rid, []).append((form, bool(ok), det))


JS_INFO = r"""() => {
  const f = document.querySelector('form.form-detail');
  const ctrls = [...f.querySelectorAll('input,select,textarea')].filter(e => !['hidden','submit'].includes(e.type) && e.name !== 'g-recaptcha-response');
  const labelOf = e => {
    if (e.type === 'radio') { const fs = e.closest('fieldset.grupo-radio'); return fs ? fs.querySelector('legend').textContent : null; }
    const l = e.id && f.querySelector(`label[for="${e.id}"]`) || e.closest('label'); return l ? l.textContent : null; };
  const names = [...new Set(ctrls.map(e => e.name))];
  return {
    novalidate: f.noValidate,
    h1: (document.querySelector('h1') || {}).textContent || '',
    title: document.title,
    legends: [...f.querySelectorAll('fieldset:not(.grupo-radio) > legend')].map(l => l.textContent.trim()),
    groupOf: Object.fromEntries(names.map(n => { const e = f.querySelector(`[name="${n}"]`);
        const fs = e.closest('fieldset:not(.grupo-radio)'); return [n, fs ? fs.querySelector('legend').textContent.trim() : null]; })),
    order: names,
    fields: names.map(n => { const els = [...f.querySelectorAll(`[name="${n}"]`)]; const e = els[0];
        const lab = (labelOf(e) || '').replace(/\s+/g, ' ').trim();
        const desc = (e.getAttribute('aria-describedby') || (e.closest('fieldset.grupo-radio') || {getAttribute:()=>null}).getAttribute('aria-describedby') || '');
        return {name: n, type: e.type === 'select-one' ? 'select' : e.tagName === 'TEXTAREA' ? 'textarea' : e.type,
          label: lab, required: els.some(x => x.required), star: lab.includes('*'), readonly: e.readOnly,
          maxlength: e.maxLength, inputmode: e.inputMode, desc,
          ajuda: desc.split(' ').filter(Boolean).map(id => (document.getElementById(id)||{}).textContent || '').join(' | '),
          invalid: e.getAttribute('aria-invalid'), cls: e.className, value: e.type==='radio' ? (els.find(x=>x.checked)||{}).value : e.value}; }),
    legenda: !!document.querySelector('.legenda-obrigatorio'),
    resumo: (document.querySelector('.resumo-erros') || {}).innerText || '',
    links: [...document.querySelectorAll('.resumo-erros a')].map(a => a.getAttribute('href').slice(1)),
    errosTexto: [...document.querySelectorAll('.error')].map(e => e.innerText).join(' | '),
    footer: getComputedStyle(document.querySelector('footer')).position,
    cancelar: !!document.querySelector('.acoes-form a.botao-secundario'),
    submitBg: getComputedStyle(f.querySelector('[type=submit]')).backgroundColor,
    contexto: (document.querySelector('.contexto-form') || {}).textContent || '',
  }; }"""

INVALIDOS = {'email': 'abc', 'cep': '123', 'ddd': '8', 'celular': '9999', 'cnpj': '123', 'numero': 'dez',
             'senha': '123', 'senhaConfirmar': '321', 'idade': '40', 'data_nascimento': '2015-01-01',
             'primeiroNome': 'Teste Preservado', 'nome_Ong': 'Teste Preservado', 'nome': 'Teste Preservado'}


def preencher(pg, d):
    for n, v in d.items():
        e = pg.locator(f'form.form-detail [name="{n}"]')
        if e.count() and e.first.get_attribute('type') not in ('radio', 'checkbox', 'file'):
            e.first.fill(v)


def foco_visivel(pg, seletor):
    pg.focus(seletor)  # foco programático não ativa :focus-visible; usar teclado
    pg.keyboard.press('Shift+Tab'); pg.keyboard.press('Tab')
    return pg.evaluate("""() => { const s = getComputedStyle(document.activeElement);
        return {el: document.activeElement.name || document.activeElement.className, style: s.outlineStyle, w: parseFloat(s.outlineWidth)}; }""")


CADASTROS = ('Usuário', 'ONG', 'Animal')


def avaliar(pg, nome, url):
    pg.goto(url); v = pg.evaluate(JS_INFO)
    F = {f['name']: f for f in v['fields']}
    if nome in CADASTROS:
        reg('R00', nome, len(F) >= 15, f'{len(F)} campos')
    # formulários curtos (até 3 campos) têm um único grupo
    reg('R01', nome, len(v['legends']) >= (2 if len(F) > 3 else 1) and all(v['groupOf'].values()), f"grupos: {v['legends']}")
    if 'email' in F and 'senha' in F:
        reg('R01', nome, 'acesso' in v['groupOf']['email'].lower() and 'acesso' in v['groupOf']['senha'].lower(), 'e-mail/senha em "Dados de acesso"')
    if 'instagram' in F:
        reg('R01', nome, v['groupOf']['instagram'] == 'Contato', 'Instagram em Contato')
    reg('R02', nome, nome.lower() in v['h1'].lower() and nome.lower() in v['title'].lower(), f"h1='{v['h1']}' title='{v['title']}'")
    if 'cep' in F:
        o = v['order']; reg('R03', nome, o.index('cep') < o.index('numero') < o.index('rua') < o.index('complemento'), 'CEP→número→rua→complemento')
    # R04: rótulos alinhados à mesma margem esquerda dentro de cada coluna
    xs = pg.evaluate("""() => [...document.querySelectorAll('form.form-detail .campo > label, form.form-detail .grupo-radio > legend')]
        .filter(l => l.offsetParent).map(l => Math.round(l.getBoundingClientRect().left))""")
    reg('R04', nome, len(set(xs)) <= 2, f'margens esquerdas distintas dos rótulos: {sorted(set(xs))}')
    reg('R05', nome, v['footer'] != 'fixed', f"footer position={v['footer']}")
    sem = [f['name'] for f in v['fields'] if not f['label']]
    reg('R06', nome, not sem, f'sem rótulo: {sem}')
    labs = ' '.join(f['label'] for f in v['fields'])
    reg('R07', nome, 'Email' not in labs and 'Confirmar Senha' not in labs, 'terminologia "E-mail"/"Confirmar senha"')
    if 'idade' in F:
        reg('R08', nome, 'anos' in F['idade']['label'], F['idade']['label'])
    erradas = [f['name'] for f in v['fields'] if f['required'] != f['star']]
    reg('R09', nome, v['legenda'] and not erradas, f'obrigatório x asterisco divergentes: {erradas}')
    fmt = [n for n in ('cep', 'ddd', 'celular', 'cnpj', 'numero', 'idade', 'data_nascimento') if n in F]
    sem_ajuda = [n for n in fmt if not F[n]['ajuda'].strip()]
    reg('R10', nome, not sem_ajuda, f'campos de formato sem ajuda: {sem_ajuda}')
    sem_max = [f['name'] for f in v['fields'] if f['type'] in ('text', 'email', 'tel', 'textarea') and f['maxlength'] <= 0]
    reg('R11', nome, not sem_max, f'sem maxlength: {sem_max}')
    reg('R12', nome, not any(f['readonly'] for f in v['fields']), 'nenhum campo readonly como entrada')
    for n in ('especie', 'tamanho', 'status'):
        if n in F: reg('R13', nome, F[n]['type'] == 'radio', f'{n}={F[n]["type"]}')
    if nome in ('Usuário', 'Animal', 'Editar animal'):
        reg('R14', nome, any(f['type'] == 'checkbox' for f in v['fields']), 'caixa de seleção binária')
    reg('R15', nome, v['cancelar'] and v['submitBg'] not in ('rgb(255, 255, 255)', 'rgba(0, 0, 0, 0)'), f"Cancelar={v['cancelar']} fundo do botão={v['submitBg']}")
    esperado = {'email': 'email', 'ddd': 'tel', 'celular': 'tel', 'data_nascimento': 'date', 'idade': 'number'}
    ruins = [n for n, t in esperado.items() if n in F and F[n]['type'] != t]
    ruins += [n for n in ('cep', 'cnpj', 'numero') if n in F and F[n]['inputmode'] != 'numeric']
    reg('R16', nome, not ruins, f'tipo/teclado inadequado: {ruins}')
    if 'status' in F:
        reg('R17', nome, F['status']['value'] == 'disponível', f"status padrão={F['status']['value']}")
    if 'descricao_fotoqrCode' in F:
        reg('R17', nome, 'Se ficar vazio' in F['descricao_fotoqrCode']['ajuda'], 'padrão do QR code anunciado e editável')
    if nome in ('Animal', 'Editar animal'):
        reg('R18', nome, 'ONG Teste' in v['contexto'], v['contexto'])
    if nome == 'Editar animal':
        reg('R18', nome, F['nome']['value'] == 'Tico' and F['especie']['value'] == 'gato', 'dados atuais do animal preenchidos')
    if nome == 'Editar perfil':
        reg('R18', nome, F['primeiroNome']['value'] == 'Ana' and F['cep']['value'] == '58400000', 'dados atuais do perfil preenchidos')
    if nome == 'Redefinir senha':
        reg('R18', nome, 'ana@teste.com' in v['contexto'], 'e-mail vem do link, não é redigitado')
    if 'senha' in F and nome != 'Entrar':
        reg('R20', nome, 'mínimo' in F['senha']['ajuda'].lower(), F['senha']['ajuda'])
    fotos = [n for n in F if n.startswith('descricao_foto')]
    reg('R20', nome, all('leitor de tela' in F[n]['ajuda'] or 'QR code' in F[n]['ajuda'] for n in fotos), 'propósito das descrições de imagem')
    # R27 foco visível (via teclado) em campo de texto, rádio/checkbox e Cancelar
    for sel in ['form.form-detail input[type=text]', 'form.form-detail input[type=email]', 'form.form-detail input[type=radio]', 'form.form-detail input[type=checkbox]', '.acoes-form a']:
        if pg.locator(sel).count():
            fv = foco_visivel(pg, sel)
            reg('R27', nome, fv['style'] != 'none' and fv['w'] >= 2, f"{sel.split()[-1]}: outline {fv['style']} {fv['w']}px")

    # envio inválido (sem validação nativa: o form tem novalidate)
    reg('R22', nome, v['novalidate'], 'novalidate ativo (todos os erros do servidor visíveis)')
    preencher(pg, INVALIDOS)
    pg.locator('form.form-detail [type=submit]').click(); pg.wait_for_load_state()
    e = pg.evaluate(JS_INFO); E = {f['name']: f for f in e['fields']}
    ingles = [w for w in ('Not a valid', 'This field', 'Invalid', 'required.') if w in e['resumo'] + e['errosTexto']]
    reg('R21', nome, not ingles and e['errosTexto'], f'termos em inglês: {ingles}')
    com_erro = [n for n in E if f'{E[n]["name"]}-erro' in E[n]['desc'] or (E[n]['type']=='radio' and E[n]['desc'] and 'erro' in E[n]['desc'])]
    sem_destaque = [n for n in com_erro if E[n]['type'] not in ('radio', 'checkbox') and (E[n]['invalid'] != 'true' or 'campo-invalido' not in E[n]['cls'])]
    reg('R22', nome, com_erro and not sem_destaque, f'{len(com_erro)} campos com erro; sem destaque/aria-invalid: {sem_destaque}')
    reg('R23', nome, e['resumo'].startswith('Corrija') and len(e['links']) == len(com_erro), f"resumo com {len(e['links'])} links para {len(com_erro)} campos com erro")
    preservado = {n: INVALIDOS[n] for n in ('primeiroNome', 'nome_Ong', 'nome', 'email') if n in E}
    reg('R24', nome, all(E[n]['value'] == x for n, x in preservado.items()) and ('novamente' in e['resumo'] or not any(f['type'] in ('password', 'file') for f in e['fields'])),
        f'preservados {list(preservado)} + aviso de reenvio de fotos/senha')
    # R28: cada link do resumo leva o foco ao campo (ou grupo de rádio)
    falhos = []
    for alvo in e['links']:
        pg.click(f'.resumo-erros a[href="#{alvo}"]')
        if pg.evaluate('document.activeElement.id') != alvo: falhos.append(alvo)
    reg('R28', nome, e['links'] and not falhos, f'links que não focam o campo: {falhos}')


def login(pg, email):
    pg.goto(f'{BASE}/logout'); pg.goto(f'{BASE}/login')
    pg.fill('[name=email]', email); pg.fill('[name=senha]', '123')
    pg.locator('input[type=submit]').first.click(); pg.wait_for_load_state()


with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome')
    pg = b.new_page(viewport={'width': 1280, 'height': 900}, locale='pt-BR')
    avaliar(pg, 'Usuário', f'{BASE}/cadastro')
    login(pg, 'admin@teste.com'); avaliar(pg, 'ONG', f'{BASE}/admin_dashboard/ongs_register')
    login(pg, 'ong@teste.com'); avaliar(pg, 'Animal', f'{BASE}/ong_dashboard/pets_register')
    avaliar(pg, 'Editar animal', f'{BASE}/ong_dashboard/pets_edit/4001')
    login(pg, 'ana@teste.com'); avaliar(pg, 'Editar perfil', f'{BASE}/profile/edit')
    pg.goto(f'{BASE}/logout')
    avaliar(pg, 'Entrar', f'{BASE}/login')
    avaliar(pg, 'Recuperar senha', f'{BASE}/recuperar')
    avaliar(pg, 'Redefinir senha', f'{BASE}/redefinir?token=' + open(TOKEN).read().strip())
    # R26: mensagem de login aparece já na página do usuário (user_layout) — conferido pela presença do include
    b.close()

falhas = 0
for rid in sorted(res):
    itens = res[rid]; ok = all(o for _, o, _ in itens); falhas += not ok
    print(f"{rid} {'OK   ' if ok else 'FALHA'}  " + ' ; '.join(f"{f}: {'ok' if o else 'X'} ({d})" for f, o, d in itens))
print(f'\n{len(res)} requisitos verificados no navegador, {falhas} com falha')
