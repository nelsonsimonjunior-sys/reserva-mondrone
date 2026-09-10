import pandas as pd
import streamlit as st
import uuid
from streamlit_gsheets import GSheetsConnection

# Configuração da página
st.set_page_config(
    page_title="Reserva de Equipamentos - Colégio Mondrone", page_icon="LogoMondrone.jpg"
)

st.title(":LogoMondrone.jpg: Reserva de Equipamentos - Colégio Mondrone")
st.write("Selecione os dados abaixo para agendar um equipamento.")

# Conexão com a planilha do Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)


# Função para carregar os dados atualizados
def carregar_dados():
    return conn.read(ttl=0)


# Carrega as reservas atuais
try:
    df_reservas = carregar_dados()
except Exception:
    df_reservas = pd.DataFrame(
        columns=["Professor", "Equipamento", "Data", "Turno", "Aula"]
    )

# Formulário de Agendamento
with st.form("form_reserva", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        professor = st.text_input("Nome do Professor(a):")
        equipamento = st.selectbox(
            "Equipamento:",
            [
                "Tablets",
                "Notebooks-Somente 3ºanos",
                "Chromebooks",
                "Netbooks",
            ],
        )
        data_reserva = st.date_input(
            "Data da Reserva:", format="DD/MM/YYYY"
        ).strftime("%d/%m/%Y")

    with col2:
        turno = st.selectbox("Turno:", ["Manhã", "Tarde", "Noite"])
        aula = st.selectbox(
            "Aula / Horário:",
            [
                "1ª Aula",
                "2ª Aula",
                "3ª Aula",
                "4ª Aula",
                "5ª Aula",
                "6ª Aula",
            ],
        )

    btn_agendar = st.form_submit_button("Confirmar Reserva")

# Validação do Agendamento ao clicar no botão
if btn_agendar:
    if not professor.strip():
        st.error("⚠️ Por favor, preencha o nome do professor.")
    elif turno != "Manhã" and aula == "6ª Aula":
        st.error(
            "⚠️ **Atenção:** A **6ª Aula** está disponível apenas no turno da **Manhã**."
        )
    else:
        # Verifica se já existe uma reserva idêntica na planilha
        conflito = False
        if not df_reservas.empty:
            linhas_conflito = df_reservas[
                (df_reservas["Equipamento"] == equipamento)
                & (df_reservas["Data"] == str(data_reserva))
                & (df_reservas["Turno"] == turno)
                & (df_reservas["Aula"] == aula)
            ]
            if len(linhas_conflito) > 0:
                conflito = True

        if conflito:
            st.error(
                f"❌ **CONFLITO DE AGENDA:** O equipamento **{equipamento}** já foi reservado para a **{aula} ({turno})** no dia **{data_reserva}**!"
            )
        else:
          # Prepara a nova linha
            nova_reserva = pd.DataFrame(
                [
                    {
                        "Professor": professor,
                        "Equipamento": equipamento,
                        "Data": str(data_reserva),
                        "Turno": turno,
                        "Aula": aula,
                    }
                ]
            )


            # Adiciona a nova linha à planilha existente
            df_atualizado = pd.concat(
                [df_reservas, nova_reserva], ignore_index=True
            )
            conn.update(worksheet="Página1", data=df_atualizado)

            st.success("✅ **Reserva realizada com sucesso!**")
            st.rerun()

# Exibição das Reservas Existentes
st.divider()
st.subheader("📋 Agendamentos Cadastrados")
if not df_reservas.empty:
    st.dataframe(df_reservas, use_container_width=True)
else:
    st.info("Nenhuma reserva cadastrada até o momento.")
