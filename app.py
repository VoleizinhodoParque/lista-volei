from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, time
import pytz

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///volei_list.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configurações de fuso horário
TIMEZONE = pytz.timezone('America/Sao_Paulo')

class Inscricao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    hora_inscricao = db.Column(db.DateTime, nullable=False)
    posicao = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'vaga' ou 'espera'

def resetar_lista():
    """Reseta a lista diariamente"""
    with app.app_context():
        # Remove todas as inscrições antigas
        Inscricao.query.delete()
        db.session.commit()

def verificar_disponibilidade():
    """Verifica quantas vagas e posições de espera estão disponíveis"""
    vagas = Inscricao.query.filter_by(status='vaga').count()
    espera = Inscricao.query.filter_by(status='espera').count()
    return vagas, espera

@app.route('/')
def index():
    # Verifica se é horário válido de inscrição
    now = datetime.now(TIMEZONE)
    horario_valido = (time(12, 0) <= now.time() <= time(23, 59))

    # Busca inscrições atuais
    vagas = Inscricao.query.filter_by(status='vaga').order_by(Inscricao.posicao).all()
    espera = Inscricao.query.filter_by(status='espera').order_by(Inscricao.posicao).all()

    return render_template('index.html', 
                           vagas=vagas, 
                           espera=espera, 
                           horario_valido=horario_valido)

@app.route('/inscrever', methods=['POST'])
def inscrever():
    nome = request.form.get('nome')
    now = datetime.now(TIMEZONE)

    # Verificar horário de inscrição
    if not (time(12, 0) <= now.time() <= time(23, 59)):
        return "Inscrições só são permitidas entre 12:00 e 23:59", 400

    # Verificar se já está inscrito
    existente = Inscricao.query.filter_by(nome=nome).first()
    if existente:
        return "Você já está inscrito", 400

    # Verificar vagas
    vagas_count, espera_count = verificar_disponibilidade()

    if vagas_count < 22:
        # Adiciona na lista de vagas
        nova_inscricao = Inscricao(
            nome=nome, 
            hora_inscricao=now, 
            posicao=vagas_count + 1, 
            status='vaga'
        )
        db.session.add(nova_inscricao)
    elif espera_count < 50:
        # Adiciona na lista de espera
        nova_inscricao = Inscricao(
            nome=nome, 
            hora_inscricao=now, 
            posicao=espera_count + 1, 
            status='espera'
        )
        db.session.add(nova_inscricao)
    else:
        return "Lista de vagas e espera estão completas", 400

    db.session.commit()
    return redirect(url_for('index'))

@app.route('/cancelar', methods=['POST'])
def cancelar():
    nome = request.form.get('nome')
    
    # Procura na lista de vagas
    inscricao = Inscricao.query.filter_by(nome=nome, status='vaga').first()
    
    if inscricao:
        # Remove da lista de vagas
        db.session.delete(inscricao)
        
        # Verifica se há alguém na lista de espera
        proxima_espera = Inscricao.query.filter_by(status='espera').order_by(Inscricao.hora_inscricao).first()
        
        if proxima_espera:
            # Move primeira pessoa da espera para vaga
            proxima_espera.status = 'vaga'
            proxima_espera.posicao = inscricao.posicao
        
        db.session.commit()
        return redirect(url_for('index'))
    
    # Procura na lista de espera
    inscricao_espera = Inscricao.query.filter_by(nome=nome, status='espera').first()
    
    if inscricao_espera:
        db.session.delete(inscricao_espera)
        db.session.commit()
        return redirect(url_for('index'))
    
    return "Inscrição não encontrada", 404

# Configurações para rodar o aplicativo
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

# Arquivo requirements.txt para dependências
# flask
# flask-sqlalchemy
# pytz