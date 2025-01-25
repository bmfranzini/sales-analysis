import streamlit as st
import requests
import xml.etree.ElementTree as ET
import numpy as np
import plotly.graph_objects as go


# Função para calcular o último dia do mês
def ultimo_dia_mes(mes, ano):
    if mes in {1, 3, 5, 7, 8, 10, 12}:
        return 31
    elif mes in {4, 6, 9, 11}:
        return 30
    else:
        return 29 if (ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0)) else 28

# Função para fazer requisição SOAP e obter dados XML
def realizar_requisicao_soap(mes, ano, filial):
    ultimo_dia = ultimo_dia_mes(mes, ano)
    url = "https://gaivota.dealernetworkflow.com.br/aws_dealernetgateway.aspx"
    headers = {"Content-Type": "text/xml; charset=utf-8"}
    soap_body = f"""
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:deal="DealerNet">
    <soapenv:Header/>
    <soapenv:Body>
        <deal:WS_DealernetGateway.CONSULTASALDOCONTABIL>
            <deal:Usuario_identificador>portus</deal:Usuario_identificador>
            <deal:Usuariosenha_senha>Portus25@</deal:Usuariosenha_senha>
            <deal:Empresa_codigo>{filial}</deal:Empresa_codigo>
            <deal:Dtini>{ano}-{mes:02d}-01</deal:Dtini>
            <deal:Dtfin>{ano}-{mes:02d}-{ultimo_dia}</deal:Dtfin>
        </deal:WS_DealernetGateway.CONSULTASALDOCONTABIL>
    </soapenv:Body>
    </soapenv:Envelope>
    """
    response = requests.post(url, data=soap_body, headers=headers)
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        namespaces = {"soapenv": "http://schemas.xmlsoap.org/soap/envelope/", "deal": "DealerNet"}
        body = root.find("soapenv:Body", namespaces)
        response = body.find("deal:WS_DealernetGateway.CONSULTASALDOCONTABILResponse", namespaces)
        xml_retorno = response.find("deal:Xml_retorno", namespaces)
        if xml_retorno is not None and xml_retorno.text:
            return ET.fromstring(xml_retorno.text.strip())
    st.error("Erro na requisição ou processamento de dados.")
    return None

# Função para calcular resultados e margens
def calcular_resultados_margens(contas, cdata_root):
    resultados, margens, nomes = [], [], []
    for conta in contas:
        valor_receita = obter_valor_conta(cdata_root, conta["receita"])
        valor_custo = obter_valor_conta(cdata_root, conta["custo"])
        if valor_receita is not None and valor_custo is not None:
            resultado = -valor_receita - valor_custo
            margem = -resultado / valor_receita * 100 if valor_receita != 0 else 0
            nomes.append(conta["nome"])
            resultados.append(resultado / 1000)  # Em milhares de reais
            margens.append(margem)
    return nomes, resultados, margens

# Função para criar gráficos com Plotly
def criar_grafico(nomes, resultados, margens, titulo):
    fig = go.Figure()

    # Adicionar barras de resultados
    fig.add_trace(
        go.Bar(
            x=nomes,
            y=resultados,
            name="Resultado (mil R$)",
            marker_color="DodgerBlue",
            hovertemplate="<b>%{x}</b><br>Resultado: %{y:.2f} mil R$<extra></extra>"
        )
    )

    # Adicionar linha de margens
    fig.add_trace(
        go.Scatter(
            x=nomes,
            y=margens,
#            yaxis="y2",
            name="Margem Bruta (%)",
            mode="lines+markers",
            line=dict(color="OrangeRed"),
            marker=dict(size=8),
            hovertemplate="<b>%{x}</b><br>Margem: %{y:.2f}%<extra></extra>"
        )
    )

    # Ajustar layout
    fig.update_layout(
        title=titulo,
        yaxis_title="Resultado (mil R$)",
        yaxis=dict(title="Resultado (mil R$)", side="left"),
        yaxis2=dict(
            title="Margem Bruta (%)",
            overlaying="y",
            side="right"
        ),
        legend=dict(x=0.6, y=1.1),
        barmode="group",
        template="plotly_dark"
    )

    return fig


# Função para extrair valores das contas
def obter_valor_conta(cdata_root, conta_id):
    for item in cdata_root.findall(".//SDT_SaldoContabilItem"):
        if item.find("ContaIDNivel").text == conta_id:
            saldo_inicial = item.find("SaldoInicial").text
            saldo_final = item.find("SaldoFinal").text
            return np.round(float(saldo_final) - float(saldo_inicial), 2)
    return None

# Função principal de análise
def analise_margens(tipo, mes, ano, filial, num_filiais):
    
    contas = [
        {"nome": "VN Passageiros", "receita": "3.1.1.001.000001", "custo": "3.3.1.001.000001"},
        {"nome": "VN Comerciais Leves", "receita": "3.1.1.001.000002", "custo": "3.3.1.001.000002"},
        {"nome": "Seminovos", "receita": "3.1.1.002.000001", "custo": "3.3.1.002.000001"},
        {"nome": "Peças Atacado", "receita": "3.1.1.003.000001", "custo": "3.3.1.003.000001"},
        {"nome": "Peças Varejo", "receita": "3.1.1.003.000002", "custo": "3.3.1.003.000002"},
        {"nome": "Peças Mecânica", "receita": "3.1.1.003.000003", "custo": "3.3.1.003.000003"},
        {"nome": "Peças Funilaria e Pintura", "receita": "3.1.1.003.000004", "custo": "3.3.1.003.000004"},
        {"nome": "Peças Garantia", "receita": "3.1.1.003.000005", "custo": "3.3.1.003.000005"},
        {"nome": "Peças Interna", "receita": "3.1.1.003.000006", "custo": "3.3.1.003.000006"},
        {"nome": "Acessórios", "receita": "3.1.1.003.000007", "custo": "3.3.1.003.000007"},
        {"nome": "Combustíveis e Lubrificantes", "receita": "3.1.1.003.000008", "custo": "3.3.1.003.000008"},
        {"nome": "Pneus e Câmaras", "receita": "3.1.1.003.000009", "custo": "3.3.1.003.000009"},
    ]

    iterations = num_filiais if filial == 0 else 1

    if tipo == "Análise Subsetorial":
        titulo = f"Resultados e Margens Brutas por Subsetor - {mes:02d}/{ano}"
        for i in range(iterations):
            cdata_root = realizar_requisicao_soap(mes, ano, i+1)
            if cdata_root is None:
                return
            if i == 0:
                nomes, resultados, margens = calcular_resultados_margens(contas, cdata_root)
            else:
                _, res, mgs = calcular_resultados_margens(contas, cdata_root)
                resultados = [a + b for a, b in zip(resultados, res)]
                margens = [a + b for a, b in zip(margens, mgs)]
        
    else:
        for i in range(iterations):
            cdata_root = realizar_requisicao_soap(mes, ano, i+1)
            if cdata_root is None:
                return
            # Consolidar os subsetores para os setores "Vendas" e "Pós-Vendas"
            vendas_receita = sum(obter_valor_conta(cdata_root, conta["receita"]) for conta in contas[:3])
            vendas_custo = sum(obter_valor_conta(cdata_root, conta["custo"]) for conta in contas[:3])
            # gambiarra pois Ourinhos não tem "Peças Atacado"
            if filial == 3 or iterations == 3:
                pos_vendas_receita = sum(obter_valor_conta(cdata_root, conta["receita"]) for conta in contas[4:])
                pos_vendas_custo = sum(obter_valor_conta(cdata_root, conta["custo"]) for conta in contas[4:])
            else:
                pos_vendas_receita = sum(obter_valor_conta(cdata_root, conta["receita"]) for conta in contas[3:])
                pos_vendas_custo = sum(obter_valor_conta(cdata_root, conta["custo"]) for conta in contas[3:])
            res = [(-vendas_receita - vendas_custo)/1000, (-pos_vendas_receita - pos_vendas_custo)/1000] # em milhares de reais
            mgs = [(vendas_receita + vendas_custo)/vendas_receita * 100 if vendas_receita != 0 else 0,
                    (pos_vendas_receita + pos_vendas_custo)/pos_vendas_receita * 100 if pos_vendas_receita != 0 else 0]
            resultados = [a + b for a, b in zip(resultados, res)] if i > 0 else res
            margens = [a + b for a, b in zip(margens, mgs)] if i > 0 else mgs
        titulo = f"Resultados e Margens Brutas por Setor"
        nomes = ["Vendas", "Pós-Vendas"]
        

    grafico = criar_grafico(nomes, resultados, margens, titulo)
    return grafico

def analise_margens_ano(ano, filial):
    margens_ano = []
    resultados_ano = []
    for i in range(7,13): #começando a partir de julho, troca de sistema
        cdata_root = realizar_requisicao_soap(i, ano, filial)
        if cdata_root is None:
            return

        contas = [
            {"nome": "VN Passageiros", "receita": "3.1.1.001.000001", "custo": "3.3.1.001.000001"},
            {"nome": "VN Comerciais Leves", "receita": "3.1.1.001.000002", "custo": "3.3.1.001.000002"},
            {"nome": "Seminovos", "receita": "3.1.1.002.000001", "custo": "3.3.1.002.000001"},
            {"nome": "Peças Atacado", "receita": "3.1.1.003.000001", "custo": "3.3.1.003.000001"},
            {"nome": "Peças Varejo", "receita": "3.1.1.003.000002", "custo": "3.3.1.003.000002"},
            {"nome": "Peças Mecânica", "receita": "3.1.1.003.000003", "custo": "3.3.1.003.000003"},
            {"nome": "Peças Funilaria e Pintura", "receita": "3.1.1.003.000004", "custo": "3.3.1.003.000004"},
            {"nome": "Peças Garantia", "receita": "3.1.1.003.000005", "custo": "3.3.1.003.000005"},
            {"nome": "Peças Interna", "receita": "3.1.1.003.000006", "custo": "3.3.1.003.000006"},
            {"nome": "Acessórios", "receita": "3.1.1.003.000007", "custo": "3.3.1.003.000007"},
            {"nome": "Combustíveis e Lubrificantes", "receita": "3.1.1.003.000008", "custo": "3.3.1.003.000008"},
            {"nome": "Pneus e Câmaras", "receita": "3.1.1.003.000009", "custo": "3.3.1.003.000009"},
        ]

        # Consolidar os subsetores para os setores "Vendas" e "Pós-Vendas"
        vendas_receita = sum(
            obter_valor_conta(cdata_root, conta["receita"]) for conta in contas[:3]
        )
        vendas_custo = sum(
            obter_valor_conta(cdata_root, conta["custo"]) for conta in contas[:3]
        )

        pos_vendas_receita = sum(
            obter_valor_conta(cdata_root, conta["receita"]) for conta in contas[3:]
        )
        pos_vendas_custo = sum(
            obter_valor_conta(cdata_root, conta["custo"]) for conta in contas[3:]
        )
        titulo = f"Resultados e Margens Brutas por Setor"
        meses = ["Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        resultados_ano.append([(-vendas_receita - vendas_custo)/1000, (-pos_vendas_receita - pos_vendas_custo)/1000]) # em milhares de reais
        margens_ano.append([(vendas_receita + vendas_custo)/vendas_receita * 100 if vendas_receita != 0 else 0,
                (pos_vendas_receita + pos_vendas_custo)/pos_vendas_receita * 100 if pos_vendas_receita != 0 else 0])
        
        grafico = criar_grafico_anual(meses, resultados_ano, margens_ano, titulo)
    return grafico
    
def criar_grafico_anual(meses, resultados, margens, titulo):
    fig = go.Figure()

    # Adicionar barras de resultados
    fig.add_trace(
        go.Bar(
            x=meses,
            y=[resultado[0] for resultado in resultados],
            name="Vendas - Resultado",
            marker_color="DarkSlateBlue",
            hovertemplate="<b>%{x}</b><br>Resultado: %{y:.2f} mil R$<extra></extra>"
        )
    )

    fig.add_trace(
        go.Bar(
            x=meses,
            y=[resultado[1] for resultado in resultados],
            name="Pós-Vendas - Resultado",
            marker_color="RoyalBlue",
            hovertemplate="<b>%{x}</b><br>Resultado: %{y:.2f} mil R$<extra></extra>"
        )
    )
    
    # Ajustar layout
    fig.update_layout(
        barmode='group',  # Define agrupamento das barras
        title=titulo,
        xaxis_title="Meses",
        yaxis_title="Valores",
        legend_title="Indicadores",
        xaxis=dict(tickmode='linear')  # Garante que todos os meses sejam exibidos
    )

    return fig


# Configuração inicial do Streamlit
st.set_page_config(layout="wide")
 
# Layout ajustado com espaçamento adicional
col_param, col_space, col_graficos = st.columns([0.6, 0.2, 3])  # Aumente ou diminua os valores conforme necessário

# Coluna de parâmetros (lado esquerdo)
with col_param:
    st.markdown("### Selecione os parâmetros de análise")
    ano = st.number_input("Ano", min_value=2000, max_value=2100, value=2024, step=1)
    mes = st.number_input("Mês", min_value=1, max_value=12, value=11, step=1)
    filiais = ["Grupo Consolidado", "Araras", "Assis", "Ourinhos"]
    # Caixa de seleção com várias possibilidades
    filial = st.selectbox(
        "Filial",
        filiais
    )
    col_graficos.title(f"Análise de Margens Contábeis - {filial} - {mes:02d}/{ano}")
    col_graficos_esq, col_graficos_dir = col_graficos.columns([1,2])
    col_graficos_esq.subheader(f"Análise Setorial")
    col_graficos_dir.subheader("Análise Subsetorial")

    if st.button("Analisar"):
        indice_filial = filiais.index(filial)
        grafico_setorial = analise_margens(tipo="Análise Setorial", mes=mes, ano=ano, filial=indice_filial, num_filiais=len(filiais)-1)
        grafico_subsetorial = analise_margens(tipo="Análise Subsetorial", mes=mes, ano=ano, filial=indice_filial, num_filiais=len(filiais)-1)
        #grafico_anual = analise_margens_ano(ano=ano, filial=indice_filial)
        col_graficos_esq.plotly_chart(grafico_setorial, use_container_width=True)
        col_graficos_dir.plotly_chart(grafico_subsetorial, use_container_width=True)
        #col_graficos.plotly_chart(grafico_anual, use_container_width=True)

# Recuperar parâmetros selecionados
#ano = st.session_state.get('ano', 2024)
#mes = st.session_state.get('mes', 9)