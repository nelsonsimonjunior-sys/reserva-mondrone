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
except Exception:
    df_reservas = pd.DataFrame(columns=["ID", "Data", "Turno", "Aula", "Equipamento", "Professor"])

# Lista de Professores Cadastrados (Validação 1)
LISTA_PROFESSORES = [
    "Selecione seu e-mail...",
    "ana.mandelli@escola.pr.gov.br",
    "danielewski.luana@escola.pr.gov.br",
    "eliana.gava@escola.pr.gov.br",
    "francielle.ghellere@escola.pr.gov.br",
    "maria.garbossa@escola.pr.gov.br",
    "os.santos.douglas0912@escola.pr.gov.br"
]

LISTA_EQUIPAMENTOS = ["Tablets", "Netbooks", "Notebooks (Apenas 3º Ano)", "Projetor / Caixa de Som"]
LISTA_TURNOS = ["Manhã", "Tarde", "Noite"]
LISTA_AULAS = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula"]

# Identificação do usuário
st.markdown("---")
professor_logado = st.selectbox("👤 **Identifique-se (Seu E-mail):**", LISTA_PROFESSORES)

if professor_logado != "Selecione seu e-mail...":

    # Divisão do App em Abas
    aba_criar, aba_gerenciar = st.tabs(["➕ Nova Reserva", "✏️ Minhas Reservas (Alterar / Excluir)"])

    # =========================================================
    # ABA 1: NOVA RESERVA (Com Validações 2 e 3)
    # =========================================================
    with aba_criar:
        st.subheader("Agendar Equipamento")
        
        hoje = datetime.date.today()
        
        # Validação 2: Impede seleção de datas passadas
        data_reserva = st.date_input("Data da Reserva:", min_value=hoje, value=hoje)
        
        # Alerta se for fim de semana
        if data_reserva.weekday() in [5, 6]:
            st.warning("⚠️ Atenção: A data selecionada é um fim de semana.")

        col1, col2, col3 = st.columns(3)
        with col1:
            equipamento = st.selectbox("Equipamento:", LISTA_EQUIPAMENTOS)
        with col2:
            turno = st.selectbox("Turno:", LISTA_TURNOS)
        with col3:
            aula = st.selectbox("Aula:", LISTA_AULAS)

        # Validação 3: Trava de confirmação
        if st.button("Confirmar Reserva", type="primary"):
            if data_reserva.weekday() in [5, 6]:
                st.error("❌ Não é possível realizar reservas para sábados ou domingos.")
            else:
                # Checa se há conflito no mesmo dia, turno, aula e equipamento
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
                    st.error(f"❌ **CONFLITO DE AGENDA:** O equipamento **{equipamento}** já foi reservado para este horário.")
                else:
                    # Cria a nova reserva
                    nova_reserva = pd.DataFrame([{
                        "ID": str(uuid.uuid4())[:8],
                        "Data": str(data_reserva),
                        "Turno": turno,
                        "Aula": aula,
                        "Equipamento": equipamento,
                        "Professor": professor_logado
                    }])

                    df_atualizado = pd.concat([df_reservas, nova_reserva], ignore_index=True)
                    conn.update(worksheet="Página1", data=df_atualizado)
                    st.success("✅ **Reserva realizada com sucesso!**")
                    st.rerun()

    # =========================================================
    # ABA 2: ALTERAR OU EXCLUIR RESERVAS PRÓPRIAS
    # =========================================================
    with aba_gerenciar:
        st.subheader(f"Reservas de {professor_logado}")

        # Filtra estritamente apenas as reservas pertencentes ao professor logado
        minhas_reservas = df_reservas[df_reservas["Professor"] == professor_logado]

        if minhas_reservas.empty:
            st.info("Você ainda não possui nenhuma reserva cadastrada.")
        else:
            st.dataframe(minhas_reservas[["Data", "Turno", "Aula", "Equipamento"]], use_container_width=True)

            # Seleciona uma reserva específica pelo ID
            opcoes_ids = minhas_reservas["ID"].tolist()
            reserva_id_selecionada = st.selectbox(
                "Selecione o código da reserva que deseja alterar ou excluir:", 
                opcoes_ids,
                format_func=lambda x: f"ID: {x} - {minhas_reservas[minhas_reservas['ID']==x]['Data'].values[0]} ({minhas_reservas[minhas_reservas['ID']==x]['Equipamento'].values[0]})"
            )

            reserva_atual = minhas_reservas[minhas_reservas["ID"] == reserva_id_selecionada].iloc[0]

            col_alt, col_exc = st.columns(2)

            # Opção A: Excluir Reserva
            with col_exc:
                st.markdown("### 🗑️ Excluir Reserva")
                if st.button("Excluir esta Reserva", type="secondary"):
                    df_atualizado = df_reservas[df_reservas["ID"] != reserva_id_selecionada]
                    conn.update(worksheet="Página1", data=df_atualizado)
                    st.success("Reserva excluída com sucesso!")
                    st.rerun()

            # Opção B: Alterar Reserva
            with col_alt:
                st.markdown("### ✏️ Editar Dados")
                nova_data = st.date_input(
                    "Nova Data:", 
                    value=datetime.datetime.strptime(str(reserva_atual["Data"]), "%Y-%m-%d").date(),
                    min_value=hoje,
                    key="edit_data"
                )
                novo_equipamento = st.selectbox("Novo Equipamento:", LISTA_EQUIPAMENTOS, index=LISTA_EQUIPAMENTOS.index(reserva_atual["Equipamento"]), key="edit_eq")
                novo_turno = st.selectbox("Novo Turno:", LISTA_TURNOS, index=LISTA_TURNOS.index(reserva_atual["Turno"]), key="edit_tur")
                nova_aula = st.selectbox("Nova Aula:", LISTA_AULAS, index=LISTA_AULAS.index(reserva_atual["Aula"]), key="edit_aul")

                if st.button("Salvar Alterações"):
                    # Remove a reserva antiga temporariamente para checar conflito
                    df_outras = df_reservas[df_reservas["ID"] != reserva_id_selecionada]
                    
                    conflito_edicao = df_outras[
                        (df_outras["Equipamento"] == novo_equipamento) &
                        (df_outras["Data"] == str(nova_data)) &
                        (df_outras["Turno"] == novo_turno) &
                        (df_outras["Aula"] == nova_aula)
                    ]

                    if len(conflito_edicao) > 0:
                        st.error("❌ Conflito! Já existe reserva para este equipamento neste dia/horário.")
                    else:
                        # Atualiza os dados da linha específica
                        df_reservas.loc[df_reservas["ID"] == reserva_id_selecionada, ["Data", "Equipamento", "Turno", "Aula"]] = [
                            str(nova_data), novo_equipamento, novo_turno, nova_aula
                        ]
                        conn.update(worksheet="Página1", data=df_reservas)
                        st.success("✅ Reserva atualizada com sucesso!")
                        st.rerun()

else:
    st.info("👆 Selecione o seu e-mail no campo acima para acessar o sistema de reservas.")
