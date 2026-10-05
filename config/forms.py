from datetime import date

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField,IntegerField,TextAreaField,SelectField
from wtforms import EmailField, TelField, DateField, RadioField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp,NumberRange,Optional, InputRequired, ValidationError
from flask_wtf.file import FileAllowed, FileRequired
from config.models import Ong, Usuario
from flask_wtf.recaptcha import RecaptchaField, Recaptcha

# Mensagens e validadores comuns aos cadastros (ISO 9241-17: mensagens claras, no idioma do usuário)
OBRIGATORIO = 'Campo obrigatório.'
EMAIL_INVALIDO = 'Informe um e-mail válido, ex.: nome@dominio.com.'
IMAGENS = ['jpg', 'png', 'jpeg']
IMAGEM_INVALIDA = 'Envie uma imagem JPG ou PNG.'
AJUDA_IMAGEM = 'Formatos aceitos: JPG ou PNG.'
AJUDA_DESCRICAO = 'Descreva a imagem para pessoas que usam leitor de tela (máx. 300 caracteres).'


def campo_cep():
    return StringField('CEP', description='8 dígitos, sem traço. Ex.: 58400000',
                       validators=[DataRequired(OBRIGATORIO), Regexp(r'^\d{8}$', message='O CEP deve ter 8 dígitos, sem traço.')],
                       render_kw=dict(maxlength=8, inputmode='numeric', placeholder='58400000', autocomplete='postal-code'))


def campo_numero():
    return StringField('Número', description='Somente dígitos.',
                       validators=[DataRequired(OBRIGATORIO), Regexp(r'^\d+$', message='O número deve conter apenas dígitos.')],
                       render_kw=dict(maxlength=10, inputmode='numeric', placeholder='123'))


def campo_ddd():
    return TelField('DDD', description='2 dígitos. Ex.: 83',
                    validators=[DataRequired(OBRIGATORIO), Regexp(r'^\d{2}$', message='O DDD deve ter 2 dígitos.')],
                    render_kw=dict(maxlength=2, inputmode='numeric', placeholder='83', autocomplete='tel-area-code'))


def campo_celular():
    return TelField('Celular', description='9 dígitos, sem traço. Ex.: 999998888',
                    validators=[DataRequired(OBRIGATORIO), Regexp(r'^\d{9}$', message='O celular deve ter 9 dígitos, sem traço.')],
                    render_kw=dict(maxlength=9, inputmode='numeric', placeholder='999998888', autocomplete='tel-local'))


def campo_senha():
    return PasswordField('Senha', description='Mínimo de 6 caracteres.',
                         validators=[DataRequired(OBRIGATORIO), Length(min=6, message='A senha deve ter no mínimo 6 caracteres.')],
                         render_kw=dict(minlength=6, autocomplete='new-password'))


def campo_confirmar_senha():
    return PasswordField('Confirmar senha', description='Repita a senha digitada acima.',
                         validators=[DataRequired(OBRIGATORIO), EqualTo('senha', message='As senhas não coincidem.')],
                         render_kw=dict(autocomplete='new-password'))


def campo_descricao_imagem(rotulo, obrigatorio=True):
    return TextAreaField(rotulo, description=AJUDA_DESCRICAO,
                         validators=[DataRequired(OBRIGATORIO) if obrigatorio else Optional(),
                                     Length(max=300, message='Máximo de 300 caracteres.')],
                         render_kw=dict(maxlength=300, rows=3))


class FormPT(FlaskForm):
    # mensagens padrão do WTForms em português (exige WTF_I18N_ENABLED = False no app)
    class Meta:
        locales = ['pt_BR', 'pt']


def maior_de_idade(form, field):
    hoje = date.today()
    nasc = field.data
    if nasc and (hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))) < 18:
        raise ValidationError('É preciso ter 18 anos ou mais para adotar.')



class cadastroForm(FormPT):
    # Dados pessoais
    primeiroNome = StringField('Primeiro nome', validators=[DataRequired(OBRIGATORIO), Length(max=100)],
                               render_kw=dict(maxlength=100, autocomplete='given-name'))
    sobrenome = StringField('Sobrenome', validators=[DataRequired(OBRIGATORIO), Length(max=100)],
                            render_kw=dict(maxlength=100, autocomplete='family-name'))
    data_nascimento = DateField('Data de nascimento', description='É preciso ter 18 anos ou mais.',
                                validators=[InputRequired(OBRIGATORIO), maior_de_idade],
                                render_kw=dict(autocomplete='bday', max=date.today().isoformat()))
    foto_perfil = FileField('Foto de perfil', description=AJUDA_IMAGEM,
                            validators=[FileRequired(OBRIGATORIO), FileAllowed(IMAGENS, IMAGEM_INVALIDA)],
                            render_kw=dict(accept='.jpg,.jpeg,.png'))
    descricao_foto_perfil = campo_descricao_imagem('Descrição da foto de perfil')

    # Endereço
    cep = campo_cep()
    rua = StringField('Rua', validators=[DataRequired(OBRIGATORIO), Length(max=150)],
                      render_kw=dict(maxlength=150, autocomplete='address-line1'))
    numero = campo_numero()
    complemento = StringField('Complemento', description='Opcional. Ex.: apto 101, bloco B.',
                              validators=[Optional(), Length(max=150)],
                              render_kw=dict(maxlength=150, autocomplete='address-line2'))

    # Contato
    ddd = campo_ddd()
    celular = campo_celular()

    # Acesso
    email = EmailField('E-mail', validators=[DataRequired(OBRIGATORIO), Email(EMAIL_INVALIDO)],
                       render_kw=dict(maxlength=150, placeholder='nome@dominio.com', autocomplete='email'))
    senha = campo_senha()
    senhaConfirmar = campo_confirmar_senha()
    declaracao = BooleanField('Declaro que as informações fornecidas são verdadeiras',
                              validators=[DataRequired('É preciso confirmar a declaração para se cadastrar.')])

    cadastrarBotao = SubmitField('Cadastrar')

class loginForm(FormPT):
    email = EmailField('E-mail', validators=[DataRequired(OBRIGATORIO), Email(EMAIL_INVALIDO)],
                       render_kw=dict(maxlength=150, placeholder='nome@dominio.com', autocomplete='email'))
    senha = PasswordField('Senha', validators=[DataRequired(OBRIGATORIO)], render_kw=dict(autocomplete='current-password'))
    recaptcha = RecaptchaField('Verificação de segurança',
                               validators=[Recaptcha('Marque a caixa "Não sou um robô" para continuar.')])
    loginBotao = SubmitField('Entrar')


class ResetPasswordForm(FormPT):
    # o e-mail vem do link enviado (token), não é digitado de novo
    senha = PasswordField('Nova senha', description='Mínimo de 6 caracteres.',
                          validators=[DataRequired(OBRIGATORIO), Length(min=6, message='A senha deve ter no mínimo 6 caracteres.')],
                          render_kw=dict(minlength=6, autocomplete='new-password'))
    senhaConfirmar = campo_confirmar_senha()
    redefinirBotao = SubmitField('Redefinir senha')


class sendLinkForm(FormPT):
    email = EmailField('E-mail', description='Use o e-mail informado no seu cadastro.',
                       validators=[DataRequired(OBRIGATORIO), Email(EMAIL_INVALIDO)],
                       render_kw=dict(maxlength=150, placeholder='nome@dominio.com', autocomplete='email'))
    sendBotao = SubmitField('Enviar link')

class profileForm(FlaskForm):
    editarBotao = SubmitField('Editar perfil')


class editPerfilForm1(cadastroForm):
    # mesmos campos do cadastro; foto e senha só mudam se forem preenchidas
    foto_perfil = FileField('Nova foto de perfil', description='Opcional: envie só se quiser trocar a foto atual. ' + AJUDA_IMAGEM,
                            validators=[FileAllowed(IMAGENS, IMAGEM_INVALIDA)], render_kw=dict(accept='.jpg,.jpeg,.png'))
    senha = PasswordField('Nova senha', description='Opcional: deixe em branco para manter a senha atual. Mínimo de 6 caracteres.',
                          validators=[Optional(), Length(min=6, message='A senha deve ter no mínimo 6 caracteres.')],
                          render_kw=dict(minlength=6, autocomplete='new-password'))
    senhaConfirmar = PasswordField('Confirmar nova senha', description='Repita a nova senha, se for trocá-la.',
                                   validators=[EqualTo('senha', message='As senhas não coincidem.')],
                                   render_kw=dict(autocomplete='new-password'))
    declaracao = None
    cadastrarBotao = None
    salvarBotao = SubmitField('Salvar alterações')


class cadastrar_OngForm(FormPT):
    # Dados da ONG
    nome_Ong = StringField('Nome da ONG', validators=[DataRequired(OBRIGATORIO), Length(max=100)],
                           render_kw=dict(maxlength=100, autocomplete='organization'))
    cnpj = StringField('CNPJ', description='14 dígitos, sem pontos ou barras. Ex.: 12345678000199',
                       validators=[DataRequired(OBRIGATORIO), Regexp(r'^\d{14}$', message='O CNPJ deve ter 14 dígitos, sem pontos ou barras.')],
                       render_kw=dict(maxlength=14, inputmode='numeric', placeholder='12345678000199'))
    fotoPerfilLogo = FileField('Logo da ONG', description='Opcional. ' + AJUDA_IMAGEM,
                               validators=[FileAllowed(IMAGENS, IMAGEM_INVALIDA)], render_kw=dict(accept='.jpg,.jpeg,.png'))
    descricao_foto_perfil_Logo = campo_descricao_imagem('Descrição da logo')

    # Endereço
    cep = campo_cep()
    rua = StringField('Rua', validators=[DataRequired(OBRIGATORIO), Length(max=150)], render_kw=dict(maxlength=150))
    numero = campo_numero()
    complemento = StringField('Complemento', description='Opcional.', validators=[Optional(), Length(max=150)],
                              render_kw=dict(maxlength=150))

    # Contato
    ddd = campo_ddd()
    celular = campo_celular()
    instagram = StringField('Instagram', description='Ex.: @minhaong',
                            validators=[DataRequired(OBRIGATORIO), Length(max=50)],
                            render_kw=dict(maxlength=50, placeholder='@minhaong'))

    # Doações
    dados_bancarios = TextAreaField('Dados bancários', description='Banco, agência e conta (máx. 100 caracteres).',
                                    validators=[DataRequired(OBRIGATORIO), Length(max=100, message='Máximo de 100 caracteres.')],
                                    render_kw=dict(maxlength=100, rows=2, placeholder='Banco 001 - Ag. 1234 - CC 56789-0'))
    fotoQrCode = FileField('QR code do PIX', description='Opcional. ' + AJUDA_IMAGEM,
                           validators=[FileAllowed(IMAGENS, IMAGEM_INVALIDA)], render_kw=dict(accept='.jpg,.jpeg,.png'))
    descricao_fotoqrCode = TextAreaField('Descrição do QR code',
                                         description='Opcional. Se ficar vazio, usaremos "Essa imagem é o QR code do PIX da ONG <nome>".',
                                         validators=[Optional(), Length(max=300, message='Máximo de 300 caracteres.')],
                                         render_kw=dict(maxlength=300, rows=2))

    # Acesso
    email = EmailField('E-mail', validators=[DataRequired(OBRIGATORIO), Email(EMAIL_INVALIDO)],
                       render_kw=dict(maxlength=150, placeholder='contato@minhaong.org'))
    senha = campo_senha()
    senhaConfirmar = campo_confirmar_senha()

    cadastrarBotao = SubmitField('Cadastrar ONG')


class AnimalForm(FormPT):
    nome = StringField('Nome do animal', validators=[DataRequired(OBRIGATORIO), Length(min=2, max=100, message='O nome deve ter entre 2 e 100 caracteres.')],
                       render_kw=dict(maxlength=100))
    # poucas opções fixas: botões de rádio deixam todas visíveis
    especie = RadioField('Espécie', choices=[('gato', 'Gato'), ('cachorro', 'Cachorro'), ('outro', 'Outro')],
                         validators=[DataRequired(OBRIGATORIO)])
    tamanho = RadioField('Porte', choices=[('pequeno', 'Pequeno'), ('medio', 'Médio'), ('grande', 'Grande')],
                         validators=[DataRequired(OBRIGATORIO)])
    # InputRequired: idade 0 (filhote com menos de 1 ano) é válida
    idade = IntegerField('Idade (em anos)', description='De 0 a 30. Use 0 para filhotes com menos de 1 ano.',
                         validators=[InputRequired(OBRIGATORIO), NumberRange(min=0, max=30, message='Informe uma idade entre 0 e 30 anos.')],
                         render_kw=dict(min=0, max=30, step=1))
    descricao = TextAreaField('Descrição', description='Temperamento, saúde, vacinas... (máx. 300 caracteres).',
                              validators=[DataRequired(OBRIGATORIO), Length(max=300, message='Máximo de 300 caracteres.')],
                              render_kw=dict(maxlength=300, rows=4))
    status = RadioField('Status', choices=[('disponível', 'Disponível'), ('adotado', 'Adotado'), ('reservado', 'Reservado')],
                        default='disponível', validators=[DataRequired(OBRIGATORIO)])
    castrado = BooleanField('Animal castrado')

    foto1 = FileField('Foto principal', description=AJUDA_IMAGEM,
                      validators=[FileRequired(OBRIGATORIO), FileAllowed(IMAGENS, IMAGEM_INVALIDA)], render_kw=dict(accept='.jpg,.jpeg,.png'))
    descricao_foto1 = campo_descricao_imagem('Descrição da foto principal')
    foto2 = FileField('Foto 2', description='Opcional. ' + AJUDA_IMAGEM,
                      validators=[FileAllowed(IMAGENS, IMAGEM_INVALIDA)], render_kw=dict(accept='.jpg,.jpeg,.png'))
    descricao_foto2 = campo_descricao_imagem('Descrição da foto 2', obrigatorio=False)
    foto3 = FileField('Foto 3', description='Opcional. ' + AJUDA_IMAGEM,
                      validators=[FileAllowed(IMAGENS, IMAGEM_INVALIDA)], render_kw=dict(accept='.jpg,.jpeg,.png'))
    descricao_foto3 = campo_descricao_imagem('Descrição da foto 3', obrigatorio=False)
    foto4 = FileField('Foto 4', description='Opcional. ' + AJUDA_IMAGEM,
                      validators=[FileAllowed(IMAGENS, IMAGEM_INVALIDA)], render_kw=dict(accept='.jpg,.jpeg,.png'))
    descricao_foto4 = campo_descricao_imagem('Descrição da foto 4', obrigatorio=False)

    cadastrarBotao = SubmitField('Cadastrar animal')

    def validate(self, extra_validators=None):
        ok = super().validate(extra_validators)
        # foto opcional enviada exige descrição; checa todas para mostrar todos os erros de uma vez
        for i in range(2, 5):
            if getattr(self, f'foto{i}').data and not getattr(self, f'descricao_foto{i}').data:
                getattr(self, f'descricao_foto{i}').errors.append('Descreva a foto enviada.')
                ok = False
        return ok


class editAnimalForm(AnimalForm):
    # mesmos campos do cadastro; a foto principal só é trocada se uma nova for enviada
    foto1 = FileField('Nova foto principal', description='Opcional: envie só se quiser trocar a foto atual. ' + AJUDA_IMAGEM,
                      validators=[FileAllowed(IMAGENS, IMAGEM_INVALIDA)], render_kw=dict(accept='.jpg,.jpeg,.png'))
    # opções variam com os interessados no animal (preenchidas na rota): lista suspensa
    adotante = SelectField('Adotante', coerce=int, choices=[(0, 'Nenhum')],
                           description='Pessoas que demonstraram interesse no animal. Usado quando o status é Adotado ou Reservado.')
    cadastrarBotao = None
    salvarBotao = SubmitField('Salvar alterações')
