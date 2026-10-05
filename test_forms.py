"""Teste dos 8 formulários (ISO 9241-17). Uso: python test_forms.py"""
import io
import os
import re
from datetime import date

os.environ.update(DATABASE_URL='sqlite:///test.db', TESTING='1')

from werkzeug.security import generate_password_hash
from app import app, db, mail
from config.models import Admin, Animal, Ong, Usuario

app.config['WTF_CSRF_ENABLED'] = False
PNG = b'\x89PNG\r\n\x1a\n' + b'0' * 16
criados = []


def imagem():
    nome = f'test_{len(criados)}.png'
    criados.append(os.path.join(app.config['UPLOAD_FOLDER'], nome))
    return io.BytesIO(PNG), nome


def usuario(**extra):
    dados = dict(primeiroNome='Ana', sobrenome='Silva', data_nascimento='1990-05-01', foto_perfil=imagem(),
                 descricao_foto_perfil='Ana sorrindo', cep='58400000', rua='Rua A', numero='10', complemento='',
                 ddd='83', celular='999998888', email='ana@teste.com', senha='segredo1', senhaConfirmar='segredo1',
                 declaracao='y')
    dados.update(extra)
    return dados


def ong(**extra):
    dados = dict(nome_Ong='ONG Nova', cnpj='12345678000199', descricao_foto_perfil_Logo='Logo', cep='58400000',
                 rua='Rua B', numero='20', ddd='83', celular='988887777', instagram='@nova',
                 dados_bancarios='Banco 001', email='nova@teste.com', senha='segredo1', senhaConfirmar='segredo1')
    dados.update(extra)
    return dados


def links_ok(html):
    # todo link do resumo de erros aponta para um elemento existente
    alvos = re.findall(r'<li><a href="#([^"]+)">', html)
    assert alvos and all(f'id="{a}"' in html for a in alvos), alvos
    assert 'novalidate' in html and 'Not a valid' not in html and 'This field' not in html
    return alvos


def login(c, email):
    c.get('/logout')
    return c.post('/login', data=dict(email=email, senha='123'))


with app.app_context():
    db.drop_all(); db.create_all()
    db.session.add(Admin(id=1001, nome='Admin', email='admin@t.com', senha=generate_password_hash('123')))
    db.session.commit()
    c = app.test_client()
    try:
        # usuário: cadastro válido grava data de nascimento e complemento é opcional
        r = c.post('/cadastro', data=usuario(), content_type='multipart/form-data')
        assert r.status_code == 302, r.data
        assert Usuario.query.one().data_nascimento == date(1990, 5, 1)

        # usuário: e-mail duplicado mostra erro no campo e mantém os dados digitados
        r = c.post('/cadastro', data=usuario(primeiroNome='Outra'), content_type='multipart/form-data')
        html = r.data.decode()
        assert r.status_code == 200 and 'Este e-mail já está cadastrado' in html and 'value="Outra"' in html

        # usuário: menor de idade e termos não aceitos são rejeitados, com resumo de erros
        r = c.post('/cadastro', data=usuario(email='b@t.com', data_nascimento=f'{date.today().year - 10}-01-01',
                                             declaracao=''), content_type='multipart/form-data')
        html = r.data.decode()
        assert '18 anos ou mais' in html and 'confirmar a declaração' in html and 'resumo-erros' in html
        assert 'novalidate' in html and 'digite a senha novamente' in html

        # mensagens padrão do WTForms em português (data inválida)
        html = c.post('/cadastro', data=usuario(data_nascimento='abc')).data.decode()
        assert 'Not a valid' not in html and 'A data não é válida' in html

        # ONG: cadastro válido com flash; descrição do QR code recebe o padrão
        login(c, 'admin@t.com')
        r = c.post('/admin_dashboard/ongs_register', data=ong(), follow_redirects=True)
        assert 'cadastrada com sucesso' in r.data.decode()
        assert Ong.query.one().descricao_foto_qrCode == 'Essa imagem é o QR code do PIX da ONG ONG Nova'

        # ONG: e-mail duplicado não redireciona em silêncio
        r = c.post('/admin_dashboard/ongs_register', data=ong(nome_Ong='Dup'))
        assert r.status_code == 200 and 'Já existe uma ONG cadastrada com este e-mail' in r.data.decode()

        # animal: idade 0 (filhote) é aceita; radios de espécie/porte gravam o valor
        o = Ong.query.one(); o.senha = generate_password_hash('123'); db.session.commit()
        login(c, 'nova@teste.com')
        r = c.post('/ong_dashboard/pets_register', content_type='multipart/form-data', follow_redirects=True,
                   data=dict(nome='Tico', especie='gato', tamanho='pequeno', idade='0', descricao='Dócil',
                             status='disponível', castrado='y', foto1=imagem(), descricao_foto1='Gato cinza'))
        assert 'cadastrado com sucesso' in r.data.decode(), r.data.decode()[:2000]
        a = Animal.query.one()
        assert (a.idade, a.especie, a.tamanho, a.castrado) == (0, 'gato', 'pequeno', True)

        # animal: foto opcional sem descrição gera erro no campo
        r = c.post('/ong_dashboard/pets_register', content_type='multipart/form-data',
                   data=dict(nome='Rex', especie='cachorro', tamanho='grande', idade='3', descricao='Brincalhão',
                             status='disponível', foto1=imagem(), descricao_foto1='Cão', foto2=imagem()))
        assert 'Descreva a foto enviada' in r.data.decode()

        # animal: todo link do resumo de erros aponta para um elemento existente (inclui grupos de rádio)
        html = c.post('/ong_dashboard/pets_register', data={}).data.decode()
        alvos = re.findall(r'<li><a href="#([^"]+)">', html)
        assert {'especie', 'tamanho'} <= set(alvos), alvos
        assert all(f'id="{a}"' in html for a in alvos), alvos
        assert 'Not a valid' not in c.post('/ong_dashboard/pets_register', data=dict(idade='x', especie='peixe')).data.decode()

        # editar animal: dados atuais preenchidos (radio, checkbox), salva sem exigir nova foto
        html = c.get(f'/ong_dashboard/pets_edit/{a.id}').data.decode()
        assert 'value="Tico"' in html and re.search(r'value="gato"[^>]*checked|checked[^>]*value="gato"', html), html[:3000]
        foto_antiga = a.foto1
        r = c.post(f'/ong_dashboard/pets_edit/{a.id}', follow_redirects=True,
                   data=dict(nome='Tico', especie='gato', tamanho='medio', idade='0', descricao='Dócil',
                             status='reservado', adotante='0', descricao_foto1='Gato cinza'))
        assert 'atualizado com sucesso' in r.data.decode()
        db.session.refresh(a)
        assert (a.tamanho, a.idade, a.castrado, a.foto1) == ('medio', 0, False, foto_antiga)
        alvos = links_ok(c.post(f'/ong_dashboard/pets_edit/{a.id}', data={}).data.decode())
        assert {'especie', 'tamanho'} <= set(alvos)

        # editar animal: outra ONG não edita
        db.session.add(Ong(nome_Ong='Outra', email='outra@t.com', senha=generate_password_hash('123'), telefone='1',
                           rua='R', complemento='', cep='58400000', instagram='@o', cnpj='1' * 14, numero='1', ddd='83',
                           celular='999999999', dados_bancarios='B', descricao_foto_perfil_Logo='L',
                           descricao_foto_qrCode='Q'))
        db.session.commit()
        login(c, 'outra@t.com')
        assert c.get(f'/ong_dashboard/pets_edit/{a.id}').status_code == 403

        # login: credencial errada gera uma única mensagem, sem revelar se o e-mail existe
        c.get('/logout')
        html = c.post('/login', data=dict(email='ana@teste.com', senha='errada')).data.decode()
        assert html.count('E-mail ou senha incorretos') == 2 and 'não encontrado' not in html  # campo + resumo
        links_ok(html)
        assert 'id="resumo-erros"' in c.post('/login', data={}).data.decode()

        # editar perfil: dados atuais preenchidos; salvar sem foto e sem senha mantém as atuais
        u = Usuario.query.filter_by(email='ana@teste.com').one()
        u.senha = generate_password_hash('123'); db.session.commit()
        foto_antiga, senha_antiga = u.foto_perfil, u.senha
        login(c, 'ana@teste.com')
        html = c.get('/profile/edit').data.decode()
        assert all(v in html for v in ('value="Ana"', 'value="58400000"', 'value="1990-05-01"'))
        perfil = {k: v for k, v in usuario(primeiroNome='Ana Maria').items()
                  if k not in ('foto_perfil', 'senha', 'senhaConfirmar', 'declaracao')}
        r = c.post('/profile/edit', data=perfil, follow_redirects=True)
        assert 'Perfil atualizado com sucesso' in r.data.decode()
        db.session.refresh(u)
        assert (u.primeiro_nome, u.foto_perfil, u.senha) == ('Ana Maria', foto_antiga, senha_antiga)

        # editar perfil: e-mail de outra conta e senha curta/diferente são recusados com resumo
        c.post('/cadastro', data=usuario(email='z@t.com'), content_type='multipart/form-data')
        html = c.post('/profile/edit', data=dict(perfil, email='z@t.com')).data.decode()
        assert 'já está em uso por outra conta' in html
        html = c.post('/profile/edit', data=dict(perfil, senha='abc', senhaConfirmar='abd')).data.decode()
        assert 'no mínimo 6 caracteres' in html and 'não coincidem' in html and 'se ia trocá-las' in html
        links_ok(html)

        # recuperar senha: mesma resposta para e-mail cadastrado ou não; link enviado só ao cadastrado
        c.get('/logout')
        with mail.record_messages() as enviados:
            r1 = c.post('/recuperar', data=dict(email='ninguem@t.com'), follow_redirects=True).data.decode()
            r2 = c.post('/recuperar', data=dict(email='ana@teste.com'), follow_redirects=True).data.decode()
        assert 'receberá em instantes um link' in r1 and 'receberá em instantes um link' in r2
        assert len(enviados) == 1
        links_ok(c.post('/recuperar', data=dict(email='abc')).data.decode())

        # redefinir senha: exige token válido; e-mail vem do token
        r = c.get('/redefinir?token=falso', follow_redirects=True).data.decode()
        assert 'inválido ou expirou' in r
        link = re.search(r'(/redefinir\?token=\S+)', enviados[0].body).group(1)
        assert 'ana@teste.com' in c.get(link).data.decode()
        links_ok(c.post(link, data=dict(senha='123456', senhaConfirmar='654321')).data.decode())
        r = c.post(link, data=dict(senha='nova123', senhaConfirmar='nova123'), follow_redirects=True)
        assert 'redefinida com sucesso' in r.data.decode()
        db.session.refresh(u)
        assert u.check_password('nova123')

        # sessão expirada (token CSRF inválido) é informada, não silenciosa
        app.config['WTF_CSRF_ENABLED'] = True
        html = c.post('/cadastro', data=usuario(email='c@t.com'), content_type='multipart/form-data').data.decode()
        app.config['WTF_CSRF_ENABLED'] = False
        assert 'Sua sessão expirou' in html and 'Corrija' not in html, html
        print('OK: 8 formulários conformes')
    finally:
        db.session.remove(); db.drop_all()
        for f in criados + [os.path.join(app.instance_path, 'test.db')]:
            if os.path.exists(f):
                os.remove(f)
