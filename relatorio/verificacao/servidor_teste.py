"""Sobe o app com banco limpo e dados de teste (TESTING=1). Uso, na raiz do projeto: python relatorio/verificacao/servidor_teste.py PORTA"""
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DATABASE_URL', 'sqlite:///caps.db'); os.environ['TESTING'] = '1'
from werkzeug.security import generate_password_hash as h
from datetime import date
from app import app, db, socketio, s
from config.models import Admin, Ong, Usuario, Animal, InteresseAnimal
with app.app_context():
    db.drop_all(); db.create_all()
    db.session.add(Admin(id=1001, nome='Admin Teste', email='admin@teste.com', senha=h('123')))
    db.session.add(Ong(id=2001, nome_Ong='ONG Teste', email='ong@teste.com', senha=h('123'), telefone='999999999',
        rua='Rua A', complemento='', cep='58400000', instagram='@ongteste', cnpj='12345678000199', numero='10',
        ddd='83', celular='999999999', dados_bancarios='Banco 001 Ag 1 CC 1',
        descricao_foto_perfil_Logo='Logo', descricao_foto_qrCode='QR'))
    u = dict(id=3001, primeiro_nome='Ana', sobrenome='Silva', email='ana@teste.com', senha=h('123'), telefone='999998888',
             rua='Rua das Flores', complemento='Apto 101', cep='58400000', numero='25', ddd='83', celular='999998888',
             foto_perfil='static/assets/pets/pet 1.jpg', descricao_foto_perfil='Ana sorrindo')
    if hasattr(Usuario, 'data_nascimento'): u['data_nascimento'] = date(1990, 5, 1)
    db.session.add(Usuario(**u))
    a = dict(id=4001, nome='Tico', especie='gato', tamanho='pequeno', idade=0, descricao='Filhote dócil e brincalhão.',
             status='disponível', foto1='static/assets/pets/pet 2.jpg', descricao_foto1='Gato cinza deitado', ong_id=2001)
    if hasattr(Animal, 'castrado'): a['castrado'] = True
    db.session.add(Animal(**a))
    db.session.commit()
    open(f"token_{sys.argv[1]}.txt", 'w').write(s.dumps('ana@teste.com', salt='email-confirm'))
socketio.run(app, port=int(sys.argv[1]), allow_unsafe_werkzeug=True)
