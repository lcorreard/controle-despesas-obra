import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import os
import hashlib
from fpdf import FPDF

# Configuração da página
st.set_page_config(page_title="Controle de Despesas - Obra", page_icon="🏗️", layout="wide")

# ==================== 🎨 CSS PERSONALIZADO ====================
st.markdown("""
<style>
    .stApp { background-color: #F2F2F2 !important; }
    h1, h2, h3, h4 { color: #BF1717 !important; font-weight: 800 !important; }
    label, [data-testid="stWidgetLabel"] p { color: #333333 !important; font-weight: 700 !important; font-size: 15px !important; }
    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stDateInput"] input, [data-testid="stTextArea"] textarea {
        background-color: #FFFFFF !important; border: 2px solid #BF1717 !important; color: #111111 !important;
        border-radius: 6px !important; padding: 10px 12px !important; font-size: 16px !important; font-weight: 600 !important;
    }
    [data-testid="stSelectbox"] > div > div, [data-testid="stMultiSelect"] > div > div {
        background-color: #FFFFFF !important; border: 2px solid #BF1717 !important; border-radius: 6px !important; color: #111111 !important;
    }
    [data-testid="stFileUploaderDropzone"] { background-color: #FFFFFF !important; border: 2px dashed #BF1717 !important; border-radius: 8px !important; }
    .stButton > button[kind="primary"], div.stButton > button:first-child {
        background-color: #BF1717 !important; color: #FFFFFF !important; border: 2px solid #BF1717 !important;
        font-weight: 700 !important; border-radius: 6px !important;
    }
    .stButton > button[kind="primary"]:hover { background-color: #991212 !important; border-color: #991212 !important; }
    .stButton > button {
        background-color: #FFFFFF !important; color: #BF1717 !important; border: 2px solid #BF1717 !important;
        font-weight: 700 !important; border-radius: 6px !important;
    }
    [data-testid="stAlert"] { background-color: #FFFFFF !important; border: 2px solid #BF1717 !important; border-radius: 6px !important; }
    [data-testid="stMetric"] { background-color: #FFFFFF !important; border: 2px solid #BF1717 !important; border-radius: 8px !important; padding: 12px !important; }
    [data-testid="stMetricValue"] { color: #BF1717 !important; font-weight: 800 !important; font-size: 2rem !important; }
    [data-testid="stMetricLabel"] { color: #333333 !important; font-weight: 700 !important; }
    .stTabs [data-baseweb="tab"] { font-weight: 700 !important; color: #A6A6A6 !important; border-bottom: 3px solid #A6A6A6 !important; }
    .stTabs [aria-selected="true"] { color: #BF1717 !important; border-bottom: 3px solid #BF1717 !important; }
    hr { border-color: #A6A6A6 !important; }
    .login-container {
        background-color: #FFFFFF; padding: 40px; border-radius: 12px; border: 3px solid #BF1717;
        max-width: 450px; margin: 80px auto; box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ==================== 🔐 FUNÇÕES DE SEGURANÇA ====================
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# ==================== 🖼️ FUNÇÃO PARA CARREGAR LOGO ====================
def carregar_logo_bytes():
    caminhos_possiveis = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "logomarca.png"),
        os.path.abspath("logomarca.png"),
        "logomarca.png"
    ]
    for caminho in caminhos_possiveis:
        if os.path.exists(caminho):
            try:
                with open(caminho, "rb") as f:
                    return f.read()
            except:
                continue
    return None

def exibir_logo(tamanho="pequeno"):
    logo_bytes = carregar_logo_bytes()
    if logo_bytes:
        if tamanho == "grande":
            st.image(logo_bytes, width=220)
        else:
            st.image(logo_bytes, width=90)
        return True
    return False

# ==================== 🗄️ BANCO DE DADOS ====================
@st.cache_resource
def conectar_banco():
    conn = sqlite3.connect('despesas.db', check_same_thread=False)
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS despesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_compra DATE NOT NULL,
            categoria TEXT NOT NULL,
            subgrupo TEXT,
            descricao TEXT NOT NULL,
            fornecedor TEXT NOT NULL,
            valor REAL NOT NULL,
            forma_pagamento TEXT NOT NULL,
            caminho_anexo TEXT,
            nome_arquivo TEXT,
            observacoes TEXT,
            quantidade REAL DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS subgrupos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT NOT NULL,
            nome TEXT NOT NULL,
            UNIQUE(categoria, nome)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            nome TEXT NOT NULL,
            pode_incluir INTEGER DEFAULT 1,
            pode_editar INTEGER DEFAULT 1,
            pode_excluir INTEGER DEFAULT 1,
            eh_admin INTEGER DEFAULT 0
        )
    ''')
    
    default_cats = ["Canteiro", "Alojamentos", "Transporte", "Outros"]
    for cat in default_cats:
        conn.execute("INSERT OR IGNORE INTO categorias (nome) VALUES (?)", (cat,))
    
    admin_existe = conn.execute("SELECT id FROM usuarios WHERE username = 'admin'").fetchone()
    if not admin_existe:
        conn.execute(
            "INSERT INTO usuarios (username, senha, nome, pode_incluir, pode_editar, pode_excluir, eh_admin) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ('admin', hash_senha('admin123'), 'Administrador', 1, 1, 1, 1)
        )
    
    # Migrações automáticas
    colunas_despesas = [row[1] for row in conn.execute("PRAGMA table_info(despesas)").fetchall()]
    if 'subgrupo' not in colunas_despesas:
        conn.execute("ALTER TABLE despesas ADD COLUMN subgrupo TEXT")
    if 'observacoes' not in colunas_despesas:
        conn.execute("ALTER TABLE despesas ADD COLUMN observacoes TEXT")
    if 'quantidade' not in colunas_despesas:
        conn.execute("ALTER TABLE despesas ADD COLUMN quantidade REAL DEFAULT 1")
    
    conn.commit()
    return conn

conn = conectar_banco()

# ==================== 📄 FUNÇÃO DE GERAÇÃO DE PDF (CABEÇALHO ALINHADO) ====================
def gerar_pdf_relatorio(df_despesas, titulo="Relatório de Despesas"):
    pdf = FPDF(orientation='L')  # Paisagem
    pdf.add_page()
    
    # ⭐ Definir fonte antes de qualquer cell()
    pdf.set_font('Helvetica', 'B', 14)
    
    # ⭐ CÁLCULO EXATO: A4 paisagem = 297mm, margens = 10mm cada lado = 277mm úteis
    margem = 10
    largura_total = 277  # Largura exata da área útil
    
    # 1. Barra vermelha com largura EXATA da área útil
    pdf.set_fill_color(191, 23, 23)
    pdf.set_xy(margem, 8)
    pdf.cell(largura_total, 12, '', fill=True)
    
    # 2. Título centralizado na barra vermelha
    pdf.set_xy(margem, 8)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(largura_total, 12, 'Sistema de Controle de Despesa - Obra', align='C')
    
    pdf.ln(15)
    
    # 3. Logo no canto superior esquerdo (fora da barra)
    logo_bytes = carregar_logo_bytes()
    if logo_bytes:
        pdf.image(logo_bytes, x=margem, y=24, w=22)
    
    # 4. Título do relatório CENTRALIZADO na página
    pdf.set_y(26)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 8, titulo.upper(), ln=True, align='C')
    
    # 5. Data de geração
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(0, 5, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(4)
    
    if df_despesas.empty:
        pdf.set_font('Helvetica', 'I', 10)
        pdf.cell(0, 8, 'Nenhuma despesa encontrada.', ln=True, align='C')
    else:
        # ⭐ LARGURAS RECALCULADAS para somar EXATAMENTE 277mm
        colunas = ['DATA', 'DESCRIÇÃO', 'QTD', 'CATEGORIA', 'SUBGRUPO', 'FORNECEDOR', 'PAGAMENTO', 'VALOR']
        larguras = [20, 80, 12, 25, 22, 70, 28, 20]  # Total = 277mm ✓
        
        pdf.set_fill_color(191, 23, 23)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Helvetica', 'B', 7)
        
        for col, larg in zip(colunas, larguras):
            pdf.cell(larg, 6, col, border=1, fill=True, align='C')
        pdf.ln()
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Helvetica', '', 6)
        
        for _, row in df_despesas.iterrows():
            data_fmt = pd.to_datetime(row['data_compra']).strftime('%d/%m/%Y')
            qtd = row.get('quantidade', 1)
            qtd_str = f"{int(qtd)}" if qtd == int(qtd) else f"{qtd:.2f}"
            
            valores = [
                data_fmt,
                str(row['descricao']).upper()[:50],
                qtd_str,
                str(row['categoria']).upper()[:18],
                str(row.get('subgrupo', '')).upper()[:18],
                str(row['fornecedor']).upper()[:38],
                str(row['forma_pagamento']).upper()[:18],
                f"R$ {row['valor']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            ]
            
            for val, larg in zip(valores, larguras):
                pdf.cell(larg, 5, str(val), border=1, align='C')
            pdf.ln()
        
        pdf.ln(2)
        total = df_despesas['valor'].sum()
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(191, 23, 23)
        pdf.cell(0, 6, f"TOTAL GERAL: R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), ln=True, align='R')
    
    pdf.ln(8)
    pdf.set_text_color(166, 166, 166)
    pdf.set_font('Helvetica', 'I', 7)
    pdf.cell(0, 5, 'Sistema de Controle de Despesa - Obra', ln=True, align='C')
    
    nome_arquivo = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    caminho = os.path.join("uploads", nome_arquivo)
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    pdf.output(caminho)
    
    return caminho, nome_arquivo

# ==================== 🧩 FUNÇÕES AUXILIARES ====================
def get_subgrupos(categoria):
    df = pd.read_sql_query("SELECT nome FROM subgrupos WHERE categoria = ? ORDER BY nome", conn, params=(categoria,))
    return df['nome'].tolist() if not df.empty else []

def get_todas_categorias():
    df = pd.read_sql_query("SELECT nome FROM categorias ORDER BY nome", conn)
    if df.empty:
        return ["Canteiro", "Alojamentos", "Transporte", "Outros"]
    return df['nome'].tolist()

def formatar_valor(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ==================== 🔐 TELA DE LOGIN ====================
def tela_login():
    st.markdown('<div class="login-container"></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    if not exibir_logo("grande"):
        st.title("🏗️ Controle de Despesas da Obra")
    
    st.subheader("🔐 Acesso ao Sistema")
    st.markdown("---")
    
    with st.form("form_login"):
        username = st.text_input("👤 Usuário", placeholder="Digite seu usuário")
        senha = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
        entrar = st.form_submit_button("Entrar", use_container_width=True, type="primary")
        
        if entrar:
            if not username or not senha:
                st.error("❌ Preencha usuário e senha!")
            else:
                usuario = pd.read_sql_query(
                    "SELECT * FROM usuarios WHERE username = ? AND senha = ?",
                    conn,
                    params=(username, hash_senha(senha))
                )
                
                if usuario.empty:
                    st.error("❌ Usuário ou senha incorretos!")
                else:
                    st.session_state.usuario_logado = {
                        'id': usuario.iloc[0]['id'],
                        'username': usuario.iloc[0]['username'],
                        'nome': usuario.iloc[0]['nome'],
                        'pode_incluir': bool(usuario.iloc[0]['pode_incluir']),
                        'pode_editar': bool(usuario.iloc[0]['pode_editar']),
                        'pode_excluir': bool(usuario.iloc[0]['pode_excluir']),
                        'eh_admin': bool(usuario.iloc[0]['eh_admin'])
                    }
                    st.session_state.msg_sucesso = f"✅ Bem-vindo, {st.session_state.usuario_logado['nome']}!"
                    st.rerun()

def logout():
    st.session_state.usuario_logado = None
    st.session_state.detalhes_compra_key = None
    st.session_state.editando_despesa_id = None
    st.session_state.editando_usuario_id = None
    st.rerun()

# ==================== 🏠 APLICAÇÃO PRINCIPAL ====================
def main():
    if 'usuario_logado' not in st.session_state or st.session_state.usuario_logado is None:
        tela_login()
        return
    
    usuario = st.session_state.usuario_logado
    
    if 'itens_compra' not in st.session_state:
        st.session_state.itens_compra = []
    if 'editando_item_idx' not in st.session_state:
        st.session_state.editando_item_idx = None
    if 'editando_despesa_id' not in st.session_state:
        st.session_state.editando_despesa_id = None
    if 'dados_compra' not in st.session_state:
        st.session_state.dados_compra = {'data': datetime.now().date(), 'fornecedor': '', 'forma_pagamento': 'Cartão Corporativo', 'observacoes': ''}
    if 'detalhes_compra_key' not in st.session_state:
        st.session_state.detalhes_compra_key = None
    if 'msg_sucesso' not in st.session_state:
        st.session_state.msg_sucesso = None
    if 'reset_seed' not in st.session_state:
        st.session_state.reset_seed = 0
    if 'editando_usuario_id' not in st.session_state:
        st.session_state.editando_usuario_id = None
    
    if st.session_state.msg_sucesso:
        st.success(st.session_state.msg_sucesso)
        st.session_state.msg_sucesso = None
    
    # Cabeçalho com logo pequena
    col_logo, col_info, col_logout = st.columns([1, 3, 1])
    with col_logo:
        if not exibir_logo("pequeno"):
            st.markdown("### 🏗️")
    with col_info:
        st.title("Controle de Despesas da Obra")
        st.caption(f"👤 Logado como: **{usuario['nome']}** ({usuario['username']})")
    with col_logout:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Sair", use_container_width=True):
            logout()
    
    st.markdown("---")
    
    abas = ["📋 Listar Despesas", "📊 Relatórios"]
    if usuario['pode_incluir']:
        abas.insert(0, "➕ Nova Despesa")
    if usuario['eh_admin']:
        abas.append("👥 Usuários")
    abas.append("⚙️ Configurações")
    
    tabs = st.tabs(abas)
    
    # ==================== ABA: NOVA DESPESA ====================
    if usuario['pode_incluir'] and "➕ Nova Despesa" in abas:
        with tabs[abas.index("➕ Nova Despesa")]:
            st.header("Registrar Nova Compra com Múltiplos Itens")
            
            seed = st.session_state.reset_seed
            
            col1, col2 = st.columns(2)
            with col1:
                data_compra = st.date_input("Data da Compra", value=st.session_state.dados_compra['data'], key=f"data_{seed}")
                fornecedor = st.text_input("Fornecedor", value=st.session_state.dados_compra['fornecedor'], placeholder="Ex: Loja do Zé", key=f"forn_{seed}")
            with col2:
                formas_pagto = ["Cartão Corporativo", "PIX", "Dinheiro", "Boleto", "Reembolso Pessoal"]
                idx_pagto = formas_pagto.index(st.session_state.dados_compra['forma_pagamento'])
                forma_pagamento = st.selectbox("Forma de Pagamento", formas_pagto, index=idx_pagto, key=f"pag_{seed}")
                arquivo = st.file_uploader("Anexar Nota Fiscal / Cupom", type=["pdf", "jpg", "jpeg", "png"], key=f"up_{seed}")
            
            observacoes = st.text_area("Observações (opcional)", value=st.session_state.dados_compra['observacoes'], placeholder="Ex: Compra realizada com desconto...", key=f"obs_{seed}")
            
            st.session_state.dados_compra = {'data': data_compra, 'fornecedor': fornecedor, 'forma_pagamento': forma_pagamento, 'observacoes': observacoes}
            st.markdown("---")
            
            st.subheader("📦 Itens da Compra")
            
            idx_atual = st.session_state.editando_item_idx
            item_atual = st.session_state.itens_compra[idx_atual] if idx_atual is not None else None
            
            key_cat = f"cat_{seed}_{idx_atual}"
            key_sub = f"sub_{seed}_{idx_atual}"
            key_desc = f"desc_{seed}_{idx_atual}"
            key_qtd = f"qtd_{seed}_{idx_atual}"
            key_val = f"val_{seed}_{idx_atual}"
            
            col1, col2 = st.columns(2)
            with col1:
                cats = get_todas_categorias()
                idx_cat = cats.index(item_atual['categoria']) if item_atual and item_atual['categoria'] in cats else 0
                categoria_item = st.selectbox("Categoria", cats, index=idx_cat, key=key_cat)
            with col2:
                subgrupos_disponiveis = get_subgrupos(categoria_item)
                opcoes_subgrupo = ["(Sem subgrupo)"] + subgrupos_disponiveis
                idx_sub = opcoes_subgrupo.index(item_atual['subgrupo']) if item_atual and item_atual['subgrupo'] in opcoes_subgrupo else 0
                subgrupo_item = st.selectbox("Subgrupo", opcoes_subgrupo, index=idx_sub, key=key_sub)
            
            col_desc, col_qtd, col_val = st.columns([3, 1, 1])
            with col_desc:
                descricao_item = st.text_input("Descrição do Item", value=item_atual['descricao'] if item_atual else "", placeholder="Ex: 50m de Fiação 2.5mm", key=key_desc)
            with col_qtd:
                quantidade_item = st.number_input("Qtd.", min_value=0.01, step=1.0, format="%.2f", 
                    value=item_atual.get('quantidade', 1) if item_atual else 1.0, key=key_qtd)
            with col_val:
                valor_item = st.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f", value=item_atual['valor'] if item_atual else 0.0, key=key_val)
            
            if idx_atual is not None:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Atualizar Item", use_container_width=True, type="primary"):
                        if descricao_item and valor_item > 0:
                            st.session_state.itens_compra[idx_atual] = {
                                "categoria": categoria_item, 
                                "subgrupo": subgrupo_item if subgrupo_item != "(Sem subgrupo)" else "", 
                                "descricao": descricao_item, 
                                "quantidade": quantidade_item,
                                "valor": valor_item
                            }
                            st.session_state.editando_item_idx = None
                            st.rerun()
                        else:
                            st.error("❌ Preencha a descrição e o valor!")
                with col2:
                    if st.button("❌ Cancelar", use_container_width=True):
                        st.session_state.editando_item_idx = None
                        st.rerun()
            else:
                if st.button("➕ Adicionar Item", use_container_width=True):
                    if descricao_item and valor_item > 0:
                        st.session_state.itens_compra.append({
                            "categoria": categoria_item, 
                            "subgrupo": subgrupo_item if subgrupo_item != "(Sem subgrupo)" else "", 
                            "descricao": descricao_item, 
                            "quantidade": quantidade_item,
                            "valor": valor_item
                        })
                        st.rerun()
                    else:
                        st.error("❌ Preencha a descrição e o valor do item!")
            
            st.markdown("---")
            
            if st.session_state.itens_compra:
                total_itens = sum(item['valor'] for item in st.session_state.itens_compra)
                st.metric("💰 Total dos Itens", formatar_valor(total_itens))
                
                h1, h2, h3, h4, h5 = st.columns([3, 1, 2, 1, 1])
                h1.markdown("**Descrição**")
                h2.markdown("**Qtd.**")
                h3.markdown("**Categoria / Subgrupo**")
                h4.markdown("**Valor**")
                h5.markdown("**Ação**")
                st.divider()
                
                for idx, item in enumerate(st.session_state.itens_compra):
                    c1, c2, c3, c4, c5 = st.columns([3, 1, 2, 1, 1])
                    c1.write(item['descricao'])
                    qtd_display = f"{int(item['quantidade'])}" if item['quantidade'] == int(item['quantidade']) else f"{item['quantidade']:.2f}"
                    c2.write(f"**{qtd_display}**")
                    c3.write(f"{item['categoria']}" + (f" / {item['subgrupo']}" if item['subgrupo'] else ""))
                    c4.write(formatar_valor(item['valor']))
                    
                    col_edit, col_del = c5.columns(2)
                    if usuario['pode_editar'] and col_edit.button("✏️", key=f"edit_{idx}", help="Editar"):
                        st.session_state.editando_item_idx = idx
                        st.rerun()
                    if usuario['pode_excluir'] and col_del.button("🗑️", key=f"del_{idx}", help="Excluir"):
                        st.session_state.itens_compra.pop(idx)
                        if st.session_state.editando_item_idx == idx: st.session_state.editando_item_idx = None
                        elif st.session_state.editando_item_idx and st.session_state.editando_item_idx > idx: st.session_state.editando_item_idx -= 1
                        st.rerun()
                
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Limpar Todos os Itens", use_container_width=True):
                        st.session_state.itens_compra = []
                        st.session_state.editando_item_idx = None
                        st.rerun()
                with col2:
                    if st.button("💾 Salvar Compra Completa", use_container_width=True, type="primary"):
                        if not fornecedor:
                            st.error("❌ Preencha o nome do fornecedor!")
                        else:
                            caminho_anexo = None
                            nome_arquivo = None
                            if arquivo is not None:
                                pasta_uploads = "uploads"
                                if not os.path.exists(pasta_uploads): os.makedirs(pasta_uploads)
                                nome_arquivo = f"{datetime.now().timestamp()}_{arquivo.name}"
                                caminho_anexo = os.path.join(pasta_uploads, nome_arquivo)
                                with open(caminho_anexo, "wb") as f: f.write(arquivo.getbuffer())
                            
                            for item in st.session_state.itens_compra:
                                conn.execute('INSERT INTO despesas (data_compra, categoria, subgrupo, descricao, fornecedor, valor, forma_pagamento, caminho_anexo, nome_arquivo, observacoes, quantidade) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                                    (data_compra, item['categoria'], item['subgrupo'], item['descricao'], fornecedor, item['valor'], forma_pagamento, caminho_anexo, nome_arquivo, observacoes, item['quantidade']))
                            conn.commit()
                            
                            st.session_state.msg_sucesso = "✅ Compra registrada com sucesso!"
                            st.session_state.itens_compra = []
                            st.session_state.editando_item_idx = None
                            st.session_state.dados_compra = {'data': datetime.now().date(), 'fornecedor': '', 'forma_pagamento': 'Cartão Corporativo', 'observacoes': ''}
                            st.session_state.reset_seed += 1 
                            st.rerun()
            else:
                st.warning("⚠️ Adicione pelo menos um item antes de salvar.")
    
    # ==================== ABA: LISTAR DESPESAS ====================
    with tabs[abas.index("📋 Listar Despesas")]:
        st.header("Despesas Registradas")
        
        if st.session_state.editando_despesa_id is not None:
            if not usuario['pode_editar']:
                st.error("❌ Você não tem permissão para editar despesas.")
                st.session_state.editando_despesa_id = None
                st.rerun()
            
            st.warning(f"✏️ **Editando despesa #{st.session_state.editando_despesa_id}**")
            despesa = pd.read_sql_query("SELECT * FROM despesas WHERE id = ?", conn, params=(st.session_state.editando_despesa_id,))
            
            if not despesa.empty:
                d = despesa.iloc[0]
                with st.form("form_editar_despesa"):
                    col1, col2 = st.columns(2)
                    with col1:
                        data_edit = st.date_input("Data da Compra", value=pd.to_datetime(d['data_compra']))
                        cats = get_todas_categorias()
                        idx_cat = cats.index(d['categoria']) if d['categoria'] in cats else 0
                        categoria_edit = st.selectbox("Categoria", cats, index=idx_cat)
                        subgrupos_edit = get_subgrupos(categoria_edit)
                        opcoes_sub = ["(Sem subgrupo)"] + subgrupos_edit
                        idx_s = opcoes_sub.index(d['subgrupo']) if d['subgrupo'] in opcoes_sub else 0
                        subgrupo_edit = st.selectbox("Subgrupo", opcoes_sub, index=idx_s)
                        fornecedor_edit = st.text_input("Fornecedor", value=d['fornecedor'])
                    with col2:
                        descricao_edit = st.text_input("Descrição", value=d['descricao'])
                        qtd_edit = st.number_input("Quantidade", min_value=0.01, step=1.0, format="%.2f", value=float(d.get('quantidade', 1)))
                        valor_edit = st.number_input("Valor (R$)", value=float(d['valor']), step=0.01, format="%.2f")
                        formas_pagto = ["Cartão Corporativo", "PIX", "Dinheiro", "Boleto", "Reembolso Pessoal"]
                        forma_pag_edit = st.selectbox("Forma de Pagamento", formas_pagto, index=formas_pagto.index(d['forma_pagamento']))
                    
                    obs_edit = st.text_area("Observações", value=d.get('observacoes', ''))
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 Salvar Alterações", use_container_width=True, type="primary"):
                            conn.execute('UPDATE despesas SET data_compra=?, categoria=?, subgrupo=?, descricao=?, fornecedor=?, valor=?, forma_pagamento=?, observacoes=?, quantidade=? WHERE id=?',
                                (data_edit, categoria_edit, subgrupo_edit if subgrupo_edit != "(Sem subgrupo)" else "", descricao_edit, fornecedor_edit, valor_edit, forma_pag_edit, obs_edit, qtd_edit, st.session_state.editando_despesa_id))
                            conn.commit()
                            st.session_state.editando_despesa_id = None
                            st.session_state.msg_sucesso = "✅ Despesa atualizada com sucesso!"
                            st.rerun()
                    with col2:
                        if st.form_submit_button("❌ Cancelar", use_container_width=True):
                            st.session_state.editando_despesa_id = None
                            st.rerun()

        elif st.session_state.detalhes_compra_key is not None:
            key = st.session_state.detalhes_compra_key
            itens = pd.read_sql_query("SELECT * FROM despesas WHERE data_compra=? AND fornecedor=? AND nome_arquivo=?", conn, params=key)
            
            if itens.empty:
                st.info("⚠️ Todos os itens desta compra foram excluídos.")
                if st.button("◀️ Voltar para a lista principal", use_container_width=True):
                    st.session_state.detalhes_compra_key = None
                    st.rerun()
            else:
                st.subheader("📋 Detalhes da Compra")
                col1, col2, col3 = st.columns(3)
                with col1: st.write(f"**Data:** {pd.to_datetime(itens.iloc[0]['data_compra']).strftime('%d/%m/%Y')}")
                with col2: st.write(f"**Fornecedor:** {itens.iloc[0]['fornecedor']}")
                with col3: st.write(f"**Pagamento:** {itens.iloc[0]['forma_pagamento']}")
                st.markdown("---")
                
                if itens.iloc[0]['observacoes']:
                    st.markdown(f"**📝 Observações:** {itens.iloc[0]['observacoes']}")
                    st.markdown("---")
                
                st.markdown("### Itens:")
                for _, item in itens.iterrows():
                    with st.container():
                        col_desc, col_qtd, col_val, col_acoes = st.columns([3, 1, 1, 1])
                        with col_desc:
                            st.write(f"**{item['descricao']}**")
                            st.caption(f"{item['categoria']}" + (f" / {item['subgrupo']}" if item['subgrupo'] else ""))
                        with col_qtd:
                            qtd_d = f"{int(item['quantidade'])}" if item['quantidade'] == int(item['quantidade']) else f"{item['quantidade']:.2f}"
                            st.write(f"**Qtd: {qtd_d}**")
                        with col_val: 
                            st.write(f"**{formatar_valor(item['valor'])}**")
                        with col_acoes:
                            if usuario['pode_editar'] and st.button("✏️", key=f"edit_{item['id']}", help="Editar"):
                                st.session_state.editando_despesa_id = item['id']
                                st.session_state.detalhes_compra_key = None
                                st.rerun()
                            if usuario['pode_excluir'] and st.button("🗑️", key=f"del_{item['id']}", help="Excluir"):
                                conn.execute("DELETE FROM despesas WHERE id = ?", (item['id'],))
                                conn.commit()
                                st.session_state.msg_sucesso = "✅ Item excluído com sucesso!"
                                st.rerun()
                        st.markdown("---")
                
                total = itens['valor'].sum()
                st.metric("💰 Total da Compra", formatar_valor(total))
                
                if itens.iloc[0]['caminho_anexo'] and os.path.exists(itens.iloc[0]['caminho_anexo']):
                    st.markdown("### 📎 Nota Fiscal")
                    with open(itens.iloc[0]['caminho_anexo'], "rb") as file:
                        st.download_button(label="📥 Baixar NF", data=file, file_name=itens.iloc[0]['nome_arquivo'], key="download_nf_detalhes")
                
                st.markdown("---")
                if st.button("◀️ Voltar para lista", use_container_width=True):
                    st.session_state.detalhes_compra_key = None
                    st.rerun()

        else:
            df = pd.read_sql_query("SELECT * FROM despesas ORDER BY data_compra DESC", conn)
            
            if df.empty:
                st.info("Nenhuma despesa registrada ainda.")
            else:
                df['data_fmt'] = pd.to_datetime(df['data_compra']).dt.strftime('%d/%m/%Y')
                compras = df.groupby(['data_compra', 'fornecedor', 'nome_arquivo']).agg({'valor': 'sum', 'forma_pagamento': 'first', 'id': 'count'}).reset_index()
                compras.columns = ['data_compra', 'fornecedor', 'nome_arquivo', 'total', 'forma_pagamento', 'qtd_itens']
                compras['data_fmt'] = pd.to_datetime(compras['data_compra']).dt.strftime('%d/%m/%Y')
                
                h1, h2, h3, h4, h5 = st.columns([2, 3, 2, 2, 1])
                h1.markdown("**Data**")
                h2.markdown("**Fornecedor**")
                h3.markdown("**Pagamento**")
                h4.markdown("**Total Gasto**")
                h5.markdown("**Ação**")
                st.divider()
                
                for _, compra in compras.iterrows():
                    c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 2, 1])
                    c1.text(compra['data_fmt'])
                    c2.text(compra['fornecedor'])
                    c3.text(compra['forma_pagamento'])
                    c4.text(formatar_valor(compra['total']))
                    
                    if c5.button("📋", key=f"det_{compra['data_compra']}_{compra['fornecedor']}_{compra['nome_arquivo']}", help="Ver Detalhes"):
                        st.session_state.detalhes_compra_key = (compra['data_compra'], compra['fornecedor'], compra['nome_arquivo'])
                        st.rerun()
                
                st.markdown("---")
                total_geral = df['valor'].sum()
                st.metric("💰 Total Geral Gasto", formatar_valor(total_geral))
    
    # ==================== ABA: RELATÓRIOS ====================
    with tabs[abas.index("📊 Relatórios")]:
        st.header("Relatórios e Filtros")
        col1, col2 = st.columns(2)
        with col1:
            filtro_categoria = st.multiselect("Filtrar por Categoria", options=get_todas_categorias())
        with col2:
            filtro_fornecedor = st.text_input("Filtrar por Fornecedor")
        
        query = "SELECT * FROM despesas WHERE 1=1"
        params = []
        if filtro_categoria:
            placeholders = ','.join(['?' for _ in filtro_categoria])
            query += f" AND categoria IN ({placeholders})"
            params.extend(filtro_categoria)
        if filtro_fornecedor:
            query += " AND fornecedor LIKE ?"
            params.append(f"%{filtro_fornecedor}%")
        query += " ORDER BY data_compra DESC"
        
        df_filtrado = pd.read_sql_query(query, conn, params=params)
        
        if df_filtrado.empty:
            st.warning("Nenhuma despesa encontrada com esses filtros.")
        else:
            df_filtrado['data_fmt'] = pd.to_datetime(df_filtrado['data_compra']).dt.strftime('%d/%m/%Y')
            df_filtrado['valor_fmt'] = df_filtrado['valor'].apply(formatar_valor)
            
            st.dataframe(df_filtrado[['data_fmt', 'categoria', 'subgrupo', 'descricao', 'fornecedor', 'valor_fmt', 'forma_pagamento']], use_container_width=True, hide_index=True)
            st.metric("💰 Total Filtrado", formatar_valor(df_filtrado['valor'].sum()))
            
            st.markdown("---")
            col_csv, col_pdf = st.columns(2)
            with col_csv:
                csv = df_filtrado.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Exportar para Excel/CSV", data=csv, file_name=f"relatorio_despesas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv", use_container_width=True)
            with col_pdf:
                caminho_pdf, nome_pdf = gerar_pdf_relatorio(df_filtrado, "Relatório de Despesas Filtrado")
                with open(caminho_pdf, "rb") as f:
                    st.download_button(label="📄 Gerar Relatório em PDF", data=f, file_name=nome_pdf, mime="application/pdf", use_container_width=True)
    
    # ==================== ABA: USUÁRIOS ====================
    if usuario['eh_admin'] and "👥 Usuários" in abas:
        with tabs[abas.index("👥 Usuários")]:
            st.header("👥 Gerenciamento de Usuários")
            st.info("💡 Aqui você pode criar novos usuários e definir suas permissões.")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("➕ Novo Usuário")
                with st.form("form_novo_usuario"):
                    novo_username = st.text_input("Usuário (login)", placeholder="Ex: joao.silva")
                    novo_nome = st.text_input("Nome Completo", placeholder="Ex: João da Silva")
                    nova_senha = st.text_input("Senha", type="password", placeholder="Mínimo 6 caracteres")
                    
                    st.markdown("**Permissões:**")
                    pode_incluir = st.checkbox("✅ Pode Incluir novas despesas", value=True)
                    pode_editar = st.checkbox("✅ Pode Editar despesas", value=True)
                    pode_excluir = st.checkbox("✅ Pode Excluir despesas", value=True)
                    
                    if st.form_submit_button("Cadastrar Usuário", use_container_width=True, type="primary"):
                        if not novo_username or not novo_nome or not nova_senha:
                            st.error("❌ Preencha todos os campos!")
                        elif len(nova_senha) < 6:
                            st.error("❌ A senha deve ter no mínimo 6 caracteres!")
                        else:
                            try:
                                conn.execute(
                                    "INSERT INTO usuarios (username, senha, nome, pode_incluir, pode_editar, pode_excluir, eh_admin) VALUES (?, ?, ?, ?, ?, ?, 0)",
                                    (novo_username, hash_senha(nova_senha), novo_nome, int(pode_incluir), int(pode_editar), int(pode_excluir))
                                )
                                conn.commit()
                                st.success(f"✅ Usuário '{novo_username}' criado com sucesso!")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("❌ Este nome de usuário já existe!")
            
            with col2:
                st.subheader("📋 Usuários Cadastrados")
                df_usuarios = pd.read_sql_query("SELECT * FROM usuarios ORDER BY username", conn)
                
                if not df_usuarios.empty:
                    for _, u in df_usuarios.iterrows():
                        with st.container():
                            st.markdown(f"""
                            <div style="background-color: white; padding: 12px; border-radius: 6px; border: 1px solid #A6A6A6; margin-bottom: 8px;">
                                <strong>👤 {u['nome']}</strong> ({u['username']})
                                {'<span style="color: #BF1717; font-weight: bold;">[ADMIN]</span>' if u['eh_admin'] else ''}
                                <br>
                                <small>
                                    {'✅ Incluir' if u['pode_incluir'] else '❌ Incluir'} | 
                                    {'✅ Editar' if u['pode_editar'] else '❌ Editar'} | 
                                    {'✅ Excluir' if u['pode_excluir'] else '❌ Excluir'}
                                </small>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if not u['eh_admin']:
                                col_perm, col_del = st.columns([3, 1])
                                with col_perm:
                                    if st.button("✏️ Permissões", key=f"perm_{u['id']}"):
                                        st.session_state.editando_usuario_id = u['id']
                                        st.rerun()
                                with col_del:
                                    if st.button("🗑️", key=f"del_user_{u['id']}"):
                                        conn.execute("DELETE FROM usuarios WHERE id = ?", (u['id'],))
                                        conn.commit()
                                        st.success(f"Usuário '{u['username']}' excluído!")
                                        st.rerun()
            
            if st.session_state.editando_usuario_id is not None:
                st.markdown("---")
                st.warning(f"✏️ **Editando permissões do usuário #{st.session_state.editando_usuario_id}**")
                
                user_edit = pd.read_sql_query("SELECT * FROM usuarios WHERE id = ?", conn, params=(st.session_state.editando_usuario_id,))
                if not user_edit.empty:
                    ue = user_edit.iloc[0]
                    with st.form("form_editar_usuario"):
                        st.write(f"**Usuário:** {ue['username']} - {ue['nome']}")
                        p_inc = st.checkbox("Pode Incluir", value=bool(ue['pode_incluir']))
                        p_edt = st.checkbox("Pode Editar", value=bool(ue['pode_editar']))
                        p_exc = st.checkbox("Pode Excluir", value=bool(ue['pode_excluir']))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Salvar Permissões", use_container_width=True, type="primary"):
                                conn.execute(
                                    "UPDATE usuarios SET pode_incluir=?, pode_editar=?, pode_excluir=? WHERE id=?",
                                    (int(p_inc), int(p_edt), int(p_exc), st.session_state.editando_usuario_id)
                                )
                                conn.commit()
                                st.session_state.editando_usuario_id = None
                                st.success("✅ Permissões atualizadas!")
                                st.rerun()
                        with col2:
                            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                                st.session_state.editando_usuario_id = None
                                st.rerun()
    
    # ==================== ABA: CONFIGURAÇÕES ====================
    with tabs[abas.index("⚙️ Configurações")]:
        st.header("⚙️ Configurações do Sistema")
        
        st.subheader("📂 Gerenciar Categorias")
        col1, col2 = st.columns([1, 2])
        with col1:
            with st.form("form_nova_categoria"):
                nova_cat = st.text_input("Nova Categoria", placeholder="Ex: Alimentação, EPIs")
                if st.form_submit_button("Adicionar Categoria", use_container_width=True):
                    if nova_cat:
                        try:
                            conn.execute("INSERT INTO categorias (nome) VALUES (?)", (nova_cat,))
                            conn.commit()
                            st.success(f"✅ Categoria '{nova_cat}' adicionada!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("❌ Esta categoria já existe!")
                    else:
                        st.error("❌ Preencha o nome da categoria!")
        
        with col2:
            st.write("**Categorias Atuais:**")
            cats_atuais = get_todas_categorias()
            for c in cats_atuais:
                col_c, col_d = st.columns([3, 1])
                col_c.write(f"• {c}")
                if col_d.button("🗑️", key=f"del_cat_{c}"):
                    subs = get_subgrupos(c)
                    if subs:
                        st.error(f"⚠️ Não é possível excluir '{c}' pois possui subgrupos. Exclua os subgrupos primeiro.")
                    else:
                        conn.execute("DELETE FROM categorias WHERE nome = ?", (c,))
                        conn.commit()
                        st.rerun()

        st.divider()

        st.subheader("📁 Gerenciar Subgrupos")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Adicionar Subgrupo:**")
            with st.form("form_subgrupo"):
                cats_para_sub = get_todas_categorias()
                categoria_nova = st.selectbox("Categoria", cats_para_sub)
                nome_subgrupo = st.text_input("Nome do Subgrupo", placeholder="Ex: Fiação, Tintas, Ferramentas")
                if st.form_submit_button("Adicionar Subgrupo", use_container_width=True):
                    if nome_subgrupo:
                        try:
                            conn.execute("INSERT INTO subgrupos (categoria, nome) VALUES (?, ?)", (categoria_nova, nome_subgrupo))
                            conn.commit()
                            st.success(f"✅ Subgrupo '{nome_subgrupo}' adicionado!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("❌ Este subgrupo já existe nesta categoria!")
                    else:
                        st.error("❌ Preencha o nome do subgrupo!")
        
        with col2:
            st.markdown("**Subgrupos Cadastrados:**")
            df_subgrupos = pd.read_sql_query("SELECT * FROM subgrupos ORDER BY categoria, nome", conn)
            if df_subgrupos.empty:
                st.info("Nenhum subgrupo cadastrado ainda.")
            else:
                for categoria in get_todas_categorias():
                    subgrupos_cat = df_subgrupos[df_subgrupos['categoria'] == categoria]
                    if not subgrupos_cat.empty:
                        st.markdown(f"**{categoria}:**")
                        for _, row in subgrupos_cat.iterrows():
                            col_a, col_b = st.columns([3, 1])
                            with col_a: st.write(f"• {row['nome']}")
                            with col_b:
                                if st.button("🗑️", key=f"del_sub_{row['id']}"):
                                    conn.execute("DELETE FROM subgrupos WHERE id = ?", (row['id'],))
                                    conn.commit()
                                    st.rerun()

    st.markdown("---")
    st.markdown("<p style='text-align: center; color: #A6A6A6; font-size: 13px;'>Sistema de Controle de Despesa - Obra</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()