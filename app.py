import datetime
import os
import uuid
import base64
import time
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------
# CONFIGURAÇÃO E BLINDAGEM DA PLANILHA
NOME_ABA = "Mondrone"
COLUNAS_PADRAO = ["ID", "Data", "Turno", "Aula", "Equipamento", "Professor", "Email", "Status"]
MAX_TENTATIVAS = 3
ESPERA_ENTRE_TENTATIVAS = 1
# ---------------------------------------------------------

DIR_APP = os.path.dirname(os.path.abspath(__file__))
NOME_LOGO = "LogoMondrone.jpg"
CAMINHO_LOGO = os.path.join(DIR_APP, NOME_LOGO)

# Configuração da página
st.set_page_config(
    page_title="Reserva de Equipamentos - Colégio Mondrone",
    page_icon=CAMINHO_LOGO if os.path.exists(CAMINHO_LOGO) else "🏫"
)

# Topo com o Logótipo e Título
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    if os.path.exists(CAMINHO_LOGO):
        st.image(CAMINHO_LOGO, width=110)
    elif os.path.exists(NOME_LOGO):
        st.image(NOME_LOGO, width=110)
    else:
        st.write("🏫")

with col_titulo:
    st.title("Reserva de Equipamentos")
    st.markdown(
        "<h3 style='margin-top: -15px; opacity: 0.85;'>Colégio Mondrone</h3>",
        unsafe_allow_html=True
    )

# Inicialização segura da conexão com Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("⚠️ Ocorreu um problema ao inicializar a ligação com o Google Sheets.")
    st.info("Por favor, recarregue a página em alguns instantes.")
    st.stop()

def normalizar_texto(texto):
    """Remove espaços extras, converte para minúsculas e padroniza símbolos."""
    if pd.isna(texto) or texto is None:
        return ""
    t = str(texto).strip().lower()
    t = t.replace("º", "").replace("°", "").replace("ª", "")
    return t

def carregar_dados_frescos():
    """Lê os dados mais recentes do Google Sheets com mecanismo de retentativas automáticas."""
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            df = conn.read(worksheet=NOME_ABA, ttl=0)
            if df is None or df.empty:
                return pd.DataFrame(columns=COLUNAS_PADRAO)
            
            df = df.dropna(how="all")
            for col in COLUNAS_PADRAO:
                if col not in df.columns:
                    df[col] = ""
            
            df = df[COLUNAS_PADRAO]
            df["Status"] = df["Status"].fillna("ATIVO")
            df["Status"] = df["Status"].replace("", "ATIVO")
            df = df.fillna("")
            df = df[df["ID"].astype(str).str.strip() != ""]
            return df
        
        except Exception:
            if tentativa < MAX_TENTATIVAS:
                time.sleep(ESPERA_ENTRE_TENTATIVAS)
            else:
                st.error("⚠️ Não foi possível carregar os dados da planilha no momento.")
                st.warning("Verifique a sua ligação à internet ou tente novamente em alguns segundos.")
                st.stop()

def salvar_dados(df):
    """Guarda os dados no Google Sheets com retentativas automáticas e tratamento de erros."""
    df_salvar = df.copy()
    for col in COLUNAS_PADRAO:
        if col not in df_salvar.columns:
            df_salvar[col] = ""
    df_salvar = df_salvar[COLUNAS_PADRAO].fillna("")
    df_salvar = df_salvar.astype(str)

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            conn.update(worksheet=NOME_ABA, data=df_salvar)
            return True
        except Exception:
            if tentativa < MAX_TENTATIVAS:
                time.sleep(ESPERA_ENTRE_TENTATIVAS)
            else:
                st.error("❌ Erro ao guardar as informações na planilha.")
                st.warning("A alteração não pôde ser salva. Por favor, clique no botão novamente.")
                return False

def verificar_conflito(df_fresco, data_reserva, equipamento, turno, aula, id_ignorar=None):
    """Verifica de forma infalível se o equipamento já está ocupado no horário selecionado."""
    if df_fresco.empty:
        return False

    df_ativas = df_fresco[df_fresco["Status"].astype(str).str.upper() != "CANCELADO"].copy()
    
    if id_ignorar:
        df_ativas = df_ativas[df_ativas["ID"].astype(str).str.strip() != str(id_ignorar).strip()]
        
    if df_ativas.empty:
        return False

    datas_parsed = pd.to_datetime(df_ativas["Data"], format="mixed", dayfirst=True, errors="coerce").dt.date

    eq_alvo = normalizar_texto(equipamento)
    tur_alvo = normalizar_texto(turno)
    aula_alvo = normalizar_texto(aula)

    for idx, row in df_ativas.iterrows():
        data_row = datas_parsed.loc[idx]
        if data_row == data_reserva:
            if (normalizar_texto(row["Equipamento"]) == eq_alvo and
                normalizar_texto(row["Turno"]) == tur_alvo and
                normalizar_texto(row["Aula"]) == aula_alvo):
                return True
    return False

# Carregamento seguro dos dados iniciais
df_reservas = carregar_dados_frescos()
df_ativas = df_reservas[df_reservas["Status"].astype(str).str.upper() != "CANCELADO"].copy()

# LISTA OFICIAL DE EQUIPAMENTOS E TURNOS
LISTA_EQUIPAMENTOS = [
    "Tablets",
    "Netbooks",
    "Notebooks (Apenas 3º Ano)",
    "ChromeBooks"
]
LISTA_TURNOS = ["Manhã", "Tarde", "Noite"]

# Carregamento do ícone do cabeçalho
def carregar_b64(caminho):
    try:
        if os.path.exists(caminho):
            with open(caminho, "rb") as f:
                return base64.b64encode(f.read()).decode()
    except Exception:
        pass
    return None

caminho_icone = os.path.join(DIR_APP, "icone.png")
if not os.path.exists(caminho_icone) and os.path.exists("icone.png"):
    caminho_icone = "icone.png"

b64_icone = carregar_b64(caminho_icone)

st.markdown("---")

# Título da Identificação com a imagem de cima
if b64_icone:
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 1rem;">
            <img src="data:image/png;base64,{b64_icone}" width="28px" height="28px" style="object-fit: contain;">
            <span style="font-size: 1.5rem; font-weight: 600;">Identificação do Professor</span>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.subheader("👤 Identificação do Professor")

# Controlo da Sessão de Utilizador
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = False

if not st.session_state["usuario_logado"]:
    with st.form("form_identificacao"):
        col_nome, col_email = st.columns(2)
        with col_nome:
            nome_input = st.text_input("Nome:").strip()
        with col_email:
            email_input = st.text_input("E-mail Institucional (@escola.pr.gov.br):").strip().lower()
        
        btn_acessar = st.form_submit_button("🔑 Acessar o Sistema", type="primary")

    if btn_acessar:
        if not nome_input or not email_input:
            st.warning("⚠️ Preencha o seu **Nome** e **E-mail Institucional** para continuar.")
        elif not email_input.endswith("@escola.pr.gov.br"):
            st.error("❌ **E-mail inválido:** Digite o seu e-mail institucional terminado em @escola.pr.gov.br.")
        else:
            st.session_state["nome_professor"] = nome_input
            st.session_state["email_professor"] = email_input
            st.session_state["usuario_logado"] = True
            st.rerun()

else:
    nome_professor = st.session_state["nome_professor"]
    email_professor = st.session_state["email_professor"]

    col_info, col_sair = st.columns([4, 1])
    with col_info:
        st.success(f"**Professor(a):** {nome_professor} | ✉️ **E-mail:** {email_professor}")

    with col_sair:
        if st.button("🔄 Alterar Usuário"):
            st.session_state["usuario_logado"] = False
            st.rerun()

    # =========================================================
    # ÁREA DE RESERVAS
    # =========================================================
    aba_criar, aba_gerenciar, aba_agenda = st.tabs([
        "➕ Nova Reserva", 
        "✏️ Minhas Reservas", 
        "📅 Agenda Geral"
    ])

    data_minima = datetime.date.today() + datetime.timedelta(days=1)

    # ---------------------------------------------------------
    # ABA 1: NOVA RESERVA
    # ---------------------------------------------------------
    with aba_criar:
        st.subheader("Agendar Equipamento")

        if "sucesso_reserva" in st.session_state:
            st.success(st.session_state.pop("sucesso_reserva"))
        
        data_reserva = st.date_input(
            "Data da Reserva (Mínimo 24h de antecedência):", 
            min_value=data_minima, 
            value=data_minima, 
            format="DD/MM/YYYY"
        )
        
        if data_reserva.weekday() in [5, 6]:
            st.warning("⚠️ Atenção: A data selecionada é um fim de semana.")

        col1, col2, col3 = st.columns(3)
        with col1:
            equipamento = st.selectbox("Equipamento:", LISTA_EQUIPAMENTOS)
        with col2:
            turno = st.selectbox("Turno:", LISTA_TURNOS)
        
        if turno == "Manhã":
            aulas_disponiveis = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula"]
        else:
            aulas_disponiveis = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula"]

        with col3:
            aula = st.selectbox("Aula:", aulas_disponiveis)

        if st.button("Confirmar Reserva", type="primary"):
            if data_reserva.weekday() in [5, 6]:
                st.error("❌ Não é possível realizar reservas para sábados ou domingos.")
            else:
                df_fresco = carregar_dados_frescos()
                
                tem_conflito = verificar_conflito(
                    df_fresco=df_fresco,
                    data_reserva=data_reserva,
                    equipamento=equipamento,
                    turno=turno,
                    aula=aula
                )

                if tem_conflito:
                    st.error(f"❌ **CONFLITO DE RESERVA:** O equipamento **{equipamento}** já está reservado no dia **{data_reserva.strftime('%d/%m/%Y')}** ({turno} - {aula}).")
                else:
                    data_formatada = data_reserva.strftime("%d/%m/%Y")
                    
                    nova_reserva = pd.DataFrame([{
                        "ID": str(uuid.uuid4())[:8],
                        "Data": data_formatada,
                        "Turno": turno,
                        "Aula": aula,
                        "Equipamento": equipamento,
                        "Professor": nome_professor,
                        "Email": email_professor,
                        "Status": "ATIVO"
                    }])

                    df_atualizado = pd.concat([df_fresco, nova_reserva], ignore_index=True)
                    if salvar_dados(df_atualizado):
                        st.session_state["sucesso_reserva"] = "✅ **Reserva realizada com sucesso!**"
                        st.rerun()

    # ---------------------------------------------------------
    # ABA 2: GERENCIAR MINHAS RESERVAS
    # ---------------------------------------------------------
    with aba_gerenciar:
        st.subheader(f"Reservas de {nome_professor}")

        if "sucesso_gerenciar" in st.session_state:
            st.success(st.session_state.pop("sucesso_gerenciar"))

        minhas_reservas = df_ativas[df_ativas["Email"].astype(str).str.lower() == email_professor.lower()]

        if minhas_reservas.empty:
            st.info("Nenhuma reserva encontrada para este e-mail.")
        else:
            st.dataframe(
                minhas_reservas[["Data", "Turno", "Aula", "Equipamento", "Professor"]],
                use_container_width=True
            )

            opcoes_ids = minhas_reservas["ID"].tolist()
            reserva_id_selecionada = st.selectbox(
                "Selecione a reserva que deseja alterar ou excluir:", 
                opcoes_ids,
                format_func=lambda x: f"ID: {x} - {minhas_reservas[minhas_reservas['ID']==x]['Data'].values[0]} ({minhas_reservas[minhas_reservas['ID']==x]['Equipamento'].values[0]})"
            )

            reserva_atual = minhas_reservas[minhas_reservas["ID"] == reserva_id_selecionada].iloc[0]

            col_alt, col_exc = st.columns(2)

            with col_exc:
                st.markdown("### 🗑️ Excluir Reserva")
                if st.button("Excluir esta Reserva"):
                    df_fresco = carregar_dados_frescos()
                    df_fresco.loc[df_fresco["ID"].astype(str) == str(reserva_id_selecionada), "Status"] = "CANCELADO"
                    if salvar_dados(df_fresco):
                        st.session_state["sucesso_gerenciar"] = "✅ Reserva cancelada com sucesso!"
                        st.rerun()

            with col_alt:
                st.markdown("### ✏️ Editar Dados")
                
                data_obj_atual = pd.to_datetime(reserva_atual["Data"], format="mixed", dayfirst=True, errors="coerce").date()
                if pd.isna(data_obj_atual) or data_obj_atual < data_minima:
                    data_obj_atual = data_minima

                nova_data = st.date_input(
                    "Nova Data:", 
                    value=data_obj_atual,
                    min_value=data_minima,
                    format="DD/MM/YYYY",
                    key=f"edit_data_{reserva_id_selecionada}"
                )
                
                idx_eq = LISTA_EQUIPAMENTOS.index(reserva_atual["Equipamento"]) if reserva_atual["Equipamento"] in LISTA_EQUIPAMENTOS else 0
                idx_tur = LISTA_TURNOS.index(reserva_atual["Turno"]) if reserva_atual["Turno"] in LISTA_TURNOS else 0

                novo_equipamento = st.selectbox("Novo Equipamento:", LISTA_EQUIPAMENTOS, index=idx_eq, key=f"edit_eq_{reserva_id_selecionada}")
                novo_turno = st.selectbox("Novo Turno:", LISTA_TURNOS, index=idx_tur, key=f"edit_tur_{reserva_id_selecionada}")

                if novo_turno == "Manhã":
                    aulas_edit_disponiveis = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula"]
                else:
                    aulas_edit_disponiveis = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula"]

                idx_aul = aulas_edit_disponiveis.index(reserva_atual["Aula"]) if reserva_atual["Aula"] in aulas_edit_disponiveis else 0

                nova_aula = st.selectbox("Nova Aula:", aulas_edit_disponiveis, index=idx_aul, key=f"edit_aul_{reserva_id_selecionada}")

                if st.button("Salvar Alterações"):
                    df_fresco = carregar_dados_frescos()
                    
                    conflito_edicao = verificar_conflito(
                        df_fresco=df_fresco,
                        data_reserva=nova_data,
                        equipamento=novo_equipamento,
                        turno=novo_turno,
                        aula=nova_aula,
                        id_ignorar=reserva_id_selecionada
                    )

                    if conflito_edicao:
                        st.error("❌ Conflito! Equipamento indisponível nesta data e horário.")
                    else:
                        df_fresco.loc[df_fresco["ID"].astype(str) == str(reserva_id_selecionada), ["Data", "Equipamento", "Turno", "Aula", "Professor", "Email"]] = [
                            nova_data.strftime("%d/%m/%Y"), novo_equipamento, novo_turno, nova_aula, nome_professor, email_professor
                        ]
                        if salvar_dados(df_fresco):
                            st.session_state["sucesso_gerenciar"] = "✅ Reserva atualizada com sucesso!"
                            st.rerun()

    # ---------------------------------------------------------
    # ABA 3: AGENDA GERAL (CONSULTA POR DIA)
    # ---------------------------------------------------------
    with aba_agenda:
        st.subheader("📋 Agenda Geral de Equipamentos")
        st.write("Consulte a disponibilidade de qualquer equipamento escolhendo a data abaixo:")

        data_consulta = st.date_input(
            "Selecione o dia para consultar:", 
            value=datetime.date.today(), 
            format="DD/MM/YYYY",
            key="data_consulta_tab"
        )

        if not df_ativas.empty:
            datas_agenda = pd.to_datetime(df_ativas["Data"], format="mixed", dayfirst=True, errors="coerce").dt.date
            reservas_dia = df_ativas[datas_agenda == data_consulta]

            if reservas_dia.empty:
                st.success(f"🎉 **Todos os equipamentos estão totalmente livres no dia {data_consulta.strftime('%d/%m/%Y')}!**")
            else:
                st.info(f"📌 **Equipamentos agendados para {data_consulta.strftime('%d/%m/%Y')}:**")
                st.dataframe(
                    reservas_dia[["Turno", "Aula", "Equipamento", "Professor"]], 
                    use_container_width=True, 
                    hide_index=True
                )
        else:
            st.success("🎉 **Nenhum agendamento cadastrado no sistema.**")
