import streamlit as st
import pandas as pd
import gspread
import uuid
from datetime import date

# ---------------------------------------------------------
# Configuração da página Streamlit
# ---------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Equipamentos - Colégio Mondrone",
    page_icon="💻",
    layout="wide"
)

# ---------------------------------------------------------
# Conexão com o Google Sheets via gspread / Secrets
# ---------------------------------------------------------
@st.cache_resource(ttl=60)
def get_gspread_client():
    return gspread.service_account_from_dict(st.secrets["gcp_service_account"])

try:
    gc = get_gspread_client()
    # Nome do ficheiro da folha de cálculo no Google Drive
    sheet_name = st.secrets.get("SPREADSHEET_NAME", "Reservas de Equipamentos - Mondrone")
    sh = gc.open(sheet_name)
    worksheet = sh.worksheet("Mondrone")
except Exception as e:
    st.error(f"Erro ao conectar à folha de cálculo do Google Sheets: {e}")
    st.stop()

# ---------------------------------------------------------
# Funções de Dados (Carregar, Guardar, Soft Delete)
# ---------------------------------------------------------
def carregar_dados():
    """Carrega e trata os dados da aba Mondrone."""
    dados = worksheet.get_all_records()
    df = pd.DataFrame(dados)
    
    # Garantir que todas as colunas necessárias existem
    colunas_esperadas = ["ID", "Data", "Turno", "Aula", "Equipamento", "Professor", "Email", "Status"]
    for col in colunas_esperadas:
        if col not in df.columns:
            df[col] = ""
    
    # Se a coluna Status estiver em branco, define como ATIVO por padrão
    df["Status"] = df["Status"].replace("", "ATIVO")
    return df

def salvar_reserva(data_str, turno, aula, equipamento, professor, email):
    """Adiciona uma nova reserva com Status = ATIVO."""
    novo_id = uuid.uuid4().hex[:8]
    nova_linha = [
        novo_id,
        data_str,
        turno,
        aula,
        equipamento,
        professor,
        email,
        "ATIVO"  # Coluna H (8)
    ]
    worksheet.append_row(nova_linha)

def cancelar_reserva_soft_delete(id_reserva):
    """Muda o estado na Coluna H (8) para CANCELADO sem apagar a linha."""
    celula = worksheet.find(id_reserva, in_column=1)
    if celula:
        # Coluna 8 = Coluna H (Status)
        worksheet.update_cell(celula.row, 8, "CANCELADO")
        return True
    return False

# ---------------------------------------------------------
# Interface Principal
# ---------------------------------------------------------
st.title("💻 Sistema de Reservas de Equipamentos")
st.subheader("Colégio Mondrone")

# Carrega os dados mais recentes
df_todos = carregar_dados()

# Filtra no Streamlit apenas os registos que NÃO foram cancelados
df_ativos = df_todos[df_todos["Status"] != "CANCELADO"]

# Navegação por Separadores (Tabs)
tab1, tab2, tab3 = st.tabs(["📅 Reservas Ativas", "➕ Nova Reserva", "❌ Cancelar Reserva"])

# ---------------------------------------------------------
# Separador 1: Visualizar Reservas Ativas
# ---------------------------------------------------------
with tab1:
    st.markdown("### 📋 Agendamentos Confirmados")
    if not df_ativos.empty:
        # Exibe apenas as colunas relevantes ao utilizador
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
                salvar_reserva(data_formatada, turno, aula, equipamento, professor, email)
                st.success(f"Reserva efetuada com sucesso para {data_formatada} ({equipamento})!")
                st.rerun()

# ---------------------------------------------------------
# Separador 3: Cancelar Reserva (Soft Delete)
# ---------------------------------------------------------
with tab3:
    st.markdown("### ⚠️ Cancelamento Seguro de Reserva")
    st.write("O cancelamento **não elimina** dados da folha de cálculo; apenas altera o estado da reserva para `CANCELADO`.")
    
    if not df_ativos.empty:
        # Opções formatadas para o menu de seleção
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
                sucesso = cancelar_reserva_soft_delete(id_para_cancelar)
                if sucesso:
                    st.success("Reserva marcada como CANCELADA com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro ao localizar a reserva na folha de cálculo.")
            else:
                st.warning("Marque a caixa de confirmação antes de prosseguir.")
    else:
        st.info("Não existem reservas ativas disponíveis para cancelamento.")
