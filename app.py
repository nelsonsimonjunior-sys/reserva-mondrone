import streamlit as st
import pandas as pd
import uuid
from datetime import date
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
# Conexão oficial via GSheetsConnection (st.connection)
# ---------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

# ---------------------------------------------------------
# Funções para manipulação de dados na Folha de Cálculo
# ---------------------------------------------------------
def carregar_dados():
    """Lê os dados da aba Mondrone sem usar cache prolongado (ttl=0)."""
    df = conn.read(worksheet="Mondrone", ttl=0)
    df = df.dropna(how="all")  # Remove linhas totalmente vazias
    
    # Garantir que todas as colunas existem
    colunas_esperadas = ["ID", "Data", "Turno", "Aula", "Equipamento", "Professor", "Email", "Status"]
    for col in colunas_esperadas:
        if col not in df.columns:
            df[col] = ""
            
    # Se o Status estiver em branco ou nulo, define como ATIVO
    df["Status"] = df["Status"].fillna("ATIVO").replace("", "ATIVO")
    return df

def salvar_reserva(df_atual, data_str, turno, aula, equipamento, professor, email):
    """Adiciona uma nova linha com Status = ATIVO e atualiza a folha."""
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
    
    df_atualizado = pd.concat([df_atual, nova_linha], ignore_index=True)
    conn.update(worksheet="Mondrone", data=df_atualizado)

def cancelar_reserva_soft_delete(df_atual, id_reserva):
    """Muda o Status da reserva para CANCELADO na folha sem apagar a linha."""
    mask = df_atual["ID"].astype(str) == str(id_reserva)
    if mask.any():
        df_atual.loc[mask, "Status"] = "CANCELADO"
        conn.update(worksheet="Mondrone", data=df_atual)
        return True
    return False

# ---------------------------------------------------------
# Interface do Utilizador (Streamlit)
# ---------------------------------------------------------
st.title("💻 Sistema de Reservas de Equipamentos")
st.subheader("Colégio Mondrone")

# Carrega os dados da folha
df_todos = carregar_dados()

# Filtra apenas os registos ATIVOS para exibição
df_ativos = df_todos[df_todos["Status"] != "CANCELADO"]

# Separadores (Tabs)
tab1, tab2, tab3 = st.tabs(["📅 Reservas Ativas", "➕ Nova Reserva", "❌ Cancelar Reserva"])

# ---------------------------------------------------------
# Separador 1: Visualizar Reservas Ativas
# ---------------------------------------------------------
with tab1:
    st.markdown("### 📋 Agendamentos Confirmados")
    if not df_ativos.empty:
        st.dataframe(
            df_ativos[["ID", "Data", "Turno", "Aula", "Equipamento", "Professor", "Email"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhuma reserva ativa encontrada de momento.")

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
