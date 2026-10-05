from random import randint

from flask import Flask, render_template, request, redirect, flash, url_for, current_app
from sqlalchemy import text
from werkzeug.utils import secure_filename
import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, UserMixin, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, BadSignature
from flask_migrate import Migrate
import base64
from flask_socketio import SocketIO, join_room, leave_room, send

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SECRET_KEY'] = 'JHBJDJMBDKJ677898'

#professora
#template app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://nome_do_user_mysql:senha_do_user@localhost/PetMatch'


#joana
#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://petuser:87Amore;;w34@localhost/PetMatch'
# de madu
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Mylooksql2024@localhost/PetMatch'
# URI vem do ambiente (ex.: mysql+pymysql://user:senha@localhost/PetMatch); sem ela usa SQLite local
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
# TESTING=1 desliga o reCAPTCHA do login em ambiente local
app.config['TESTING'] = os.environ.get('TESTING') == '1'
# deixa o WTForms usar as próprias traduções (FormPT em config/forms.py)
app.config['WTF_I18N_ENABLED'] = False
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

socketio = SocketIO(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

app.config['RECAPTCHA_PUBLIC_KEY'] = '6LdumXQqAAAAACTj9aFwLpEszVahxWSWTpItn9qj'
app.config['RECAPTCHA_PRIVATE_KEY'] = '6LdumXQqAAAAAEPJFVgv-sHxpeTE5KOdvjAM-HE7'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Servidor SMTP do Gmail
app.config['MAIL_PORT'] = 587  # Porta para TLS
app.config['MAIL_USE_TLS'] = True  # Habilita TLS
app.config['MAIL_USE_SSL'] = False  # Não usa SSL
app.config['MAIL_USERNAME'] = 'petmatch.adm@gmail.com'
# app.config['MAIL_PASSWORD'] = 'eett34;;'
app.config['MAIL_PASSWORD'] = 'kuya dzya toli ygpz'
mail = Mail(app)
s = URLSafeTimedSerializer(app.secret_key)

from config.models import Usuario, Admin, Ong, Animal, Mensagem, InteresseAnimal, Adocao
from config.forms import cadastroForm, loginForm, ResetPasswordForm, sendLinkForm, profileForm, editPerfilForm1, \
    cadastrar_OngForm, AnimalForm, editAnimalForm


@login_manager.user_loader
def load_user(user_id):
    # Tenta carregar como Usuario
    user = Usuario.query.get(int(user_id))
    if user:
        return user

    # Tenta carregar como Admin
    user = Admin.query.get(int(user_id))
    if user:
        return user

    # Tenta carregar como Ong
    return Ong.query.get(int(user_id))


# Rota de teste para verificar a conexão com o banco de dados
@app.route('/test_db')
def test_db():
    try:
        #  consulta simples
        result = db.session.execute(text('SELECT 1'))
        return "Conexão com o banco de dados bem-sucedida!"
    except Exception as e:
        return f"Erro ao conectar ao banco de dados: {e}"


# Rotas gerais
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = loginForm()
    if form.validate_on_submit():
        # usuário, admin e ONG compartilham a mesma tela de login
        for modelo, destino, boas_vindas in ((Usuario, 'profile', 'Login bem-sucedido!'),
                                             (Admin, 'admin_dashboard', 'Login bem-sucedido! Bem-vindo, administrador.'),
                                             (Ong, 'ong_dashboard', 'Login bem-sucedido! Bem-vinda, ONG.')):
            conta = modelo.query.filter_by(email=form.email.data).first()
            if conta and conta.check_password(form.senha.data):
                login_user(conta)
                flash(boas_vindas, 'success')
                return redirect(url_for(destino))
        # mensagem única: não revela se o e-mail existe
        form.senha.errors.append('E-mail ou senha incorretos. Confira os dados e tente novamente.')

    return render_template('auth/login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu da sua conta.', 'success')
    return redirect(url_for('login'))


@app.route('/')
@app.route('/home')
def home():
    return render_template('geral/index.html')


@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    form = cadastroForm()
    valido = form.validate_on_submit()
    if valido and Usuario.query.filter_by(email=form.email.data).first():
        form.email.errors.append('Este e-mail já está cadastrado. Faça login ou use outro e-mail.')
    elif valido:
        print("Formulário validado")
        # hasheando a senha antes de salvar
        senha_hash = generate_password_hash(form.senha.data)

        # inicializa a variável para o caminho da foto do perfil
        foto_perfil_path = None

        # verifica se uma imagem foi enviada
        if form.foto_perfil.data:
            # Salva a imagem na pasta de uploads
            filename = secure_filename(form.foto_perfil.data.filename)
            foto_perfil_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.foto_perfil.data.save(foto_perfil_path)

        # criando novo usuário
        novo_usuario = Usuario(
            primeiro_nome=form.primeiroNome.data,
            sobrenome=form.sobrenome.data,
            email=form.email.data,
            senha=senha_hash,  # Senha hasheada
            telefone=form.celular.data,
            rua=form.rua.data,
            complemento=form.complemento.data or '',
            cep=form.cep.data,
            numero=form.numero.data,
            ddd=form.ddd.data,
            celular=form.celular.data,
            data_nascimento=form.data_nascimento.data,
            foto_perfil=foto_perfil_path,  # Caminho da imagem
            descricao_foto_perfil=form.descricao_foto_perfil.data
        )

        # adiciona usuário no bd
        db.session.add(novo_usuario)
        db.session.commit()

        flash('Cadastro realizado com sucesso! Entre com seu e-mail e senha.', 'success')
        return redirect(url_for('login'))
    else:
        print("Formulário inválido:", form.errors)
    return render_template('auth/cadastro.html', form=form)


@app.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    form = sendLinkForm()
    if form.validate_on_submit():
        email = form.email.data
        if Usuario.query.filter_by(email=email).first():
            token = s.dumps(email, salt='email-confirm')
            link = url_for('redefinir', token=token, _external=True)
            msg = Message('Redefinição de Senha', sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.body = f'Seu link para redefinir a senha é: {link}\nO link vale por 1 hora.'
            try:
                mail.send(msg)
            except Exception as e:
                print('Falha ao enviar e-mail:', e)
                flash('Não foi possível enviar o e-mail agora. Tente novamente em alguns minutos.', 'danger')
                return render_template('user_pages/recuperarSenha.html', form=form)
        # mesma resposta para e-mail cadastrado ou não: não revela quem tem conta
        flash(f'Se {email} estiver cadastrado, você receberá em instantes um link para redefinir a senha. '
              'O link vale por 1 hora.', 'success')
        return redirect(url_for('recuperar'))

    return render_template('user_pages/recuperarSenha.html', form=form)


@app.route('/redefinir', methods=['GET', 'POST'])
def redefinir():
    token = request.args.get('token', '')
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
    except BadSignature:  # inclui link expirado
        flash('Este link de redefinição é inválido ou expirou. Peça um novo link abaixo.', 'danger')
        return redirect(url_for('recuperar'))

    user = Usuario.query.filter_by(email=email).first_or_404()
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.senha = generate_password_hash(form.senha.data)
        db.session.commit()
        flash('Sua senha foi redefinida com sucesso! Entre com a nova senha.', 'success')
        return redirect(url_for('login'))

    return render_template('user_pages/redefinirSenha.html', form=form, email=email, token=token)


@app.route('/chats', methods=['GET', 'POST'])
@login_required
def allchats():
    # buscar todos os chats do usuário em interesses
    if isinstance(current_user, Usuario):

        chats = InteresseAnimal.query.filter_by(usuario_id=current_user.id).all()
    elif isinstance(current_user, Ong):
        # se for uma ONG buscar os chats relacionados aos animais daquela ONG
        chats = InteresseAnimal.query.join(Animal).filter(Animal.ong_id == current_user.id).all()
    else:
        chats = []

    return render_template('user_pages/allChats.html', chats=chats)


@app.route('/chat/<numero_unico>', methods=['GET'])
@login_required
def chat_por_numero(numero_unico):
    interesse = InteresseAnimal.query.filter_by(numero_unico=numero_unico).first_or_404()
    animal = Animal.query.get_or_404(interesse.animal_id)
    ong = Ong.query.get_or_404(animal.ong_id)

    # Verificar permissões
    if isinstance(current_user, Usuario):
        if interesse.usuario_id != current_user.id:
            return redirect(url_for('home'))
    elif isinstance(current_user, Ong):
        if animal.ong_id != current_user.id:
            return redirect(url_for('home'))

    mensagens = Mensagem.query.filter_by(room_id=animal.id).order_by(Mensagem.timestamp.asc()).all()

    return render_template('geral/chat.html', animal=animal, ong=ong, user=current_user, mensagens=mensagens)


@app.route('/interesse/<int:animal_id>', methods=['POST'])
@login_required
def interesse_animal(animal_id):
    animal = Animal.query.get_or_404(animal_id)
    if isinstance(current_user, Usuario):
        # verificar se o usuário já tem interesse registrado
        interesse_existente = InteresseAnimal.query.filter_by(usuario_id=current_user.id, animal_id=animal.id).first()
        if not interesse_existente:
            # gerar número aleatório único
            while True:
                numero_unico = str(randint(100000, 999999))  # Gera número de 6 dígitos
                if not InteresseAnimal.query.filter_by(numero_unico=numero_unico).first():
                    break

            # novo registro de interesse
            interesse = InteresseAnimal(usuario_id=current_user.id, animal_id=animal.id, numero_unico=numero_unico)
            db.session.add(interesse)
            db.session.commit()

            return redirect(url_for('chat_por_numero', numero_unico=numero_unico))
        else:
            return redirect(url_for('chat_por_numero', numero_unico=interesse_existente.numero_unico))


@socketio.on('join_room')
def handle_join_room(data):
    join_room(data)
    if isinstance(current_user, Usuario):
        send(f'{current_user.primeiro_nome} entrou na sala.', to=data)
    elif isinstance(current_user, Ong):
        send(f'{current_user.nome_Ong} entrou na sala.', to=data)


@socketio.on('send_message')
def handle_send_message(data):
    room = data['room']
    message = data['message']
    sender_name = data['senderName']

    # Salvar a mensagem no bd
    nova_mensagem = Mensagem(
        message=message,
        sender_name=sender_name,
        room_id=room
    )
    db.session.add(nova_mensagem)
    db.session.commit()

    #print(f'Mensagem de {sender_name} na sala {room}: {message}')

    # Envia a mensagem
    socketio.emit('receive_message', {'message': message, 'senderName': sender_name}, to=room)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = profileForm()
    if isinstance(current_user, Usuario):
        #  histórico de adoções
        adocoes = Adocao.query.filter_by(usuario_id=current_user.id).all()
        return render_template('user_pages/profile.html', form=form, adocoes=adocoes)
    # if form.validate_on_submit():
    #     return redirect(url_for('edit_profile'))
    else:
        return "Unauthorized access", 403


# campo do formulário -> atributo do usuário
CAMPOS_PERFIL = dict(primeiroNome='primeiro_nome', sobrenome='sobrenome', data_nascimento='data_nascimento',
                     descricao_foto_perfil='descricao_foto_perfil', cep='cep', rua='rua', numero='numero',
                     complemento='complemento', ddd='ddd', celular='celular', email='email')


@app.route('/profile/edit', methods=[ 'POST','GET'])
@login_required
def edit_profile():
    if not isinstance(current_user, Usuario):
        return "Unauthorized access", 403
    form = editPerfilForm1()

    # dados já conhecidos vêm preenchidos
    if request.method == 'GET':
        for campo, attr in CAMPOS_PERFIL.items():
            form[campo].data = getattr(current_user, attr)

    valido = form.validate_on_submit()
    if valido and Usuario.query.filter(Usuario.email == form.email.data, Usuario.id != current_user.id).first():
        form.email.errors.append('Este e-mail já está em uso por outra conta.')
    elif valido:
        for campo, attr in CAMPOS_PERFIL.items():
            setattr(current_user, attr, form[campo].data)
        current_user.complemento = form.complemento.data or ''
        current_user.telefone = form.celular.data

        # Atualizar a foto de perfil, se fornecida
        if form.foto_perfil.data:
            # Remover a foto antiga se existir
            if current_user.foto_perfil and os.path.exists(current_user.foto_perfil):
                os.remove(current_user.foto_perfil)

            filename = secure_filename(form.foto_perfil.data.filename)
            foto_perfil_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.foto_perfil.data.save(foto_perfil_path)
            current_user.foto_perfil = foto_perfil_path

        # Atualizar a senha, se fornecida
        if form.senha.data:
            current_user.senha = generate_password_hash(form.senha.data)

        db.session.commit()
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('profile'))
    else:
        print("Formulário inválido:", form.errors)

    return render_template('user_pages/edit.html', form=form)


@app.route('/petsList')
def petsList():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    especie = request.args.get('especie')
    tamanho = request.args.get('tamanho')
    idade = request.args.get('idade')  # Obter filtro de idade


    query = Animal.query.filter(Animal.status != 'adotado')  # Exclui animais adotados
    if especie:
        query = query.filter_by(especie=especie)
    if tamanho:
        query = query.filter_by(tamanho=tamanho)
    if idade:
        query = query.filter(Animal.idade <= int(idade))  # filtra animais com idade menor ou igual

    animais = query.paginate(page=page, per_page=per_page, error_out=False)
    total_pages = animais.pages

    return render_template(
        'geral/petsList.html',
        animal=animais.items,
        page=page,
        total_pages=total_pages,
        especie=especie,
        tamanho=tamanho,
        idade=idade
    )


@app.route('/petsList/<int:animal_id>')
def animalDetail(animal_id):
    animal = Animal.query.get_or_404(animal_id)
    ong = Ong.query.get(animal.ong_id)
    user_type = "Usuario" if isinstance(current_user, Usuario) else "Ong"

    return render_template('geral/animalDetail.html', animal=animal, ong=ong, user=current_user, user_type=user_type)


@app.route('/ongsList')
def ongsList():
    page = request.args.get('page', 1, type=int)  # Obter o número da página da requisição
    per_page = 5
    ongs = Ong.query.paginate(page=page, per_page=per_page, error_out=False)  # Consultar ONGs no banco de dados
    total_pages = ongs.pages

    return render_template('geral/ongsList.html', ongs=ongs.items, page=page, total_pages=total_pages)

# ROTAS DO ADMIN

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():

    #print(isinstance(current_user, Admin))

    if isinstance(current_user, Admin):
        usuarios = Usuario.query.all()
        ongs = Ong.query.all()
        animais = Animal.query.all()
        return render_template('admin_pages/admin_dashboard.html', usuarios=usuarios, ongs=ongs, animais=animais)
    else:
        print("Acesso negado. Somente administradores podem acessar esta página.")

        return redirect(url_for('home'))


@app.route('/admin_dashboard/ongs_register', methods=['GET', 'POST'])
@login_required
def ongs_register():
    # garantir que o usuário logado é um administrador
    if isinstance(current_user, Admin):
        form = cadastrar_OngForm()

        valido = form.validate_on_submit()
        if valido and Ong.query.filter_by(email=form.email.data).first():
            form.email.errors.append('Já existe uma ONG cadastrada com este e-mail.')
        elif valido:
            print("Formulário validado")

            # Hasheando a senha antes de salvar
            senha_hash = generate_password_hash(form.senha.data)

            foto_qr_code_path = None
            foto_perfil_path = None

            if form.fotoQrCode.data:
                filename_qr = secure_filename(form.fotoQrCode.data.filename)
                foto_qr_code_path = os.path.join(app.config['UPLOAD_FOLDER'], filename_qr)
                form.fotoQrCode.data.save(foto_qr_code_path)

            if form.fotoPerfilLogo.data:
                filename_logo = secure_filename(form.fotoPerfilLogo.data.filename)
                foto_perfil_path = os.path.join(app.config['UPLOAD_FOLDER'], filename_logo)
                form.fotoPerfilLogo.data.save(foto_perfil_path)

            # nova ONG
            nova_ong = Ong(
                nome_Ong=form.nome_Ong.data,
                email=form.email.data,
                senha=senha_hash,  # Senha hasheada
                telefone=form.celular.data,
                rua=form.rua.data,
                complemento=form.complemento.data or '',
                cep=form.cep.data,
                numero=form.numero.data,
                ddd=form.ddd.data,
                celular=form.celular.data,
                foto_perfil_Logo=foto_perfil_path,
                foto_qrCode=foto_qr_code_path,
                cnpj=form.cnpj.data,
                instagram=form.instagram.data,
                dados_bancarios=form.dados_bancarios.data,
                descricao_foto_perfil_Logo=form.descricao_foto_perfil_Logo.data,
                # valor padrão editável: só é usado se o admin deixar o campo vazio
                descricao_foto_qrCode=form.descricao_fotoqrCode.data or f"Essa imagem é o QR code do PIX da ONG {form.nome_Ong.data}"
            )

            db.session.add(nova_ong)
            db.session.commit()

            flash(f'ONG "{nova_ong.nome_Ong}" cadastrada com sucesso!', 'success')

            return redirect(url_for('admin_dashboard'))

        else:
            print("Formulário inválido:", form.errors)

        return render_template('admin_pages/ongs_register.html', form=form)

    else:

        return redirect(url_for('home'))


# ROTAS DA ONG

@app.route('/ong_dashboard')
@login_required
def ong_dashboard():

    #print(isinstance(current_user, Ong))

    if isinstance(current_user, Ong):
        # Aqui você pode adicionar dados que deseja exibir no dashboard

        animais = Animal.query.filter_by(ong_id=current_user.id).all()
        return render_template('ongs_pages/ong_dashboard.html', animais=animais)
    else:
        #print("Acesso negado. Somente Ongs podem acessar esta página.")

        return redirect(url_for('home'))


@app.route('/ong_dashboard/pets_register', methods=['GET', 'POST'])
@login_required
def pets_register():

    if isinstance(current_user, Ong):
        form = AnimalForm()

        if form.validate_on_submit():
            # diretório de upload
            upload_folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)

            # salva as imagens e o caminho no banco de dados
            foto_paths = []
            for i in range(1, 5):
                foto = getattr(form, f'foto{i}').data
                if foto:
                    filename = secure_filename(foto.filename)
                    foto_path = os.path.join(upload_folder, filename)
                    foto.save(foto_path)
                    foto_paths.append(foto_path)  # caminho para o banco
                else:
                    foto_paths.append(None)

            # novo animal
            novo_animal = Animal(
                nome=form.nome.data,
                especie=form.especie.data,
                tamanho=form.tamanho.data,
                idade=form.idade.data,
                descricao=form.descricao.data,
                status=form.status.data,
                castrado=form.castrado.data,
                foto1=foto_paths[0],
                foto2=foto_paths[1],
                foto3=foto_paths[2],
                foto4=foto_paths[3],
                descricao_foto1=form.descricao_foto1.data,
                descricao_foto2=form.descricao_foto2.data,
                descricao_foto3=form.descricao_foto3.data,
                descricao_foto4=form.descricao_foto4.data,
                ong_id=current_user.id
            )

            db.session.add(novo_animal)
            db.session.commit()

            flash(f'Animal "{novo_animal.nome}" cadastrado com sucesso!', 'success')

            return redirect(url_for('ong_dashboard'))
        else:
            print("Formulário inválido:", form.errors)

        return render_template('ongs_pages/pets_register.html', form=form)

    else:

        return redirect(url_for('home'))


@app.route('/ong_dashboard/pets_delete/<int:id>', methods=['POST'])
@login_required
def delete_animal(id):
    if isinstance(current_user, Ong):
        animal = Animal.query.get_or_404(id)  # busca o animal pelo ID

        # exclui as imagens do animal
        for foto_path in [animal.foto1, animal.foto2, animal.foto3, animal.foto4]:
            if foto_path and os.path.exists(foto_path):
                os.remove(foto_path)

        db.session.delete(animal)  # exclui o animal do banco de dados
        db.session.commit()
        flash('Animal excluído com sucesso!', 'success')
        return redirect(url_for('ong_dashboard'))
    else:

        return redirect(url_for('home'))




@app.route('/ong_dashboard/pets_edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_animal(id):
    if isinstance(current_user, Ong):
        animal = Animal.query.get_or_404(id)  # Busca o animal pelo ID
        if animal.ong_id != current_user.id:  # só a ONG dona edita o animal
            return "Unauthorized access", 403
        form = editAnimalForm()

        # possiveis adotantes com os users que tem interesse registrado em tal pet
        interessados = Usuario.query.join(InteresseAnimal, Usuario.id == InteresseAnimal.usuario_id) \
            .filter(InteresseAnimal.animal_id == animal.id).all()
        form.adotante.choices = [(0, 'Nenhum')] + [(usuario.id, f'{usuario.primeiro_nome} {usuario.sobrenome}') for
                                                   usuario in interessados]

        campos = ['nome', 'especie', 'tamanho', 'idade', 'descricao', 'status', 'castrado',
                  'descricao_foto1', 'descricao_foto2', 'descricao_foto3', 'descricao_foto4']
        if request.method == 'GET':
            for campo in campos:
                form[campo].data = getattr(animal, campo)
            form.adotante.data = animal.adocao.usuario.id if animal.adocao else 0

        if form.validate_on_submit():
            for campo in campos:
                setattr(animal, campo, form[campo].data)

            # atualiza ou cria uma adoção
            adotante_id = form.adotante.data
            if adotante_id != 0:  # Caso um adotante tenha sido selecionado
                if animal.adocao:
                    animal.adocao.usuario_id = adotante_id
                else:  # Cria uma nova adoção
                    nova_adocao = Adocao(usuario_id=adotante_id, animal_id=animal.id)
                    db.session.add(nova_adocao)
            else:
                if animal.adocao:
                    db.session.delete(animal.adocao)

            # atualiza as fotos se novas forem enviadas
            for i, foto_field in enumerate([form.foto1, form.foto2, form.foto3, form.foto4], start=1):
                if foto_field.data:
                    # Deleta a imagem antiga, se existir
                    foto_atual = getattr(animal, f'foto{i}')
                    if foto_atual and os.path.exists(foto_atual):
                        os.remove(foto_atual)

                    filename = secure_filename(foto_field.data.filename)
                    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    foto_field.data.save(path)
                    setattr(animal, f'foto{i}', path)

            db.session.commit()
            flash(f'Animal "{animal.nome}" atualizado com sucesso!', 'success')
            return redirect(url_for('ong_dashboard'))  # Redireciona para o dashboard da ONG

        return render_template('ongs_pages/pets_edit.html', form=form, animal=animal)
    else:

        return redirect(url_for('home'))

#