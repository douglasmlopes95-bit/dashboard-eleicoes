import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

# ======================
# Configuração do banco
# ======================
conn = sqlite3.connect("eleicoes.db", check_same_thread=False)
c = conn.cursor()

# Criação das tabelas
c.execute('''CREATE TABLE IF NOT EXISTS deputados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT,
                tipo TEXT
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS membros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT,
                votos INTEGER,
                cargo TEXT,
                percentual REAL,
                deputado_federal_id INTEGER,
                deputado_estadual_id INTEGER,
                FOREIGN KEY (deputado_federal_id) REFERENCES deputados(id),
                FOREIGN KEY (deputado_estadual_id) REFERENCES deputados(id)
            )''')
conn.commit()

# ======================
# Funções auxiliares
# ======================
def add_deputado(nome, tipo):
    c.execute("INSERT INTO deputados (nome, tipo) VALUES (?, ?)", (nome, tipo))
    conn.commit()

def get_deputados(tipo=None):
    if tipo:
        return pd.read_sql(f"SELECT * FROM deputados WHERE tipo = ?", conn, params=(tipo,))
    return pd.read_sql("SELECT * FROM deputados", conn)

def update_deputado(dep_id, nome, tipo):
    c.execute("UPDATE deputados SET nome=?, tipo=? WHERE id=?", (nome, tipo, dep_id))
    conn.commit()

def delete_deputado(dep_id):
    c.execute("DELETE FROM deputados WHERE id=?", (dep_id,))
    conn.commit()

def add_membro(nome, votos, cargo, percentual, dep_federal, dep_estadual):
    c.execute("""INSERT INTO membros 
              (nome, votos, cargo, percentual, deputado_federal_id, deputado_estadual_id)
              VALUES (?, ?, ?, ?, ?, ?)""",
              (nome, votos, cargo, percentual, dep_federal, dep_estadual))
    conn.commit()

def get_membros():
    return pd.read_sql("""SELECT m.id, m.nome, m.votos, m.cargo, m.percentual,
                          df.id AS deputado_federal_id, df.nome AS deputado_federal,
                          de.id AS deputado_estadual_id, de.nome AS deputado_estadual
                          FROM membros m
                          LEFT JOIN deputados df ON m.deputado_federal_id = df.id
                          LEFT JOIN deputados de ON m.deputado_estadual_id = de.id""", conn)

def update_membro(mem_id, nome, votos, cargo, percentual, dep_federal, dep_estadual):
    c.execute("""UPDATE membros 
                 SET nome=?, votos=?, cargo=?, percentual=?, deputado_federal_id=?, deputado_estadual_id=?
                 WHERE id=?""",
              (nome, votos, cargo, percentual, dep_federal, dep_estadual, mem_id))
    conn.commit()

def delete_membro(mem_id):
    c.execute("DELETE FROM membros WHERE id=?", (mem_id,))
    conn.commit()

# ======================
# Interface Streamlit
# ======================
st.set_page_config(page_title="Dashboard Eleições 2026", layout="wide")
st.title("📊 Dashboard Eleições 2026")

menu = st.sidebar.radio("Menu", ["Cadastrar Deputados", "Cadastrar Membros", "Dashboard"])

# ======================
# Cadastro e edição de Deputados
# ======================
if menu == "Cadastrar Deputados":
    st.subheader("➕ Adicionar Deputado")

    with st.form("form_deputado", clear_on_submit=True):
        nome = st.text_input("Nome do deputado")
        tipo = st.radio("Tipo", ["Federal", "Estadual"])
        salvar = st.form_submit_button("Salvar Deputado")

    if salvar and nome:
        add_deputado(nome, tipo)
        st.success(f"✅ Deputado {nome} ({tipo}) cadastrado com sucesso!")

    st.write("📋 Deputados cadastrados:")
    deputados = get_deputados()
    st.dataframe(deputados)

    if not deputados.empty:
        dep_options = deputados["id"].tolist()
        dep_display = deputados["nome"].tolist()
        sel = st.selectbox("Selecione um Deputado para editar/excluir", options=list(range(len(dep_options))),
                           format_func=lambda i: f"{dep_display[i]} (id: {dep_options[i]})")
        dep_id = dep_options[sel]
        dep_data = deputados[deputados["id"] == dep_id].iloc[0]

        with st.expander("✏️ Editar Deputado"):
            with st.form("edit_dep_form", clear_on_submit=False):
                novo_nome = st.text_input("Nome", dep_data["nome"])
                novo_tipo = st.radio("Tipo", ["Federal", "Estadual"], index=0 if dep_data["tipo"] == "Federal" else 1)
                atualizar = st.form_submit_button("Atualizar")
            if atualizar:
                update_deputado(dep_id, novo_nome, novo_tipo)
                st.success("✅ Deputado atualizado!")
                st.experimental_rerun()

        if st.button("🗑️ Excluir Deputado"):
            delete_deputado(dep_id)
            st.warning("🚨 Deputado excluído!")
            st.experimental_rerun()

# ======================
# Cadastro e edição de Membros
# ======================
elif menu == "Cadastrar Membros":
    st.subheader("➕ Adicionar Membro da Equipe")

    deputados_fed_df = get_deputados("Federal")
    deputados_est_df = get_deputados("Estadual")

    fed_options = deputados_fed_df["nome"].tolist() if not deputados_fed_df.empty else []
    est_options = deputados_est_df["nome"].tolist() if not deputados_est_df.empty else []

    with st.form("form_membro", clear_on_submit=True):
        nome = st.text_input("Nome do membro")
        votos = st.number_input("Votos", min_value=0, step=1)
        cargo = st.text_input("Cargo")
        percentual = st.number_input("% de votos (ex.: 40 para 40%)", min_value=0.0, step=0.1, format="%.2f")

        if fed_options:
            dep_fed_sel = st.selectbox("Deputado Federal", fed_options)
        else:
            dep_fed_sel = None
            st.info("Nenhum deputado federal cadastrado. Cadastre um em 'Cadastrar Deputados'.")

        if est_options:
            dep_est_sel = st.selectbox("Deputado Estadual", est_options)
        else:
            dep_est_sel = None
            st.info("Nenhum deputado estadual cadastrado. Cadastre um em 'Cadastrar Deputados'.")

        salvar = st.form_submit_button("Salvar Membro")

    if salvar and nome and dep_fed_sel and dep_est_sel:
        dep_fed_id = deputados_fed_df.loc[deputados_fed_df["nome"] == dep_fed_sel, "id"].values[0]
        dep_est_id = deputados_est_df.loc[deputados_est_df["nome"] == dep_est_sel, "id"].values[0]
        add_membro(nome, votos, cargo, percentual, dep_fed_id, dep_est_id)
        st.success(f"✅ Membro {nome} cadastrado com sucesso!")

    st.write("📋 Membros cadastrados:")
    membros = get_membros()

    if not membros.empty:
        membros["votos"] = pd.to_numeric(membros["votos"]).fillna(0)
        membros["percentual"] = pd.to_numeric(membros["percentual"]).fillna(0)
        membros["votos_convertidos"] = (membros["votos"] * membros["percentual"] / 100).round(2)
        st.dataframe(membros[["id", "nome", "votos", "percentual", "votos_convertidos", "cargo", "deputado_federal", "deputado_estadual"]])
    else:
        st.info("⚠️ Nenhum membro cadastrado ainda.")

    # Edit / Delete membro
    if not membros.empty:
        mem_options = membros["id"].tolist()
        mem_display = membros["nome"].tolist()
        sel_mem = st.selectbox("Selecione um Membro para editar/excluir", options=list(range(len(mem_options))),
                               format_func=lambda i: f"{mem_display[i]} (id: {mem_options[i]})")
        mem_id = mem_options[sel_mem]
        mem_data = membros[membros["id"] == mem_id].iloc[0]

        with st.expander("✏️ Editar Membro"):
            with st.form("edit_mem_form", clear_on_submit=False):
                novo_nome = st.text_input("Nome", mem_data["nome"])
                novos_votos = st.number_input("Votos", min_value=0, value=int(mem_data["votos"]))
                novo_cargo = st.text_input("Cargo", mem_data["cargo"])
                novo_percentual = st.number_input("% de votos (ex.: 40 para 40%)", min_value=0.0, value=float(mem_data["percentual"]), format="%.2f")

                fed_options = deputados_fed_df["nome"].tolist() if not deputados_fed_df.empty else []
                est_options = deputados_est_df["nome"].tolist() if not deputados_est_df.empty else []

                fed_default_idx = fed_options.index(mem_data["deputado_federal"]) if mem_data["deputado_federal"] in fed_options else 0
                est_default_idx = est_options.index(mem_data["deputado_estadual"]) if mem_data["deputado_estadual"] in est_options else 0

                dep_fed = st.selectbox("Deputado Federal", fed_options, index=fed_default_idx)
                dep_est = st.selectbox("Deputado Estadual", est_options, index=est_default_idx)

                atualizar = st.form_submit_button("Atualizar")
            if atualizar:
                dep_fed_id = deputados_fed_df.loc[deputados_fed_df["nome"] == dep_fed, "id"].values[0]
                dep_est_id = deputados_est_df.loc[deputados_est_df["nome"] == dep_est, "id"].values[0]
                update_membro(mem_id, novo_nome, novos_votos, novo_cargo, novo_percentual, dep_fed_id, dep_est_id)
                st.success("✅ Membro atualizado!")
                st.experimental_rerun()

        if st.button("🗑️ Excluir Membro"):
            delete_membro(mem_id)
            st.warning("🚨 Membro excluído!")
            st.experimental_rerun()

# ======================
# Dashboard
# ======================
elif menu == "Dashboard":
    st.subheader("📊 Relatórios e Análises")

    df = get_membros()
    if df.empty:
        st.info("⚠️ Nenhum membro cadastrado ainda.")
    else:
        # normaliza colunas numéricas e calcula votos convertidos
        df["votos"] = pd.to_numeric(df["votos"]).fillna(0)
        df["percentual"] = pd.to_numeric(df["percentual"]).fillna(0)
        df["votos_convertidos"] = (df["votos"] * df["percentual"] / 100).round(2)

        deputados_fed_df = get_deputados("Federal")
        deputados_est_df = get_deputados("Estadual")

        default_fed = deputados_fed_df.iloc[0]["nome"] if not deputados_fed_df.empty else "Sem deputado federal"
        default_est = deputados_est_df.iloc[0]["nome"] if not deputados_est_df.empty else "Sem deputado estadual"

        # Forçar vínculo
        df["deputado_federal"] = df["deputado_federal"].fillna(default_fed)
        df["deputado_estadual"] = df["deputado_estadual"].fillna(default_est)

        # filtros opcionais por deputado
        st.sidebar.subheader("Filtros")
        filtrar_por_dep_fed = st.sidebar.selectbox("Filtrar por Deputado Federal (opcional)", options=["Todos"] + df["deputado_federal"].unique().tolist())
        filtrar_por_dep_est = st.sidebar.selectbox("Filtrar por Deputado Estadual (opcional)", options=["Todos"] + df["deputado_estadual"].unique().tolist())

        df_filtered = df.copy()
        if filtrar_por_dep_fed != "Todos":
            df_filtered = df_filtered[df_filtered["deputado_federal"] == filtrar_por_dep_fed]
        if filtrar_por_dep_est != "Todos":
            df_filtered = df_filtered[df_filtered["deputado_estadual"] == filtrar_por_dep_est]

        # escolha do filtro de métrica
        filtro = st.radio("Visualizar por:", ["Votos Totais", "Votos Convertidos (pela %)"], horizontal=True)

        if filtro == "Votos Totais":
            total_votos = df_filtered["votos"].sum()
            st.metric("Total de Votos (brutos)", int(total_votos))

            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(df_filtered, x="nome", y="votos", color="deputado_federal",
                             title="Votos por Membro (brutos)", text="votos")
                fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                grouped = df_filtered.groupby("deputado_estadual")["votos"].sum().reset_index()
                fig2 = px.pie(grouped, names="deputado_estadual", values="votos",
                              title="Distribuição de votos por Deputado Estadual (brutos)")
                st.plotly_chart(fig2, use_container_width=True)
        else:
            total_convertidos = df_filtered["votos_convertidos"].sum()
            st.metric("Total de Votos Convertidos (pela %)", f"{total_convertidos:.2f}")

            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(df_filtered, x="nome", y="votos_convertidos", color="deputado_federal",
                             title="Votos Convertidos por Membro", text="votos_convertidos")
                fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                grouped = df_filtered.groupby("deputado_estadual")["votos_convertidos"].sum().reset_index()
                fig2 = px.pie(grouped, names="deputado_estadual", values="votos_convertidos",
                              title="Distribuição de votos convertidos por Deputado Estadual")
                st.plotly_chart(fig2, use_container_width=True)

        st.markdown("### Tabela — Membros (com votos convertidos)")
        st.dataframe(df_filtered[["id", "nome", "votos", "percentual", "votos_convertidos", "cargo", "deputado_federal", "deputado_estadual"]])
