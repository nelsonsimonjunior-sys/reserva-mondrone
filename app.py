import streamlit as st
import pandas as pd
import uuid
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------
# Configuração da página Streamlit
# ---------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Equipamentos - Colégio Mondrone",
    page_icon="💻",
    layout="wide"
)

# ---------------------------------------------------------
# Conexão com o Google Sheets via GSheetsConnection
# ---------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

# ---------------------------------------------------------
# Funções de Dados (Leitura, Gravação e Soft Delete)
# ---------------------------------------------------------
def carregar_dados():
    """Lê os dados da 1ª aba da folha de cálculo sem usar cache (ttl=0)."""
    df = conn.read(worksheet=0, ttl=0)
    df = df.dropna(how="all")
    
    colunas_esperadas = ["ID", "Data", "Turno", "Aula", "Equipamento", "Professor", "Email", "Status"]
    for col in colunas_esperadas:
        if col not in df.columns:
            df[col] = ""
            
    df["Status"] = df["Status"].fillna("ATIVO").replace("", "ATIVO")
    
    # Converter coluna de Data para datetime para permitir ordenação e filtros
    df["Data_DT"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
    return df

def salvar_reserva(df_atual, data_str, turno, aula, equipamento, professor, email):
    """Adiciona uma nova linha com Status = ATIVO."""
    novo_id = uuid.uuid4().hex[:8]
    nova_linha = pd.DataFrame([{
        "ID": novo_id,
        "Data": data_str,
        "Turno": turno,
        "Aula": aula,
        "Equipamento": equipamento,
        "Professor": professor,
        "Email": email,
        "Status": "ATIVO"
    }])
    
    # Remove a coluna temporária de datetime antes de salvar na planilha
    if "Data_DT" in df_atual.columns:
        df_atual = df_atual.drop(columns=["Data_DT"])
        
    df_atualizado = pd.concat([df_atual, nova_linha], ignore_index=True)
    conn.update(worksheet=0, data=df_atualizado)

def cancelar_reserva_soft_delete(df_atual, id_reserva):
    """Muda o Status da reserva para CANCELADO na folha de cálculo."""
    if "Data_DT" in df_atual.columns:
        df_atual = df_atual.drop(columns=["Data_DT"])
        
    mask = df_atual["ID"].astype(str) == str(id_reserva)
    if mask.any():
        df_atual.loc[mask, "Status"] = "CANCELADO"
        conn.update(worksheet=0, data=df_atual)
        return True
    return False

# ---------------------------------------------------------
# Carregamento Inicial
# ---------------------------------------------------------
df_todos = carregar_dados()

# Filtra apenas registos NÃO cancelados
df_ativos = df_todos[df_todos["Status"] != "CANCELADO"].copy()

# ---------------------------------------------------------
# Barra Lateral (Sidebar) - Filtros de Pesquisa
# ---------------------------------------------------------
st.sidebar.header("🔍 Filtros de Consulta")

# Filtro de Intervalo de Datas
hoje = date.today()
primeiro_dia_mes = hoje.replace(day=1)
ultimo_dia_mes = (hoje.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

data_inicio = st.sidebar.date_input("Data Inicial", value=primeiro_dia_mes)
data_fim = st.sidebar.date_input("Data Final", value=ultimo_dia_mes)

# Filtro por Equipamento
lista_equipamentos = [
    "Todos", 
    "Tablets", 
    "Netbooks", 
    "Chromebooks", 
    "Notebooks (Apenas 3º Ano)", 
    "Projetor / Caixa de Som"
]
equipamento_filtro = st.sidebar.selectbox("Filtrar por Equipamento", lista_equipamentos)

# Filtro por Turno
turno_filtro = st.sidebar.selectbox("Filtrar por Turno", ["Todos", "Manhã", "Tarde", "Noite"])

# Pesquisa textual por Professor / E-mail / ID
busca_texto = st.sidebar.text_input("Pesquisar Professor / E-mail / ID")

# ---------------------------------------------------------
# Aplicação dos Filtros nos Dados
# ---------------------------------------------------------
df_exibicao = df_ativos.copy()

if not df_exibicao.empty:
    # Filtro de Datas
    mask_data = (df_exibicao["Data_DT"].dt.date >= data_inicio) & (df_exibicao["Data_DT"].dt.date <= data_fim)
    df_exibicao = df_exibicao[mask_data]
    
    # Filtro de Equipamento
    if equipamento_filtro != "Todos":
        df_exibicao = df_exibicao[df_exibicao["Equipamento"] == equipamento_filtro]
        
    # Filtro de Turno
    if turno_filtro != "Todos":
        df_exibicao = df_exibicao[df_exibicao["Turno"] == turno_filtro]
        
    # Pesquisa de Texto
    if busca_texto:
        termo = busca_texto.lower()
        mask_texto = (
            df_exibicao["Professor"].str.lower().str.contains(termo, na=False) |
            df_exibicao["Email"].str.lower().str.contains(termo, na=False) |
            df_exibicao["ID"].str.lower().str.contains(termo, na=False)
        )
        df_exibicao = df_exibicao[mask_texto]
        
    # Ordenação por Data, Turno e Aula
    df_exibicao = df_exibicao.sort_values(by=["Data_DT", "Turno", "Aula"], ascending=[True, True, True])

# ---------------------------------------------------------
# Interface Principal
# ---------------------------------------------------------
st.title("💻 Sistema de Reservas de Equipamentos")
st.subheader("Colégio Mondrone")

# Separadores
tab1, tab2, tab3 = st.tabs(["📅 Reservas Ativas", "➕ Nova Reserva", "❌ Cancelar Reserva"])

# ---------------------------------------------------------
# Separador 1: Visualizar Reservas Ativas
# ---------------------------------------------------------
with tab1:
    st.markdown("### 📋 Agendamentos Confirmados")
    
    # Cartões de Métricas
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Reservas Encontradas", len(df_exibicao))
    col_m2.metric("Período Selecionado", f"{data_inicio.strftime('%d/%m')} até {data_fim.strftime('%d/%m')}")
    col_m3.metric("Filtro Equipamento", equipamento_filtro)
    
    st.divider()
    
    if not df_exibicao.empty:
        # Exibe a tabela formatada
        st.dataframe(
            df_exibicao[["ID", "Data", "Turno", "Aula", "Equipamento", "Professor", "Email"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhuma reserva encontrada para os filtros selecionados no painel lateral.")

# ---------------------------------------------------------
# Separador 2: Criar Nova Reserva
# ---------------------------------------------------------
with tab2:
    st.markdown("### 📝 Registo de Novo Agendamento")
    
    with st.form("form_nova_reserva", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            data_reserva = st.date_input("Data do Agendamento", value=date.today())
            turno = st.selectbox("Turno", ["Manhã", "Tarde", "Noite"])
            aula = st.selectbox("Aula", ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula"])
        
        with col2:
            equipamento = st.selectbox(
                "Equipamento", 
                [
                    "Tablets", 
                    "Netbooks", 
                    "Chromebooks", 
                    "Notebooks (Apenas 3º Ano)", 
                    "Projetor / Caixa de Som"
                ]
            )
            professor = st.text_input("Nome do Professor")
            email = st.text_input("E-mail do Professor")
        
        submit_btn = st.form_submit_button("Confirmar Reserva")
        
        if submit_btn:
            if not professor or not email:
                st.error("Por favor, preencha o Nome e o E-mail do Professor.")
            else:
                data_formatada = data_reserva.strftime("%d/%m/%Y")
                salvar_reserva(df_todos, data_formatada, turno, aula, equipamento, professor, email)
                st.success(f"Reserva efetuada com sucesso para {data_formatada} ({equipamento})!")
                st.rerun()

# ---------------------------------------------------------
# Separador 3: Cancelar Reserva (Soft Delete)
# ---------------------------------------------------------
with tab3:
    st.markdown("### ⚠️ Cancelamento Seguro de Reserva")
    st.write("O cancelamento **não elimina** dados da folha de cálculo; apenas altera o estado da reserva para `CANCELADO`.")
    
    if not df_ativos.empty:
        opcoes_cancelamento = {
            f"{row['ID']} | {row['Data']} | {row['Turno']} - {row['Aula']} | {row['Equipamento']} ({row['Professor']})": row['ID']
            for _, row in df_ativos.iterrows()
        }
        
        reserva_selecionada_label = st.selectbox(
            "Selecione a reserva que deseja cancelar:",
            options=list(opcoes_cancelamento.keys())
        )
        
        id_para_cancelar = opcoes_cancelamento[reserva_selecionada_label]
        confirmar = st.checkbox("Confirmo que pretendo cancelar esta reserva.")
        
        if st.button("Confirmar Cancelamento"):
            if confirmar:
                sucesso = cancelar_reserva_soft_delete(df_todos, id_para_cancelar)
                if sucesso:
                    st.success("Reserva marcada como CANCELADA com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro ao localizar a reserva na folha de cálculo.")
            else:
                st.warning("Marque a caixa de confirmação antes de prosseguir.")
    else:
        st.info("Não existem reservas ativas disponíveis para cancelamento.")
