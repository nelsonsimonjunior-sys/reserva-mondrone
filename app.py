import datetime
import os
import uuid
import base64
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Localiza o arquivo de imagem no mesmo diretório do app.py
DIR_APP = os.path.dirname(os.path.abspath(__file__))
NOME_LOGO = "LogoMondrone.jpg"
CAMINHO_LOGO = os.path.join(DIR_APP, NOME_LOGO)

# Configuração da página
st.set_page_config(
    page_title="Reserva de Equipamentos - Colégio Mondrone",
    page_icon=CAMINHO_LOGO if os.path.exists(CAMINHO_LOGO) else NOME_LOGO
)

# Topo com a Logo e Título
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
    st.markdown("<h2 style='color: #4A4A4A; margin-top: -15px; font-weight: 600;'>Colégio Mondrone</h2>", unsafe_allow_html=True)

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    return conn.read(ttl=0)

try:
    df_reservas = carregar_dados()
    if "Email" not in df_reservas.columns:
        df_reservas["Email"] = ""
except Exception:
    df_reservas = pd.DataFrame(columns=["ID", "Data", "Turno", "Aula", "Equipamento", "Professor", "Email"])

LISTA_EQUIPAMENTOS = ["Tablets", "Netbooks", "Notebooks (Apenas 3º Ano)", "Projetor / Caixa de Som"]
LISTA_TURNOS = ["Manhã", "Tarde", "Noite"]

# Função para converter imagem em base64
def carregar_b64(caminho):
    if os.path.exists(caminho):
        with open(caminho, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

caminho_icone = os.path.join(DIR_APP, "icone.png")
if not os.path.exists(caminho_icone) and os.path.exists("icone.png"):
    caminho_icone = "icone.png"

b64_icone = carregar_b64(caminho_icone)

st.markdown("---")

# Cabeçalho da Identificação
if b64_icone:
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 1rem;">
            <img src="data:image/png;base64,{b64_icone}" width="26px" height="26px" style="object-fit: contain;">
            <span style="font-size: 1.5rem; font-weight: 600; color: #31333F;">Identificação do Professor</span>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.subheader("Identificação do Professor")

# Controle do Login na Sessão
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = False

if not st.session_state["usuario_logado"]:
    with st.form("form_identificacao"):
        col_nome, col_email = st.columns(2)
        with col_nome:
            nome_input = st.text_input("Nome:").strip()
        with col_email:
            email_input = st.text_input("E-mail Institucional (@escola.pr.gov.br):").strip().lower()
        
        btn_acessar = st.form_submit_button("🔑 Acessar Sistema", type="primary")

    if btn_acessar:
        if not nome_input or not email_input:
            st.warning("⚠️ Preencha seu **Nome** e **E-mail Institucional** para continuar.")
        elif not email_input.endswith("@escola.pr.gov.br"):
            st.error("❌ **E-mail inválido:** Digite seu e-mail institucional terminado em `@escola.pr.gov.br`.")
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
        if b64_icone:
            st.markdown(
                f"""
                <div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 8px; padding: 10px 15px; display: flex; align-items: center; gap: 8px; color: #155724;">
                    <img src="data:image/png;base64,{b64_icone}" width="20px" height="20px" style="object-fit: contain;">
                    <span><b>Professor(a):</b> {nome_professor} &nbsp;|&nbsp; ✉️ <b>E-mail:</b> {email_professor}</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.success(f"**Professor(a):** {nome_professor} | ✉️ **E-mail:** {email_professor}")

    with col_sair:
        if st.button("🔄 Trocar Usuário"):
            st.session_state["usuario_logado"] = False
            st.rerun()

    # =========================================================
    # ÁREA DE RESERVAS (LIBERADA APÓS LOGIN)
    # =========================================================
    aba_criar, aba_gerenciar = st.tabs(["➕ Nova Reserva", "✏️ Minhas Reservas (Alterar / Excluir)"])

    # Regra de 24h de antecedência: a data mínima para reserva é AMANHÃ
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
        
        # Regra da 6ª Aula exclusiva para o turno da Manhã
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
                conflito = False
                if not df_reservas.empty:
                    datas_planilha = pd.to_datetime(df_reservas["Data"], dayfirst=True, errors="coerce").dt.date

                    linhas_conflito = df_reservas[
                        (df_reservas["Equipamento"].astype(str).str.strip() == equipamento.strip()) &
                        (datas_planilha == data_reserva) &
                        (df_reservas["Turno"].astype(str).str.strip() == turno.strip()) &
                        (df_reservas["Aula"].astype(str).str.strip() == aula.strip())
                    ]
                    if len(linhas_conflito) > 0:
                        conflito = True

                if conflito:
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
                        "Email": email_professor
                    }])

                    df_atualizado = pd.concat([df_reservas, nova_reserva], ignore_index=True)
                    conn.update(worksheet="Página1", data=df_atualizado)
                    
                    st.session_state["sucesso_reserva"] = "✅ **Reserva realizada com sucesso!**"
                    st.rerun()

    # ---------------------------------------------------------
    # ABA 2: GERENCIAR MINHAS RESERVAS
    # ---------------------------------------------------------
    with aba_gerenciar:
        st.subheader(f"Reservas de {nome_professor}")

        if "sucesso_gerenciar" in st.session_state:
            st.success(st.session_state.pop("sucesso_gerenciar"))

        minhas_reservas = df_reservas[df_reservas["Email"].astype(str).str.lower() == email_professor]

        if minhas_reservas.empty:
            st.info("Nenhuma reserva encontrada para este e-mail.")
        else:
            st.dataframe(minhas_reservas[["Data", "Turno", "Aula", "Equipamento", "Professor"]], use_container_width=True)

            opcoes_ids = minhas_reservas["ID"].tolist()
            reserva_id_selecionada = st.selectbox(
                "Selecione a reserva que deseja alterar ou excluir:", 
                opcoes_ids,
                format_func=lambda x: f"ID: {x} - {minhas_reservas[minhas_reservas['ID']==x]['Data'].values[0]} ({minhas_reservas[minhas_reservas['ID']==x]['Equipamento'].values[0]})"
            )

            reserva_atual = minhas_reservas[minhas_reservas["ID"] == reserva_id_selecionada].iloc[0]

            col_alt, col_exc = st.columns(2)

            # Excluir Reserva
            with col_exc:
                st.markdown("### 🗑️ Excluir Reserva")
                if st.button("Excluir esta Reserva"):
                    df_atualizado = df_reservas[df_reservas["ID"] != reserva_id_selecionada]
                    conn.update(worksheet="Página1", data=df_atualizado)
                    st.session_state["sucesso_gerenciar"] = "✅ Reserva excluída com sucesso!"
                    st.rerun()

            # Alterar Reserva
            with col_alt:
                st.markdown("### ✏️ Editar Dados")
                
                data_obj_atual = pd.to_datetime(reserva_atual["Data"], dayfirst=True, errors="coerce").date()
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
                    df_outras = df_reservas[df_reservas["ID"] != reserva_id_selecionada]
                    datas_outras = pd.to_datetime(df_outras["Data"], dayfirst=True, errors="coerce").dt.date
                    
                    conflito_edicao = df_outras[
                        (df_outras["Equipamento"].astype(str).str.strip() == novo_equipamento.strip()) &
                        (datas_outras == nova_data) &
                        (df_outras["Turno"].astype(str).str.strip() == novo_turno.strip()) &
                        (df_outras["Aula"].astype(str).str.strip() == nova_aula.strip())
                    ]

                    if len(conflito_edicao) > 0:
                        st.error("❌ Conflito! Equipamento indisponível nesta data e horário.")
                    else:
                        df_reservas.loc[df_reservas["ID"] == reserva_id_selecionada, ["Data", "Equipamento", "Turno", "Aula", "Professor", "Email"]] = [
                            nova_data.strftime("%d/%m/%Y"), novo_equipamento, novo_turno, nova_aula, nome_professor, email_professor
                        ]
                        conn.update(worksheet="Página1", data=df_reservas)
                        st.session_state["sucesso_gerenciar"] = "✅ Reserva atualizada com sucesso!"
                        st.rerun()

# --- QR CODE PARA ACESSO NO CELULAR ---
st.sidebar.markdown("---")
st.sidebar.subheader("📱 Acesse no Celular")

# Substitua com o link REAL do seu app publicado
url_seu_app = "https://seu-app.streamlit.app" 

# Gera o QR Code automaticamente via API gratuita
qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={url_seu_app}"

st.sidebar.image(qr_url, caption="Aponte a câmera do celular para abrir")
