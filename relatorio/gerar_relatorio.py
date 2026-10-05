"""Gera relatorio/Relatorio_ISO9241-17_PetMatch.docx no padrão ABNT (NBR 14724, 6023, 6024, 6027, 6028, 10520).
O sumário e as listas usam duas passagens: a 1ª é convertida em PDF (LibreOffice) para localizar as páginas.
Uso (na raiz do projeto): python relatorio/gerar_relatorio.py
As tabelas de campos são extraídas dos próprios formulários: o "antes" vem de config/forms.py no commit BASE."""
import os
import subprocess
import sys
import types

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

sys.path.insert(0, '.')
BASE = '5d7d6fa'
IMG = 'relatorio/img/'
SAIDA = 'relatorio/Relatorio_ISO9241-17_PetMatch.docx'

from app import app, db  # noqa: E402
import config.forms as forms_depois  # noqa: E402

# ---------- extração dos campos (antes = commit BASE, depois = código atual) ----------
forms_antes = types.ModuleType('forms_antes')
exec(subprocess.check_output(['git', 'show', f'{BASE}:config/forms.py'], text=True), forms_antes.__dict__)

CADASTROS = [('Usuário', 'cadastroForm'), ('ONG', 'cadastrar_OngForm'), ('Animal', 'AnimalForm')]
OUTROS = [('Editar perfil', 'editPerfilForm1'), ('Editar animal', 'editAnimalForm'), ('Entrar', 'loginForm'),
          ('Recuperar senha', 'sendLinkForm'), ('Redefinir senha', 'ResetPasswordForm')]


def tipo_html(field):
    if field.type == 'RadioField':
        return 'radio'
    if field.type == 'SelectField':
        return 'select'
    if field.type == 'TextAreaField':
        return 'textarea'
    if field.type == 'RecaptchaField':
        return 'reCAPTCHA'
    return getattr(field.widget, 'input_type', None) or field.type


def campos(modulo, classe):
    with app.test_request_context():
        db.create_all()  # o editAnimalForm original consulta usuários ao ser criado
        form = getattr(modulo, classe)(meta={'csrf': False})
        return [(f.name, f.label.text, tipo_html(f), bool(f.flags.required)) for f in form
                if f.type not in ('SubmitField', 'CSRFTokenField', 'HiddenField')]


ANTES = {nome: campos(forms_antes, c) for nome, c in CADASTROS}
DEPOIS = {nome: campos(forms_depois, c) for nome, c in CADASTROS}
ANTES_O = {nome: campos(forms_antes, c) for nome, c in OUTROS}
DEPOIS_O = {nome: campos(forms_depois, c) for nome, c in OUTROS}

# ---------- checklist ISO 9241-17 ----------
# (id, cláusula de referência, requisito, situação antes, evidência antes, correção aplicada)
# Situação depois = Conforme para todos os itens aplicáveis (verificado nas capturas e em test_forms.py).
NC, P, C, NA = 'Não conforme', 'Parcial', 'Conforme', 'N.A. (não existia)'
CHECKLIST = [
    ('R01', '5 Estrutura – organização', 'Campos relacionados agrupados logicamente e com título de grupo.', NC,
     'E-mail e senha dentro de "Informações de Contato" (usuário); Instagram em "Informações Bancárias" (ONG); grupos só com <h2>, sem relação semântica.',
     'Grupos <fieldset>/<legend>: Dados pessoais, Endereço, Contato, Doações, Dados de acesso.'),
    ('R02', '5 Estrutura – organização', 'Formulário identificado por título claro.', NC,
     'Páginas abrem com "Informações Gerais"/"Informações do Animal"; nenhum título diz qual cadastro é.',
     'Título <h1> "Cadastro de usuário / de ONG / de animal" e <title> correspondente.'),
    ('R03', '5 Estrutura – organização', 'Ordem dos campos segue a sequência natural de preenchimento.', P,
     'Endereço começa pela rua e o CEP vem depois; credenciais misturadas com contato.',
     'Endereço na ordem CEP → número → rua → complemento; credenciais e declaração ao final.'),
    ('R04', '5 Estrutura – layout', 'Alinhamento e espaçamento consistentes entre rótulos e campos.', NC,
     'Recuo de 60 px só nos campos em linha dupla (nome/sobrenome desalinhados dos demais).',
     'CSS comum (static/css/formularios.css) com grade única e colunas iguais.'),
    ('R05', '5 Estrutura – layout', 'Nenhum elemento fixo deve encobrir campos do formulário.', NC,
     'Rodapé com position: fixed (ongs_register.css) cobre parte da tela durante a rolagem.',
     'Rodapé estático nas páginas de cadastro.'),
    ('R06', '5 Rótulos', 'Todo campo possui rótulo visível e associado a ele.', NC,
     'Campos de arquivo Foto de perfil, Logo e QR code renderizados sem <label>.',
     'Macro templates/macros/campo.html sempre renderiza <label for> (ou <legend> em grupos de rádio).'),
    ('R07', '5 Rótulos', 'Rótulos descritivos, consistentes e na terminologia do usuário.', P,
     '"Email" x "E-mail", "Confirmar Senha" x "Confirmar senha"; "Tamanho" para porte; "Foto 1" sem indicar que é a principal.',
     'Terminologia unificada: "E-mail", "Porte", "Foto principal", capitalização consistente.'),
    ('R08', '5 Rótulos', 'Unidade de medida indicada no rótulo.', NC,
     'Idade sem unidade; "em anos" só no placeholder, que some ao digitar.',
     'Rótulo "Idade (em anos)" + ajuda "De 0 a 30".'),
    ('R09', '5 Campos de entrada', 'Campos obrigatórios distinguidos dos opcionais.', NC,
     'Nenhuma marcação; o usuário só descobre após o envio. Complemento obrigatório para usuário e opcional para ONG.',
     'Asterisco + legenda "Campos marcados com * são obrigatórios"; opcionais dizem "Opcional". Complemento opcional nos dois.'),
    ('R10', '5 Campos de entrada', 'Formato esperado informado antes do preenchimento (exemplo/máscara).', NC,
     'CEP 8 dígitos, DDD 2, celular 9, CNPJ 14 só aparecem na mensagem de erro.',
     'Texto de ajuda sob cada campo (ex.: "8 dígitos, sem traço. Ex.: 58400000") ligado por aria-describedby.'),
    ('R11', '5 Campos de entrada', 'Tamanho máximo do campo indicado e limitado.', NC,
     'Sem maxlength; textareas de 300 caracteres sem aviso do limite.',
     'maxlength em todos os campos de texto e "(máx. 300 caracteres)" na ajuda.'),
    ('R12', '5 Campos de entrada', 'Dados não editáveis não devem parecer campos de entrada.', NC,
     'Campo "ONG" readonly com aparência idêntica aos editáveis.',
     'Campo removido do formulário; a ONG responsável aparece como texto de contexto.'),
    ('R13', '5 Entradas de escolha', 'Poucas opções fixas e mutuamente exclusivas exibidas todas de uma vez (botões de rádio).', NC,
     'Espécie, tamanho e status (3 opções cada) em <select>; espécie e tamanho estilizados como caixa de texto (sem seta), escondendo as opções.',
     'Espécie, porte e status como botões de rádio, com todas as opções visíveis; status mantém o padrão "Disponível".'),
    ('R14', '5 Entradas de escolha', 'Escolhas binárias por caixa de seleção.', NA,
     'Não havia nenhuma escolha binária nos cadastros.',
     'Caixas de seleção "Declaro que as informações fornecidas são verdadeiras" (usuário, obrigatória) e "Animal castrado" (animal, opcional).'),
    ('R15', '5 Controles', 'Ações de envio e de cancelamento claramente identificáveis.', NC,
     'Botão de envio branco, sem borda, parecendo texto solto; não há como cancelar.',
     'Botão primário verde e botão secundário "Cancelar" que volta à página inicial ou ao painel.'),
    ('R16', '6 Entrada de dados', 'Tipo de entrada adequado ao dado (teclado numérico, e-mail, data).', NC,
     'E-mail, telefone, CEP, CNPJ e número como type="text".',
     'type email/tel/date/number + inputmode="numeric" e autocomplete.'),
    ('R17', '6 Entrada de dados', 'Valores padrão oferecidos quando prováveis e sempre alteráveis.', P,
     'Status começa em "Disponível" (ok), mas a descrição do QR code era sobrescrita a cada envio, apagando o texto digitado.',
     'Padrão aplicado só se o campo ficar vazio, com aviso na ajuda.'),
    ('R18', '6 Entrada de dados', 'O usuário não redigita dados que o sistema já conhece.', C,
     'ONG do animal preenchida automaticamente a partir do login.', 'Mantido (exibido como contexto).'),
    ('R19', '6 Validação', 'Valores válidos são aceitos.', NC,
     'Idade 0 (filhote) rejeitada como "campo vazio" por DataRequired.',
     'InputRequired + NumberRange(0, 30).'),
    ('R20', '6 Validação', 'Ajuda/instruções contextuais sobre o propósito do campo e regras.', NC,
     'Sem regras de senha; propósito da descrição da imagem só no rótulo.',
     'Ajuda sob cada campo (senha mín. 6 caracteres, descrição para leitor de tela, maioridade).'),
    ('R21', '7 Feedback', 'Mensagens de erro no idioma do usuário, específicas e indicando a correção.', NC,
     '"This field is required.", "Invalid email address." (inglês); "Senhas diferentes".',
     'Mensagens próprias em português com a ação esperada; mensagens padrão do WTForms (data, número, escolha inválidos) '
     'traduzidas pela localização pt_BR.'),
    ('R22', '7 Feedback', 'Erro indicado junto ao campo e destacado visualmente; todos os erros mostrados.', NC,
     'Só o 1º erro de cada campo; campo não muda de aparência; sem aria-invalid. A validação nativa do navegador '
     'interrompia o envio mostrando um balão de cada vez.',
     'Borda vermelha + ícone, todos os erros listados, aria-invalid/aria-describedby; validação nativa desativada '
     '(novalidate) para que todos os erros apareçam de uma vez, no padrão do sistema.'),
    ('R23', '7 Feedback', 'Indicação dos erros no nível do formulário.', NC,
     'Nenhum resumo; em formulários longos o erro fica fora da tela.',
     'Resumo no topo com quantidade de erros e links que levam a cada campo; aviso de sessão expirada.'),
    ('R24', '7 Feedback', 'Dados digitados preservados após erro.', P,
     'E-mail duplicado do usuário redirecionava para o login, descartando tudo.',
     'Página re-renderizada com os dados e erro no campo E-mail. Fotos e senha não podem ser mantidas por segurança: '
     'o resumo avisa para selecioná-las/digitá-las novamente.'),
    ('R25', '7 Feedback', 'Falhas de envio sempre informadas (duplicidade, sessão expirada).', NC,
     'ONG com e-mail já existente: redirecionamento silencioso para o formulário vazio. Sessão expirada (token de '
     'segurança CSRF) também rejeitava o envio sem nenhuma mensagem.',
     'Mensagem "Já existe uma ONG cadastrada com este e-mail" no campo; "Sua sessão expirou. Revise os dados e envie '
     'novamente." no resumo.'),
    ('R26', '7 Feedback', 'Confirmação de conclusão do cadastro.', NC,
     'Mensagens flash só eram exibidas na tela de login; ONG e animal sem confirmação.',
     'Mensagens flash no layout público, nas páginas do usuário e nos painéis: "ONG X cadastrada com sucesso!" etc.'),
    ('R27', '8 Navegação', 'Foco do cursor visível e ordem de tabulação lógica.', NC,
     'CSS com outline: none em todos os inputs: não se vê onde está o foco ao usar o teclado.',
     'Contorno de foco (:focus-visible) de 3 px; ordem do DOM segue a ordem visual.'),
    ('R28', '8 Navegação', 'Navegação direta até o campo com erro.', NC,
     'Inexistente.', 'Links do resumo de erros levam o foco ao campo, inclusive aos grupos de botões de rádio.'),
]

NAP = 'Não se aplica'
COR = {NC: 'F8D7DA', P: 'FFF3CD', C: 'D4EDDA', NA: 'E2E3E5', NAP: 'F2F2F2'}

# Demais formulários: situação antes em Editar perfil | Editar animal | Entrar | Recuperar senha | Redefinir senha
# (id, situações, evidência antes, correção). Depois: Conforme onde aplicável.
CHECKLIST_O = [
    ('R01', (NC, P, C, C, C), 'Perfil: e-mail e senha em "Informações de Contato". Animal: campo ONG solto no grupo de fotos.',
     'Mesmos grupos <fieldset> dos cadastros; formulários curtos com um único grupo.'),
    ('R02', (NC, NC, C, C, NC), 'Edições abrem com "Informações Gerais"/"Informações do Animal"; redefinir senha não tem título.',
     '<h1> e <title>: Editar perfil, Editar animal, Entrar, Recuperar senha, Redefinir senha.'),
    ('R03', (P, C, C, NAP, C), 'Perfil: rua antes do CEP.', 'CEP → número → rua → complemento.'),
    ('R04', (NC, C, C, C, P), 'Perfil: nome/sobrenome recuados; redefinir: campos lado a lado com o botão desalinhado.',
     'CSS comum de formulários.'),
    ('R05', (C, C, NC, C, C), 'Login: as mensagens de erro ficavam no topo da página, encobertas pela barra de navegação fixa.',
     'Erros dentro do formulário (resumo e junto ao campo); rodapé estático.'),
    ('R06', (C, C, C, C, C), 'Campos com rótulo.', 'Mantido pela macro de campo; reCAPTCHA ganhou rótulo "Verificação de segurança".'),
    ('R07', (P, P, P, P, P), '"Email", "Confirmar Senha", "Tamanho", "Foto 1".', 'Terminologia igual à dos cadastros.'),
    ('R08', (NAP, NC, NAP, NAP, NAP), 'Idade sem unidade.', '"Idade (em anos)".'),
    ('R09', (NC, NC, NC, NC, NC), 'Nenhuma marcação de obrigatório; na edição do perfil a foto era exigida sem aviso.',
     'Asterisco + legenda; opcionais dizem "Opcional".'),
    ('R10', (NC, NC, NAP, NAP, NAP), 'CEP, DDD, celular e idade sem formato informado.', 'Ajuda de formato sob o campo.'),
    ('R11', (NC, NC, NC, NC, NC), 'Sem maxlength.', 'maxlength em todos os campos de texto.'),
    ('R12', (NAP, NC, NAP, NAP, NAP), 'Campo "ONG" somente leitura com aparência de editável.', 'ONG exibida como texto de contexto.'),
    ('R13', (NAP, NC, NAP, NAP, NAP), 'Espécie, tamanho e status em <select> com aparência de caixa de texto.', 'Botões de rádio.'),
    ('R14', (NAP, NA, NAP, NAP, NAP), '"Castrado" não existia na edição (o valor do cadastro não podia ser alterado).',
     'Caixa de seleção "Animal castrado", carregada com o valor atual.'),
    ('R15', (NC, NC, P, P, NC), 'Botões "Salvar"/"Redefinir Senha" com aparência de texto; sem Cancelar; login e recuperar sem caminho de volta.',
     'Botão primário verde + Cancelar / Criar conta / Voltar ao login.'),
    ('R16', (NC, C, NC, NC, NC), 'E-mail, telefone e CEP como type="text".', 'type email/tel/date/number, inputmode e autocomplete.'),
    ('R17', (NAP, C, NAP, NAP, NAP), 'Status atual carregado.', 'Mantido.'),
    ('R18', (NC, C, NAP, NAP, NC), 'Perfil abria com todos os campos vazios (salvar apagava nome, endereço etc.); '
     'redefinir pedia o e-mail de novo e não verificava o link enviado.',
     'Dados atuais carregados; o e-mail vem do link assinado (token de 1 h) e aparece como contexto.'),
    ('R19', (NC, NC, C, C, C), 'Perfil exigia nova foto a cada edição; animal rejeitava idade 0.',
     'Foto e senha opcionais na edição; idade 0 aceita.'),
    ('R20', (NC, NC, NAP, C, NC), 'Sem regras de senha nem propósito das descrições de imagem.', 'Ajuda contextual sob cada campo.'),
    ('R21', (NC, NC, NC, NC, NC), '"This field is required.", "Invalid email address."; login com senha errada gerava '
     '"Senha incorreta" e "Usuário não encontrado" ao mesmo tempo.',
     'Mensagens em português; login com mensagem única "E-mail ou senha incorretos".'),
    ('R22', (NC, NC, NC, NC, NC), 'Só o 1º erro, sem destaque; no recuperar senha o erro saía em texto claro sobre fundo branco '
     '(quase invisível); no login, as mensagens não apareciam no formulário (ver R05).',
     'Borda vermelha, ícone, aria-invalid; novalidate.'),
    ('R23', (NC, NC, NC, NC, NC), 'Nenhum resumo de erros.', 'Resumo no topo com links.'),
    ('R24', (P, P, P, C, P), 'Dados mantidos, mas sem aviso de que fotos/senha precisam ser informadas de novo.',
     'Aviso no resumo ("se ia trocá-las, ..." nas edições).'),
    ('R25', (NC, NC, NC, NC, NC), 'Sessão expirada rejeitava o envio sem mensagem; e-mail de outra conta no perfil não era tratado.',
     'Aviso de sessão expirada; "Este e-mail já está em uso por outra conta".'),
    ('R26', (NC, NC, C, C, C), 'Salvar perfil/animal voltava à página anterior sem confirmação.',
     '"Perfil atualizado com sucesso!", "Animal X atualizado com sucesso!".'),
    ('R27', (NC, NC, NC, P, NC), 'outline: none nos campos (recuperar só mudava a cor da borda).', 'Contorno de foco de 3 px.'),
    ('R28', (NC, NC, NC, NC, NC), 'Inexistente.', 'Links do resumo levam o foco ao campo.'),
]


# ---------- formatação ABNT (NBR 14724, 6024, 6027, 6023, 10520) ----------
FONTE = 'Arial'
LARGURA = 16  # cm úteis: A4 (21) - margem esquerda (3) - direita (2)
FONTE_ELAB = 'Elaborado pelos autores (2026).'
AUTORES = ('João Vitor Aguiar de Sousa', 'Lucas Ferreira Maia', 'Laryssa Finizola Costa da Silva', 'Tassio Sales dos Santos')
TITULO = 'AVALIAÇÃO DE CONFORMIDADE DO PETMATCH COM A ISO 9241-17'
SUBTITULO = 'diálogos por preenchimento de formulários'


def fonte_em(elemento):
    # estilos de título usam a fonte do tema; troca por Arial em todos os scripts
    rpr = elemento.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts'); rpr.insert(0, rf)
    for a in list(rf.attrib):
        del rf.attrib[a]
    for a in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rf.set(qn(a), FONTE)


def configurar(doc):
    for nome in ('Normal', 'Heading 1', 'Heading 2', 'Heading 3', 'Caption'):
        st = doc.styles[nome]
        fonte_em(st.element)
        st.font.size = Pt(12); st.font.color.rgb = RGBColor(0, 0, 0); st.font.italic = False
    pf = doc.styles['Normal'].paragraph_format
    pf.line_spacing = 1.5; pf.space_before = pf.space_after = Pt(0)
    pf.first_line_indent = Cm(1.25); pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    # seção primária: negrito e maiúsculas, em página nova; secundária: negrito; terciária: normal (NBR 6024)
    for nome, negrito in (('Heading 1', True), ('Heading 2', True), ('Heading 3', False)):
        st = doc.styles[nome]; st.font.bold = negrito
        pf = st.paragraph_format
        pf.first_line_indent = Cm(0); pf.alignment = WD_ALIGN_PARAGRAPH.LEFT; pf.line_spacing = 1.5
        pf.space_before = Pt(18); pf.space_after = Pt(18); pf.keep_with_next = True
    doc.styles['Heading 1'].paragraph_format.page_break_before = True
    st = doc.styles['Caption']; st.font.size = Pt(10); st.font.bold = False
    pf = st.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER; pf.first_line_indent = Cm(0); pf.line_spacing = 1
    pf.space_before = Pt(12); pf.space_after = Pt(4); pf.keep_with_next = True
    s = doc.sections[0]
    s.page_width, s.page_height = Cm(21), Cm(29.7)
    s.top_margin = s.left_margin = Cm(3); s.bottom_margin = s.right_margin = Cm(2); s.header_distance = Cm(2)


def sombrear(celula, cor):
    tc = celula._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear'); shd.set(qn('w:color'), 'auto'); shd.set(qn('w:fill'), cor)
    tc.append(shd)


def borda(nome, val='single'):
    e = OxmlElement(f'w:{nome}'); e.set(qn('w:val'), val)
    if val == 'single':
        e.set(qn('w:sz'), '8'); e.set(qn('w:space'), '0'); e.set(qn('w:color'), '000000')
    return e


def simples(p, alinhamento=WD_ALIGN_PARAGRAPH.LEFT, tamanho=None):
    pf = p.paragraph_format
    pf.first_line_indent = Cm(0); pf.line_spacing = 1; pf.alignment = alinhamento
    if tamanho:
        for r in p.runs:
            r.font.size = Pt(tamanho)
    return p


def campo_fld(tipo):
    r = OxmlElement('w:r'); f = OxmlElement('w:fldChar'); f.set(qn('w:fldCharType'), tipo); r.append(f)
    return r


class Relatorio:
    """Monta o documento. pag: página de cada título/legenda (2ª passagem); inicio: número da página da introdução."""

    def __init__(self, pag, inicio):
        self.doc = Document(); configurar(self.doc)
        self.pag, self.inicio = pag, inicio
        self.sumario, self.listas = [], {'Figura': [], 'Quadro': [], 'Tabela': []}

    # ----- texto -----
    def par(self, texto, negrito=False, italico=False, recuo=True):
        p = self.doc.add_paragraph(); r = p.add_run(texto); r.bold = negrito; r.italic = italico
        if not recuo:
            p.paragraph_format.first_line_indent = Cm(0)
        return p

    def centro(self, texto, negrito=False, antes=0, nova_pagina=False):
        p = self.doc.add_paragraph(); r = p.add_run(texto); r.bold = negrito
        pf = p.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.CENTER; pf.first_line_indent = Cm(0); pf.space_before = Pt(antes)
        pf.page_break_before = nova_pagina
        return p

    def alineas(self, itens):
        # NBR 6024: alíneas em letra minúscula seguida de parêntese, terminadas em ";" e a última em "."
        for i, item in enumerate(itens):
            p = self.doc.add_paragraph()
            pf = p.paragraph_format; pf.left_indent = Cm(1.9); pf.first_line_indent = Cm(-0.65)
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT  # rotas longas esticavam os espaços na justificação
            p.add_run(f'{"abcdefghijklmnopqrstuvwxyz"[i]}) ')
            if isinstance(item, tuple):
                p.add_run(item[0]).bold = True; item = item[1]
            p.add_run(item.rstrip(' ;.') + ('.' if i == len(itens) - 1 else ';'))

    def titulo(self, texto, nivel=1, centralizado=False):
        h = self.doc.add_heading(texto, nivel)
        if centralizado:
            h.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        self.sumario.append((texto, nivel))

    def pre_textual(self, texto):
        # títulos sem indicativo numérico, centralizados, fora do sumário (NBR 14724)
        p = self.centro(texto, negrito=True, nova_pagina=True)
        p.paragraph_format.space_after = Pt(18)
        return p

    # ----- ilustrações e tabelas -----
    def proximo(self, tipo):
        return len(self.listas[tipo]) + 1

    def legenda(self, tipo, texto):
        n = self.proximo(tipo)
        p = self.doc.add_paragraph(style='Caption')
        p.add_run(f'{tipo} ')
        fld = OxmlElement('w:fldSimple'); fld.set(qn('w:instr'), f' SEQ {tipo} \\* ARABIC ')
        r = OxmlElement('w:r'); t = OxmlElement('w:t'); t.text = str(n); r.append(t); fld.append(r)
        p._p.append(fld)
        p.add_run(f' – {texto}')
        self.listas[tipo].append(f'{tipo} {n} – {texto}')
        return p

    def fonte(self, nota=None, texto=FONTE_ELAB):
        p = simples(self.doc.add_paragraph(), tamanho=None)
        p.paragraph_format.space_after = Pt(0 if nota else 12)
        r = p.add_run(f'Fonte: {texto}'); r.font.size = Pt(10)
        if nota:
            p = simples(self.doc.add_paragraph()); p.paragraph_format.space_after = Pt(12)
            r = p.add_run(f'Nota: {nota}'); r.font.size = Pt(10)

    def tabela(self, tipo, titulo, cabecalho, linhas, larguras, fonte=9, nota=None):
        """tipo 'Tabela' (dados numéricos, laterais abertas, padrão IBGE) ou 'Quadro' (texto, grade fechada)"""
        self.legenda(tipo, titulo)
        escala = min(1, LARGURA / sum(larguras)); larguras = [w * escala for w in larguras]
        t = self.doc.add_table(rows=1, cols=len(cabecalho)); t.alignment = WD_TABLE_ALIGNMENT.CENTER
        if tipo == 'Quadro':
            t.style = 'Table Grid'
        else:
            bordas = OxmlElement('w:tblBorders')
            for lado, val in (('top', 'single'), ('left', 'nil'), ('bottom', 'single'), ('right', 'nil'),
                              ('insideH', 'nil'), ('insideV', 'nil')):
                bordas.append(borda(lado, val))
            t._tbl.tblPr.append(bordas)
        for i, h in enumerate(cabecalho):
            c = t.rows[0].cells[i]
            r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(fonte)
            simples(c.paragraphs[0], WD_ALIGN_PARAGRAPH.CENTER)
            if tipo == 'Quadro':
                sombrear(c, 'D9D9D9')
            else:
                tb = OxmlElement('w:tcBorders'); tb.append(borda('bottom')); c._tc.get_or_add_tcPr().append(tb)
        t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))  # cabeçalho repetido em cada página
        for linha in linhas:
            cells = t.add_row().cells
            for i, v in enumerate(linha):
                r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(fonte)
                numero = isinstance(v, int)
                simples(cells[i].paragraphs[0], WD_ALIGN_PARAGRAPH.CENTER if numero else WD_ALIGN_PARAGRAPH.LEFT)
                if v in COR and tipo == 'Quadro':
                    sombrear(cells[i], COR[v])
        t.autofit = False
        for i, w in enumerate(larguras):
            t.columns[i].width = Cm(w)  # grade da tabela (usada pelo LibreOffice)
        for row in t.rows:
            for i, w in enumerate(larguras):
                row.cells[i].width = Cm(w)
        # tabelas pequenas ficam inteiras; nas grandes, a última linha fica com a fonte (o Word respeita, o LibreOffice não)
        for row in (t.rows if len(linhas) <= 12 else t.rows[-1:]):
            for c in row.cells:
                c.paragraphs[0].paragraph_format.keep_with_next = True
        self.fonte(nota)

    def figura(self, titulo, imagens):
        self.legenda('Figura', titulo)
        t = self.doc.add_table(rows=2, cols=len(imagens)); t.alignment = WD_TABLE_ALIGNMENT.CENTER
        largura = (LARGURA - 0.4) / len(imagens)
        for i, (rotulo, caminho) in enumerate(imagens):
            p = simples(t.rows[0].cells[i].paragraphs[0], WD_ALIGN_PARAGRAPH.CENTER)
            r = p.add_run(rotulo); r.bold = True; r.font.size = Pt(10)
            p = simples(t.rows[1].cells[i].paragraphs[0], WD_ALIGN_PARAGRAPH.CENTER)
            p.add_run().add_picture(caminho, width=Cm(largura))
        self.fonte(texto='Elaborado pelos autores (2026), a partir de capturas de tela do sistema PetMatch.')

    # ----- sumário e listas: campos do Word com o resultado já preenchido -----
    def indice(self, marcador, instr, entradas):
        paras = []
        for texto, nivel in entradas:
            p = marcador.insert_paragraph_before()
            pf = p.paragraph_format; pf.first_line_indent = Cm(0); pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.tab_stops.add_tab_stop(Cm(LARGURA), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
            r = p.add_run(texto); r.bold = nivel == 1
            p.add_run('\t' + str(self.pag.get(texto, '00')))
            paras.append(p)
        if not paras:
            return
        primeiro = paras[0].runs[0]._r
        instr_r = OxmlElement('w:r'); it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve')
        it.text = f' {instr} '; instr_r.append(it)
        for e in (campo_fld('begin'), instr_r, campo_fld('separate')):
            primeiro.addprevious(e)
        paras[-1]._p.append(campo_fld('end'))

    def numerar_paginas(self):
        # elementos pré-textuais contam mas não mostram número; a numeração aparece a partir da introdução,
        # no canto superior direito (NBR 14724)
        s = self.doc.add_section(WD_SECTION.NEW_PAGE)
        s.header.is_linked_to_previous = False
        p = s.header.paragraphs[0]; simples(p, WD_ALIGN_PARAGRAPH.RIGHT)
        for e in (campo_fld('begin'),):
            p._p.append(e)
        r = OxmlElement('w:r'); it = OxmlElement('w:instrText'); it.text = ' PAGE '; r.append(it); p._p.append(r)
        p._p.append(campo_fld('separate'))
        r = p.add_run(str(self.inicio)); r.font.size = Pt(10)
        p._p.append(campo_fld('end'))
        num = OxmlElement('w:pgNumType'); num.set(qn('w:start'), str(self.inicio))
        s._sectPr.append(num)


def construir(pag, inicio):
    R = Relatorio(pag, inicio); doc = R.doc

    # ---------- capa ----------
    R.centro('UNIVERSIDADE ESTADUAL DA PARAÍBA\nCAMPUS I – CAMPINA GRANDE', negrito=True)
    R.centro('\n'.join(a.upper() for a in AUTORES), antes=90)
    p = R.centro('', antes=120); p.add_run(TITULO + ':').bold = True; p.add_run('\n' + SUBTITULO)
    R.centro('CAMPINA GRANDE\n2026', negrito=True, antes=190)

    # ---------- folha de rosto ----------
    R.centro('\n'.join(a.upper() for a in AUTORES), nova_pagina=True)
    p = R.centro('', antes=120); p.add_run(TITULO + ':').bold = True; p.add_run('\n' + SUBTITULO)
    p = simples(R.doc.add_paragraph(), WD_ALIGN_PARAGRAPH.JUSTIFY)
    p.paragraph_format.left_indent = Cm(8); p.paragraph_format.space_before = Pt(36)
    p.add_run('Relatório apresentado à disciplina Projeto de Interface Homem-Computador, da Universidade Estadual da '
              'Paraíba, como requisito parcial para avaliação.\n\nProfessor: Daniel Scherer.')
    R.centro('CAMPINA GRANDE\n2026', negrito=True, antes=170)

    # ---------- resumo e abstract (NBR 6028) ----------
    R.pre_textual('RESUMO')
    R.par(f'Este relatório avalia a conformidade dos formulários do sistema web PetMatch, que aproxima organizações de '
          f'proteção animal e pessoas interessadas em adotar, com a ISO 9241-17, norma que trata de diálogos por '
          f'preenchimento de formulários. Foram analisados oito formulários: os cadastros de usuário, de ONG e de animal, '
          f'as telas de edição de perfil e de animal e os formulários de login, recuperação e redefinição de senha. Por '
          f'meio da inspeção do código e de capturas de tela, {len(CHECKLIST)} requisitos foram avaliados. Nos cadastros, '
          f'{RESUMO[NC]} estavam não conformes, {RESUMO[P]} parcialmente conformes e {RESUMO[C]} conforme antes das '
          f'correções. Os principais problemas eram mensagens de erro em inglês ou ausentes, falta de indicação de campos '
          f'obrigatórios, de formatos e de unidades, escolha inadequada do tipo de campo e foco invisível na navegação por '
          f'teclado. As correções reuniram a renderização dos campos em um componente único, com rótulo, ajuda, '
          f'mensagens em português e resumo de erros com links para os campos. A verificação combinou testes '
          f'automatizados, validação independente no navegador, em que 26 requisitos foram conferidos sem falhas, e o '
          f'percurso dos formulários com o leitor de tela Orca. Após as correções, todos os requisitos aplicáveis '
          f'passaram a ser atendidos nos oito formulários.', recuo=False)
    R.par('', recuo=False)
    p = R.par('', recuo=False); p.add_run('Palavras-chave: ').bold = True
    p.add_run('ergonomia; formulários; ISO 9241-17; usabilidade; acessibilidade.')

    R.pre_textual('ABSTRACT')
    R.par(f'This report assesses the conformity of the forms of PetMatch, a web system that connects animal protection '
          f'organizations with people interested in adopting, with ISO 9241-17, the standard on form filling dialogues. '
          f'Eight forms were analyzed: the user, organization and animal registration forms, the profile and animal '
          f'editing screens, and the login, password recovery and password reset forms. Through code inspection and '
          f'screenshots, {len(CHECKLIST)} requirements were assessed. In the registration forms, {RESUMO[NC]} were '
          f'nonconforming, {RESUMO[P]} partially conforming and {RESUMO[C]} conforming before the corrections. The main '
          f'problems were error messages in English or missing, no indication of required fields, formats and units, '
          f'inadequate field types and invisible keyboard focus. The corrections render every field through a single '
          f'component with label, help text, messages in Portuguese and an error summary linking to the fields. '
          f'Verification combined automated tests, an independent browser check in which 26 requirements passed '
          f'without failures, and a walkthrough with the Orca screen reader. After the corrections, all applicable '
          f'requirements are met in the eight forms.', recuo=False)
    R.par('', recuo=False)
    p = R.par('', recuo=False); p.add_run('Keywords: ').bold = True
    p.add_run('ergonomics; forms; ISO 9241-17; usability; accessibility.')

    # ---------- listas e sumário (preenchidos ao final) ----------
    marcadores = {}
    for tipo, nome in (('Figura', 'LISTA DE FIGURAS'), ('Quadro', 'LISTA DE QUADROS'), ('Tabela', 'LISTA DE TABELAS'),
                       ('Sumário', 'SUMÁRIO')):
        R.pre_textual(nome)
        marcadores[tipo] = R.doc.add_paragraph()
    R.numerar_paginas()

    # ---------- 1 introdução ----------
    R.titulo('1 INTRODUÇÃO E ESCOPO')
    R.par('O PetMatch é um sistema web (Flask e WTForms) que aproxima organizações não governamentais (ONGs) de proteção '
          'animal e pessoas interessadas em adotar. Este relatório avalia os formulários do sistema frente à ISO 9241-17, '
          'que estabelece requisitos ergonômicos para diálogos por preenchimento de formulários (INTERNATIONAL '
          'ORGANIZATION FOR STANDARDIZATION, 1998). O trabalho identifica os requisitos aplicáveis, demonstra a aderência '
          'ou não conformidade de cada um, descreve as correções implementadas e apresenta o comparativo antes e depois.')
    R.par('Foram avaliados os oito formulários de preenchimento do sistema. Os três cadastros formam o núcleo do '
          'trabalho, por atenderem ao requisito da disciplina de no mínimo 15 campos:')
    R.alineas(['cadastro de usuário (adotante), na rota /cadastro',
               'cadastro de ONG, feito pelo administrador, na rota /admin_dashboard/ongs_register',
               'cadastro de animal, feito pela ONG, na rota /ong_dashboard/pets_register'])
    R.par('Os outros cinco reaproveitam os mesmos campos ou são formulários curtos de acesso:')
    R.alineas(['edição de perfil, na rota /profile/edit', 'edição de animal, na rota /ong_dashboard/pets_edit/<id>',
               'login ("Entrar"), na rota /login', 'recuperação de senha, na rota /recuperar',
               'redefinição de senha, na rota /redefinir, aberta pelo link enviado por e-mail'])
    R.par('Ficaram fora da análise os elementos que não são diálogos de preenchimento: botões isolados (Tenho interesse, '
          'Excluir animal, Editar perfil), a caixa de mensagem do chat e os filtros da lista de pets.')

    # ---------- 2 norma ----------
    R.titulo('2 A NORMA ISO 9241-17')
    R.par('A ISO 9241-17 trata de diálogos em que o usuário preenche, seleciona ou modifica campos rotulados em um '
          'formulário (INTERNATIONAL ORGANIZATION FOR STANDARDIZATION, 1998). As recomendações estão organizadas nos '
          'seguintes grupos, usados como referência na coluna "Cláusula" do checklist:')
    R.alineas([('estrutura do formulário (cl. 5): ', 'organização e agrupamento dos campos, título, layout, rótulos, campos '
                'de entrada, entradas de escolha e controles'),
               ('considerações de entrada (cl. 6): ', 'tipo de entrada, valores padrão, validação e ajuda'),
               ('feedback (cl. 7): ', 'mensagens de erro, indicação de erros, preservação de dados e confirmação'),
               ('navegação (cl. 8): ', 'movimentação do cursor ou do foco e acesso aos campos')])
    R.par('A ISO 9241-17 foi cancelada e substituída pela ISO 9241-143, que trata do mesmo tema com o título "Forms" '
          '(INTERNATIONAL ORGANIZATION FOR STANDARDIZATION, 2012). Este relatório segue a ISO 9241-17, adotada pela '
          'disciplina. A numeração das cláusulas segue a estrutura de referência da norma e deve ser conferida com a '
          'cópia disponível na xerox da disciplina.')

    # ---------- 3 metodologia ----------
    R.titulo('3 METODOLOGIA')
    R.par('O trabalho seguiu as etapas abaixo:')
    R.alineas(['inspeção do código dos formulários (config/forms.py), das rotas (app.py) e dos templates Jinja',
               'execução do sistema localmente e captura das telas de cada formulário vazio, após envio inválido e, para '
               f'a ONG, após envio com e-mail já cadastrado (script relatorio/capturar_telas.py); a versão "antes" é o '
               f'commit {BASE}, executado com banco SQLite de teste e reCAPTCHA desligado, únicas mudanças necessárias '
               'para rodá-lo localmente',
               'nas capturas da versão "antes", desligamento da validação nativa do navegador para registrar as mensagens '
               'do servidor, já que o navegador mostrava ao usuário real um balão por campo; na versão "depois", o próprio '
               'formulário desativa essa validação (novalidate), e a captura mostra exatamente o que o usuário vê',
               'avaliação de cada requisito aplicável como Conforme, Parcial, Não conforme ou Não se aplica',
               'correção do software e repetição das mesmas capturas e cenários',
               'verificação automatizada dos fluxos corrigidos (test_forms.py)',
               'validação independente dos requisitos no navegador (relatorio/verificacao/validar.py) e percurso dos '
               'formulários com o leitor de tela Orca (relatorio/verificacao/orca_teste.py)'])

    # ---------- 4 campos ----------
    R.titulo('4 OS FORMULÁRIOS E SEUS CAMPOS')
    tot_a = sum(len(v) for v in ANTES.values()); tot_d = sum(len(v) for v in DEPOIS.values())
    tipos_a = sorted({c[2] for v in ANTES.values() for c in v}); tipos_d = sorted({c[2] for v in DEPOIS.values() for c in v})
    R.par(f'A Tabela {R.proximo("Tabela")} resume os campos dos três cadastros. Antes, eram {tot_a} campos com '
          f'{len(tipos_a)} tipos HTML ({", ".join(tipos_a)}), quase todos "text". Depois, são {tot_d} campos com '
          f'{len(tipos_d)} tipos ({", ".join(tipos_d)}). O requisito da disciplina (três cadastros, no mínimo 15 campos '
          'e variedade de tipos) é atendido.')
    R.tabela('Tabela', 'Campos dos cadastros antes e depois das correções', ['Cadastro', 'Campos antes', 'Campos depois', 'Tipos depois'],
             [(n, len(ANTES[n]), len(DEPOIS[n]), ', '.join(sorted({c[2] for c in DEPOIS[n]}))) for n, _ in CADASTROS]
             + [('Total', tot_a, tot_d, f'{len(tipos_d)} tipos distintos')], [3, 2.5, 2.5, 8])

    def campos_quadro(antes_d, depois_d, nome, titulo_q):
        antes = {c[0]: c for c in antes_d[nome]}
        linhas = []
        for nm, rot, tp, req in depois_d[nome]:
            a = antes.pop(nm, None)
            linhas.append((rot, f'{a[2]}{" *" if a[3] else ""}' if a else '— (novo)', f'{tp}{" *" if req else ""}'))
        linhas += [(a[1], f'{a[2]}{" *" if a[3] else ""}', '— (removido)') for a in antes.values()]
        R.tabela('Quadro', titulo_q, ['Campo', 'Tipo antes', 'Tipo depois'], linhas, [7, 4.5, 4.5],
                 nota='* campo obrigatório.')

    for i, (nome, _) in enumerate(CADASTROS, start=1):
        alvo = nome if nome == 'ONG' else nome.lower()
        R.titulo(f'4.{i} Cadastro de {alvo}', 2)
        R.par(f'O Quadro {R.proximo("Quadro")} lista os campos do cadastro de {alvo}, com o tipo antes e depois das correções.')
        campos_quadro(ANTES, DEPOIS, nome, f'Campos do cadastro de {alvo}')

    R.titulo('4.4 Demais formulários', 2)
    R.par('As telas de edição usam as mesmas definições dos cadastros (herança das classes de formulário), com foto e '
          f'senha opcionais. Os formulários de acesso têm poucos campos. A Tabela {R.proximo("Tabela")} resume os campos '
          'de cada um.')
    R.tabela('Tabela', 'Campos dos demais formulários antes e depois das correções',
             ['Formulário', 'Campos antes', 'Campos depois', 'Tipos depois'],
             [(n, len(ANTES_O[n]), len(DEPOIS_O[n]), ', '.join(sorted({c[2] for c in DEPOIS_O[n]}))) for n, _ in OUTROS],
             [3.5, 2.5, 2.5, 7.5])
    for i, (nome, _) in enumerate(OUTROS, start=1):
        R.titulo(f'4.4.{i} {nome}', 3)
        nota = ''
        if nome == 'Editar animal':
            nota = (' O adotante continua em lista suspensa porque as opções variam com os interessados em cada animal; '
                    'ele só aparece quando o status é Adotado ou Reservado.')
        R.par(f'O Quadro {R.proximo("Quadro")} lista os campos do formulário {nome}.{nota}')
        campos_quadro(ANTES_O, DEPOIS_O, nome, f'Campos do formulário {nome}')

    # ---------- 5 checklist ----------
    R.titulo('5 CHECKLIST DE CONFORMIDADE')
    R.titulo('5.1 Cadastros', 2)
    R.par(f'Cada requisito aplicável foi avaliado antes e depois das correções. A Tabela {R.proximo("Tabela")} resume a '
          f'situação inicial e o Quadro {R.proximo("Quadro")} detalha cada requisito. Todos os itens ficaram conformes '
          'após as correções.')
    R.tabela('Tabela', 'Situação dos requisitos nos cadastros antes das correções', ['Situação antes', 'Quantidade'],
             [(s_, q) for s_, q in RESUMO.items()] + [('Total de requisitos', len(CHECKLIST))], [7, 3])
    R.tabela('Quadro', 'Checklist de conformidade dos cadastros',
             ['ID', 'Cláusula', 'Requisito', 'Antes', 'Evidência (antes)', 'Correção', 'Depois'],
             [(i, cl, req, s_, ev, cor, C) for i, cl, req, s_, ev, cor in CHECKLIST],
             [1.1, 1.7, 2.7, 1.8, 3.8, 3.4, 1.9], fonte=8)

    R.titulo('5.2 Demais formulários', 2)
    R.par('Os mesmos requisitos da seção 5.1 foram avaliados nas cinco telas restantes. "Não se aplica" indica que o '
          f'formulário não tem o tipo de campo em questão. A Tabela {R.proximo("Tabela")} resume a situação inicial e o '
          f'Quadro {R.proximo("Quadro")} detalha cada requisito. Depois das correções, todos os itens aplicáveis ficaram '
          'conformes.')
    cont = {s_: sum(x[1].count(s_) for x in CHECKLIST_O) for s_ in (NC, P, C, NA, NAP)}
    R.tabela('Tabela', 'Situação dos requisitos nos demais formulários antes das correções',
             ['Situação antes (5 telas × 28 requisitos)', 'Quantidade'], [(s_, q) for s_, q in cont.items()], [8, 3])
    R.tabela('Quadro', 'Checklist de conformidade dos demais formulários',
             ['ID', 'Editar perfil', 'Editar animal', 'Entrar', 'Recuperar senha', 'Redefinir senha', 'Evidência (antes)', 'Correção'],
             [(i, *st, ev, cor) for i, st, ev, cor in CHECKLIST_O], [1.0, 1.9, 1.9, 1.9, 1.9, 1.9, 3.0, 2.9], fonte=8)

    # ---------- 6 comparativo ----------
    R.titulo('6 COMPARATIVO VISUAL ANTES E DEPOIS')
    R.par(f'As Figuras {R.proximo("Figura")} a {R.proximo("Figura") + len(CAPTURAS) - 1} comparam cada tela antes '
          '(à esquerda) e depois (à direita) das correções, nos mesmos cenários.')
    for n, (chave, legenda) in enumerate(CAPTURAS):
        p = R.par(f'{NOTAS[chave].rstrip(".")} (Figura {R.proximo("Figura")}).')
        p.paragraph_format.page_break_before = n > 0
        R.figura(legenda, [('ANTES', f'{IMG}antes_{chave}.png'), ('DEPOIS', f'{IMG}depois_{chave}.png')])

    # ---------- 7 arquivos ----------
    R.titulo('7 ARQUIVOS ALTERADOS')
    R.par(f'O Quadro {R.proximo("Quadro")} relaciona os arquivos alterados e o que mudou em cada um.')
    R.tabela('Quadro', 'Arquivos alterados', ['Arquivo', 'Alteração'], ARQUIVOS, [6, 10])

    # ---------- 8 verificação ----------
    R.titulo('8 VERIFICAÇÃO')
    for texto in VERIFICACAO:
        R.par(texto)
    R.titulo('8.1 Validação no navegador', 2)
    R.par('O script relatorio/verificacao/validar.py, independente dos testes acima, abre cada um dos oito formulários no '
          'Chrome com o sistema em execução, mede a página real (rótulos, tipos, ajudas, foco, rodapé e cores) e faz um '
          'envio inválido. Critérios que só valem para alguns formulários (mínimo de 15 campos, botões de rádio, caixa de '
          'seleção, aviso de reenvio de foto ou senha) são aplicados apenas onde o campo existe. Os requisitos R19, R25 e '
          f'R26 dependem de gravar dados e são cobertos pelo test_forms.py. A Tabela {R.proximo("Tabela")} mostra o '
          'resultado: 26 requisitos verificados, nenhum com falha.')
    R.tabela('Tabela', 'Resultado da validação no navegador', ['Requisito', 'Formulários verificados', 'Resultado'],
             [(r_, n_, ok) for r_, (ok, n_) in VALIDACAO.items()], [3, 4, 3])

    R.titulo('8.2 Teste com leitor de tela (Orca 46)', 2)
    R.par('Os três cadastros foram percorridos com a tecla Tab no Google Chrome com o leitor de tela Orca 46 (GNOME/Linux) '
          'em execução; a fala de cada campo foi extraída do registro de depuração do Orca. A primeira rodada, já com as '
          'correções da ISO aplicadas, revelou que o Orca não anunciava o nome do grupo, a obrigatoriedade nem o erro dos '
          'botões de rádio, e não dizia "obrigatório" em senha, arquivo e data (a marcação estava correta, mas o leitor '
          'ignora esse estado nesses tipos). As correções usaram os atributos de acessibilidade da especificação WAI-ARIA '
          '(WORLD WIDE WEB CONSORTIUM, 2023): nome do grupo, ajuda e erro ligados a cada botão de rádio '
          '(aria-labelledby e aria-describedby), texto "(obrigatório)" visível apenas para leitores de tela nesses tipos, '
          'erro incluído no nome acessível de rádios e arquivos, e foco levado ao resumo de erros quando a página '
          'recarrega com erros. A terceira rodada confirmou o anúncio correto em todos os campos. Essas três rodadas foram '
          'feitas sobre o mesmo código dos cadastros, trazido sem alteração para este repositório. O Quadro '
          f'{R.proximo("Quadro")} compara as falas registradas.')
    R.tabela('Quadro', 'Falas do Orca nos cadastros antes e depois dos ajustes de acessibilidade',
             ['Situação', '1ª rodada (fala do Orca)', 'Após correção (fala do Orca)'], ORCA_CADASTROS, [4, 6, 6])
    R.par('Uma quarta rodada, neste repositório, percorreu os oito formulários (178 passos, 177 com fala registrada). '
          'Os cadastros mantiveram as falas acima e as cinco telas novas foram anunciadas corretamente, como mostra o '
          f'Quadro {R.proximo("Quadro")}. Ao abrir a edição de perfil, a janela do Chrome perdeu o foco por alguns passos '
          'e o Orca leu outra janela; a partir do primeiro campo do formulário, o percurso seguiu normalmente.')
    R.tabela('Quadro', 'Falas do Orca nos demais formulários', ['Situação', 'Fala do Orca'], ORCA_OUTROS, [5, 11])
    R.par('Limitações: o teste foi feito com um único leitor de tela (Orca) e um navegador (Chrome), e a navegação foi '
          'automatizada (tecla Tab e foco programático), sem usuário real. Nos campos de arquivo, o Orca repete o rótulo '
          'por causa da forma como o Chrome expõe esse controle. Recomenda-se repetir o roteiro com o NVDA no Windows.')

    # ---------- 9 observações, 10 considerações finais ----------
    R.titulo('9 OBSERVAÇÕES FORA DO ESCOPO DA NORMA')
    R.par('Durante o trabalho foram identificados pontos que não pertencem à ISO 9241-17, mas afetam o sistema:')
    R.alineas(OBSERVACOES)

    R.titulo('10 CONSIDERAÇÕES FINAIS')
    R.par(f'Dos {len(CHECKLIST)} requisitos aplicáveis avaliados nos cadastros, {RESUMO[NC]} estavam não conformes, '
          f'{RESUMO[P]} parcialmente conformes e {RESUMO[C]} conforme antes das correções. Os principais problemas eram de '
          'feedback (mensagens em inglês, erros silenciosos, ausência de confirmação), de sinalização (obrigatoriedade, '
          'formato e unidade não informados) e de escolha do tipo de campo. Após as correções, todos os requisitos '
          'aplicáveis passaram a ser atendidos nos três cadastros, e os formulários ganharam variedade de tipos de campo.')
    R.par('O mesmo tratamento foi estendido às duas telas de edição e aos três formulários de acesso, que passaram a '
          'seguir o mesmo padrão de rótulos, ajuda, feedback e navegação, verificado no navegador e com o leitor de tela.')

    # ---------- referências (NBR 6023): espaço simples, alinhadas à esquerda, separadas por uma linha em branco ----------
    R.titulo('REFERÊNCIAS', centralizado=True)
    for antes, negrito, depois in REFERENCIAS:
        p = simples(R.doc.add_paragraph()); p.paragraph_format.space_after = Pt(12)
        p.add_run(antes); p.add_run(negrito).bold = True; p.add_run(depois)

    # ---------- preenche listas e sumário ----------
    for tipo in ('Figura', 'Quadro', 'Tabela'):
        R.indice(marcadores[tipo], f'TOC \\h \\z \\c "{tipo}"', [(t, 0) for t in R.listas[tipo]])
    R.indice(marcadores['Sumário'], 'TOC \\o "1-3" \\h \\z \\u', R.sumario)
    return R


# ---------- conteúdo ----------
RESUMO = {s_: sum(1 for x in CHECKLIST if x[3] == s_) for s_ in (NC, P, C, NA)}
CAPTURAS = [('usuario_vazio', 'Cadastro de usuário: formulário vazio'),
            ('usuario_erros', 'Cadastro de usuário: após envio com dados inválidos'),
            ('ong_vazio', 'Cadastro de ONG: formulário vazio'),
            ('ong_erros', 'Cadastro de ONG: após envio com dados inválidos'),
            ('ong_email_duplicado', 'Cadastro de ONG: envio com e-mail já cadastrado'),
            ('animal_vazio', 'Cadastro de animal: formulário vazio'),
            ('animal_erros', 'Cadastro de animal: após envio com dados inválidos'),
            ('perfil_editar', 'Editar perfil: ao abrir'),
            ('perfil_editar_erros', 'Editar perfil: após envio com dados inválidos'),
            ('animal_editar', 'Editar animal: ao abrir'),
            ('animal_editar_erros', 'Editar animal: após envio com dados inválidos'),
            ('login_vazio', 'Entrar: formulário vazio'),
            ('login_erros', 'Entrar: senha incorreta'),
            ('recuperar_vazio', 'Recuperar senha: formulário vazio'),
            ('recuperar_erros', 'Recuperar senha: e-mail inválido'),
            ('redefinir_vazio', 'Redefinir senha: ao abrir'),
            ('redefinir_erros', 'Redefinir senha: senhas inválidas')]
NOTAS = {
    'usuario_vazio': 'Antes: sem título, sem marcação de obrigatórios, foto sem rótulo, botão sem aparência de botão. '
                     'Depois: título, legenda de obrigatórios, grupos, ajuda de formato, novos campos (data, declaração) e botões Cancelar e Cadastrar',
    'usuario_erros': 'Antes: mensagens em inglês e só abaixo do campo. Depois: resumo no topo com links, campos destacados e mensagens em português',
    'ong_vazio': 'Antes: Instagram em "Informações Bancárias", fotos sem rótulo, rodapé fixo. Depois: grupos Dados da ONG, Endereço, Contato, Doações e Acesso',
    'ong_erros': 'Depois: todos os erros visíveis no resumo e junto aos campos',
    'ong_email_duplicado': 'Antes: o sistema volta ao formulário vazio, sem explicação. Depois: dados preservados e erro no campo E-mail',
    'animal_vazio': 'Antes: espécie e tamanho em listas que parecem caixas de texto, idade sem unidade, campo ONG editável na aparência. '
                    'Depois: botões de rádio, "Idade (em anos)", caixa "Animal castrado" e ONG como contexto',
    'animal_erros': 'Depois: idade fora da faixa explicada e resumo de erros no topo',
    'perfil_editar': 'Antes: todos os campos vazios (salvar apagaria os dados) e foto exigida a cada edição. '
                     'Depois: dados atuais carregados, foto atual exibida e foto e senha opcionais',
    'perfil_editar_erros': 'Depois: resumo com links, erros em português e aviso sobre foto e senha',
    'animal_editar': 'Antes: listas com aparência de caixa de texto, campo ONG editável na aparência, sem "castrado". '
                     'Depois: igual ao cadastro, com os dados atuais e a foto atual de cada posição',
    'animal_editar_erros': 'Antes: "This field is required." e "Idade inválida". Depois: resumo e mensagens explicativas',
    'login_vazio': 'Antes: placeholder repetindo o rótulo e botão sem destaque. Depois: mesmo padrão visual dos demais formulários',
    'login_erros': 'Antes: as mensagens "Senha incorreta" e "Usuário não encontrado" eram geradas juntas, mas ficavam '
                   'encobertas pela barra de navegação, e nada aparece no formulário. Depois: "E-mail ou senha incorretos", '
                   'sem revelar se o e-mail existe',
    'recuperar_vazio': 'Depois: ajuda indicando qual e-mail usar e caminho de volta ao login',
    'recuperar_erros': 'Antes: "Invalid email address." em texto claro sobre fundo branco, quase invisível. Depois: erro destacado em português',
    'redefinir_vazio': 'Antes: sem título, pedindo de novo o e-mail e sem verificar o link. Depois: conta identificada pelo link',
    'redefinir_erros': 'Depois: regras da senha informadas antes e erros explicados',
}
ARQUIVOS = [
    ('config/forms.py', 'Tipos de campo, validadores e mensagens em português, ajudas, limites, novos campos (data de nascimento, declaração, castrado); localização pt_BR das mensagens padrão.'),
    ('config/models.py', 'Colunas Usuario.data_nascimento (MySQL: ALTER TABLE usuario ADD COLUMN data_nascimento DATE NULL) e '
                         'Animal.castrado (MySQL: ALTER TABLE animal ADD COLUMN castrado BOOLEAN NOT NULL DEFAULT 0).'),
    ('templates/macros/campo.html', 'Macro única de campo (rótulo, obrigatório, ajuda, erros, nomes acessíveis para leitor de tela) e cabeçalho (legenda e resumo de erros com foco automático).'),
    ('templates/macros/flash.html', 'Mensagens de confirmação e erro do sistema, incluídas nos dois layouts e nos painéis.'),
    ('templates/auth/cadastro.html, admin_pages/ongs_register.html, ongs_pages/pets_register.html', 'Reescritos com grupos, título, macro, botões e novalidate.'),
    ('templates/user_pages/edit.html, ongs_pages/pets_edit.html, auth/login.html, user_pages/recuperarSenha.html, '
     'user_pages/redefinirSenha.html', 'Reescritos no mesmo padrão; a edição de animal mostra a foto atual de cada posição.'),
    ('static/css/formularios.css', 'Estilo comum: grupos, ajuda, erros, foco visível, botões, rádios e caixa de seleção.'),
    ('app.py', 'E-mail duplicado como erro no campo, mensagens de sucesso, padrão do QR code, data de nascimento, castrado, '
            'WTF_I18N_ENABLED = False (tradução pt_BR), URI do banco por variável de ambiente; edição de perfil e de '
            'animal carregam os dados atuais; login com mensagem única; recuperação com resposta neutra; redefinição '
            'exige link assinado; edição de animal restrita à ONG dona.'),
    ('test_forms.py', 'Verificação automatizada dos oito formulários.'),
    ('relatorio/verificacao/', 'Servidor de teste, validação no navegador, roteiro do Orca e resultados registrados.'),
]
VERIFICACAO = [
    'O script test_forms.py executa, contra um banco SQLite temporário: cadastro válido de usuário (com data de '
    'nascimento e complemento vazio); e-mail duplicado com preservação dos dados; rejeição de menor de idade e de '
    'declaração não marcada, com novalidate e aviso de reenvio de fotos e senha; mensagem de data inválida em português; '
    'cadastro de ONG com mensagem de sucesso e descrição padrão do QR code; e-mail de ONG duplicado; cadastro de animal '
    'com idade 0, botões de rádio e caixa "castrado"; foto opcional sem descrição; todos os links do resumo de erros '
    'apontando para um elemento existente; ausência de mensagens em inglês; e sessão expirada informada no resumo.',
    'Nas demais telas, o mesmo script verifica: edição de animal com dados atuais, idade 0 e sem nova foto, e bloqueio '
    'para outra ONG; edição de perfil com dados atuais, sem trocar foto nem senha, recusando e-mail de outra conta e '
    'senha curta ou diferente; login com mensagem única; recuperação de senha com a mesma resposta para e-mail '
    'cadastrado ou não e envio do link só ao cadastrado; redefinição rejeitando link falso e trocando a senha pelo link '
    'válido. Todos os casos passaram.',
    'Durante a verificação foi encontrado um defeito adicional: o complemento vazio podia chegar como nulo e violar a '
    'restrição NOT NULL do banco (erro 500). O defeito foi corrigido.',
    'Uma revisão posterior das afirmações do checklist contra o sistema em execução encontrou lacunas na primeira versão '
    'das correções (validação nativa do navegador escondendo o resumo, sessão expirada silenciosa, links do resumo sem '
    'destino nos botões de rádio, mensagens padrão em inglês, aviso de reenvio de fotos e senha, status em lista '
    'suspensa e confirmação de termos inexistentes). Todas foram corrigidas e cobertas pelo teste.',
]
VALIDACAO = {}
for linha in open('relatorio/verificacao/validar.out', encoding='utf-8'):
    if linha[:1] == 'R' and linha[3:4] == ' ':
        forms_ok = []
        for trecho in linha[11:].split(' ; '):
            nome_f = trecho.split(':')[0].strip()
            if nome_f not in forms_ok:
                forms_ok.append(nome_f)
        VALIDACAO[linha[:3]] = ('OK' if 'OK' in linha[4:10] else 'FALHA', len(forms_ok))
ORCA_CADASTROS = [
    ('Espécie (rádio), ao focar', 'Gato. não selecionado radio button', 'Espécie (obrigatório) Gato. não selecionado radio button'),
    ('Espécie após envio sem escolha', 'Gato. não selecionado radio button',
     'Espécie (obrigatório) Gato ⚠ Campo obrigatório. não selecionado radio button'),
    ('Senha', 'Senha password text. Mínimo de 6 caracteres.', 'Senha (obrigatório) password text. Mínimo de 6 caracteres.'),
    ('Data de nascimento', 'Data de nascimento Dia Data de nascimento 0 spin button. É preciso ter 18 anos ou mais.',
     'Data de nascimento (obrigatório) Dia ... 0 spin button. É preciso ter 18 anos ou mais.'),
    ('Foto principal após erro', 'Foto principal Foto principal: Nenhum arquivo escolhido push button.',
     'Foto principal (obrigatório) ⚠ Campo obrigatório. ...: Nenhum arquivo escolhido push button.'),
    ('Página recarregada com erros', 'Resumo lido de forma inconsistente (dependia do tempo de carregamento).',
     'notification. Corrija 13 campo(s) para continuar: • Nome da ONG: Campo obrigatório. • CNPJ: ...'),
    ('Campo de texto com erro (sem mudança)', 'CEP entry 123 obrigatório. entrada inválida. 8 dígitos, sem traço. Ex.: 58400000 ⚠ O CEP deve ter 8 dígitos, sem traço.',
     'idem'),
    ('Declaração após erro', '(não registrada na 1ª rodada)',
     'Declaro que as informações fornecidas são verdadeiras check box não selecionada obrigatório. entrada inválida. ⚠ É preciso confirmar a declaração para se cadastrar.'),
]
ORCA_OUTROS = [
    ('Editar animal: espécie (dado atual)', 'Espécie (obrigatório) Gato. selecionado radio button'),
    ('Editar animal: idade após erro', 'Idade (em anos) 40 spin button obrigatório. entrada inválida. De 0 a 30. ... ⚠ Informe uma idade entre 0 e 30 anos.'),
    ('Editar perfil: nova senha', 'Nova senha password text. Opcional: deixe em branco para manter a senha atual. Mínimo de 6 caracteres.'),
    ('Editar perfil: página com erros', 'notification. Corrija 4 campo(s) para continuar: • CEP: O CEP deve ter 8 dígitos, sem traço. • E-mail: ...'),
    ('Entrar: e-mail após erro', 'E-mail entry abc obrigatório. entrada inválida. ⚠ Informe um e-mail válido, ex.: nome@dominio.com.'),
    ('Entrar: reCAPTCHA', 'Não sou um robô check box não selecionada.'),
    ('Recuperar senha: e-mail', 'E-mail entry obrigatório. Use o e-mail informado no seu cadastro.'),
    ('Redefinir senha: confirmação após erro', 'Confirmar senha (obrigatório) password text. Repita a senha digitada acima. ⚠ As senhas não coincidem.'),
]
OBSERVACOES = [
    'credenciais (senha do e-mail SMTP e chaves do reCAPTCHA) estão escritas diretamente em app.py; recomenda-se '
    'movê-las para variáveis de ambiente e revogá-las, e os valores não são reproduzidos neste relatório',
    'o texto da página de cadastro pedia que ONGs enviassem a senha por e-mail; o pedido foi removido',
    'problemas de segurança encontrados nas telas de acesso foram corrigidos junto: a redefinição de senha aceitava '
    'qualquer e-mail sem verificar o link enviado, qualquer ONG podia editar animais de outra e o login gravava a senha '
    'digitada no log do servidor',
    'a recuperação de senha só atende usuários adotantes; ONGs e administradores não têm esse fluxo',
    'a barra de navegação mostra "Cadastrar" e "Entrar" mesmo com usuário logado',
]
# (texto antes do destaque, destaque em negrito, texto depois) — NBR 6023
REFERENCIAS = [
    ('INTERNATIONAL ORGANIZATION FOR STANDARDIZATION. ', 'ISO 9241-17',
     ': ergonomic requirements for office work with visual display terminals (VDTs): part 17: form filling dialogues. '
     'Geneva: ISO, 1998.'),
    ('INTERNATIONAL ORGANIZATION FOR STANDARDIZATION. ', 'ISO 9241-143',
     ': ergonomics of human-system interaction: part 143: forms. Geneva: ISO, 2012.'),
    ('WORLD WIDE WEB CONSORTIUM. ', 'Accessible Rich Internet Applications (WAI-ARIA) 1.2',
     '. [S. l.]: W3C, 2023. Disponível em: https://www.w3.org/TR/wai-aria-1.2/. Acesso em: 4 out. 2026.'),
]


# ---------- duas passagens: a 1ª descobre em que página cai cada título e legenda ----------
def paginas(pdf, R):
    texto = subprocess.run(['pdftotext', pdf, '-'], capture_output=True, text=True, check=True).stdout
    linhas = [[l.strip() for l in pg.splitlines()] for pg in texto.split('\f')]
    # a introdução é a primeira página em que o título aparece sozinho na linha (no sumário vem com pontilhado)
    ini = next(i for i, ls in enumerate(linhas) if R.sumario[0][0] in ls)
    pag = {}
    alvos = [(t, t) for t, _ in R.sumario] + [(t, t.split(' – ')[0] + ' –') for tp in R.listas.values() for t in tp]
    for chave, busca in alvos:
        for i in range(ini, len(linhas)):
            if any(l == busca or (busca.endswith('–') and l.startswith(busca)) for l in linhas[i]):
                pag[chave] = i  # índice 0 = capa, que não é contada: a página física i+1 recebe o número i
                break
    return pag, ini


import shutil, tempfile  # noqa: E402

R = construir({}, 1)
if shutil.which('soffice') and shutil.which('pdftotext'):
    with tempfile.TemporaryDirectory() as tmp:
        R.doc.save(f'{tmp}/r.docx')
        subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', tmp, f'{tmp}/r.docx'],
                       capture_output=True, check=True)
        pag, inicio = paginas(f'{tmp}/r.pdf', R)
    R = construir(pag, inicio)
    faltando = [t for t, _ in R.sumario if t not in pag] + [t for tp in R.listas.values() for t in tp if t not in pag]
    if faltando:
        print('aviso: página não encontrada para', faltando)
else:
    print('aviso: soffice/pdftotext ausentes; sumário e listas sem número de página (atualize no Word com F9)')
R.doc.save(SAIDA)
print('gerado', SAIDA)
