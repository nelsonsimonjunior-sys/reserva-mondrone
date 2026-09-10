import datetime
import uuid
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# 1. Configuração da página e layout
st.set_page_config(
    page_title="Reserva de Equipamentos - Colégio Mondrone",
    page_icon="LogoMondrone.jpg"
)

# Topo com a Logo e Título
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    st.image("LogoMondrone.jpg", width=100)
with col_titulo:
    st.title("Reserva de Equipamentos")
    st.write("**Colégio Mondrone**")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    return conn.read(ttl=0)

try:
    df_reservas = carregar_dados()
    # Garante que a coluna 'Email' exista caso a planilha antiga não a tenha
    if "Email" not in df_reservas.columns:
        df_reservas["Email"] = ""
except Exception:
    df_reservas = pd.DataFrame(columns=["ID", "Data", "Turno", "Aula", "Equipamento", "Professor", "Email"])

LISTA_EQUIPAMENTOS = ["Tablets", "Netbooks", "Notebooks (Apenas 3º Ano)", "Projetor / Caixa de Som"]
LISTA_TURNOS = ["Manhã", "Tarde", "Noite"]
LISTA_AULAS = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula"]

# =========================================================
# IDENTIFICAÇÃO DO PROFESSOR (Nome + Validação de E-mail)
# =========================================================
st.markdown("---")
st.subheader("👤 Identificação do Professor")

col_nome, col_email = st.columns(2)
with col_nome:
    nome_professor = st.text_input("Nome Completo:").strip()
with col_email:
    email_professor = st.text_input("E-mail Institucional (@escola.pr.gov.br):").strip().lower()

# Função simples para validar o formato do e-mail
def email_valido(email):
    return "@" in email and "." in email

# Verifica se ambos os campos foram preenchidos e se o e-mail é válido
if nome_professor and email_professor:
    if not email_valido(email_professor):
        st.warning("⚠️ **E-mail inválido:** Digite um e-mail correto (exemplo: `nome@escola.pr.gov.br`).")
    else:
        # Se os dados estiverem válidos, libera o acesso às abas
        aba_criar, aba_gerenciar = st.tabs(["➕ Nova Reserva", "✏️ Minhas Reservas (Alterar / Excluir)"])

        # =========================================================
        # ABA 1: NOVA RESERVA
        # =========================================================
        with aba_criar:
            st.subheader("Agendar Equipamento")
            
            hoje = datetime.date.today()
            data_reserva = st.date_input("Data da Reserva:", min_value=hoje, value=hoje)
            
            if data_reserva.weekday() in [5, 6]:
                st.warning("⚠️ Atenção: A data selecionada é um fim de semana.")

            col1, col2, col3 = st.columns(3)
            with col1:
                equipamento = st.selectbox("Equipamento:", LISTA_EQUIPAMENTOS)
            with col2:
                turno = st.selectbox("Turno:", LISTA_TURNOS)
            with col3:
                aula = st.selectbox("Aula:", LISTA_AULAS)

            if st.button("Confirmar Reserva", type="primary"):
                if data_reserva.weekday() in [5, 6]:
                    st.error("❌ Não é possível realizar reservas para sábados ou domingos.")
                else:
                    # Checa conflitos de reserva
                    conflito = False
                    if not df_reservas.empty:
                        linhas_conflito = df_reservas[
                            (df_reservas["Equipamento"] == equipamento) &
                            (df_reservas["Data"] == str(data_reserva)) &
                            (df_reservas["Turno"] == turno) &
                            (df_reservas["Aula"] == aula)
                        ]
                        if len(linhas_conflito) > 0:
                            conflito = True

                    if conflito:
                        st.error(f"❌ **CONFLITO:** O equipamento **{equipamento}** já foi reservado para este horário.")
                    else:
                        # Registra ID, Data, Turno, Aula, Equipamento, Nome e E-mail
                        nova_reserva = pd.DataFrame([{
                            "ID": str(uuid.uuid4())[:8],
                            "Data": str(data_reserva),
                            "Turno": turno,
                            "Aula": aula,
                            "Equipamento": equipamento,
                            "Professor": nome_professor,
                            "Email": email_professor
                        }])

                        df_atualizado = pd.concat([df_reservas, nova_reserva], ignore_index=True)
                        conn.update(worksheet="Página1", data=df_atualizado)
                        st.success("✅ **Reserva realizada com sucesso!**")
                        st.rerun()

        # =========================================================
        # ABA 2: GERENCIAR MINHAS RESERVAS
        # =========================================================
        with aba_gerenciar:
            st.subheader(f"Reservas de {nome_professor}")

            # Busca reservas associadas ao e-mail digitado
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
                        st.success("Reserva excluída com sucesso!")
                        st.rerun()

                # Alterar Reserva
                with col_alt:
                    st.markdown("### ✏️ Editar Dados")
                    nova_data = st.date_input(
    "Nova Data:", 
    value=pd.to_datetime(reserva_atual["Data"]).date(),
    min_value=hoje,
    key="edit_data"
)
                    novo_equipamento = st.selectbox("Novo Equipamento:", LISTA_EQUIPAMENTOS, index=LISTA_EQUIPAMENTOS.index(reserva_atual["Equipamento"]), key="edit_eq")
                    novo_turno = st.selectbox("Novo Turno:", LISTA_TURNOS, index=LISTA_TURNOS.index(reserva_atual["Turno"]), key="edit_tur")
                    nova_aula = st.selectbox("Nova Aula:", LISTA_AULAS, index=LISTA_AULAS.index(reserva_atual["Aula"]), key="edit_aul")

                    if st.button("Salvar Alterações"):
                        df_outras = df_reservas[df_reservas["ID"] != reserva_id_selecionada]
                        
                        conflito_edicao = df_outras[
                            (df_outras["Equipamento"] == novo_equipamento) &
                            (df_outras["Data"] == str(nova_data)) &
                            (df_outras["Turno"] == novo_turno) &
                            (df_outras["Aula"] == nova_aula)
                        ]

                        if len(conflito_edicao) > 0:
                            st.error("❌ Conflito! Equipamento indisponível nesta data/horário.")
                        else:
                            df_reservas.loc[df_reservas["ID"] == reserva_id_selecionada, ["Data", "Equipamento", "Turno", "Aula", "Professor", "Email"]] = [
                                str(nova_data), novo_equipamento, novo_turno, nova_aula, nome_professor, email_professor
                            ]
                            conn.update(worksheet="Página1", data=df_reservas)
                            st.success("✅ Reserva atualizada com sucesso!")
                            st.rerun()

else:
    st.info("👆 Preencha seu **Nome Completo** e **E-mail Institucional** acima para liberar o sistema.")
