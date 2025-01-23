import streamlit as st
import requests
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib.pyplot as plt
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
def realizar_requisicao_soap(mes, ano):
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
            <deal:Empresa_codigo>1</deal:Empresa_codigo>
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
        xaxis_title="Categorias",
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
def analise_margens(tipo, mes, ano):
    cdata_root = realizar_requisicao_soap(mes, ano)
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

    if tipo == "Análise Subsetorial":
        titulo = f"Resultados e Margens Brutas por Subsetor - {mes:02d}/{ano}"
        nomes, resultados, margens = calcular_resultados_margens(contas, cdata_root)
    else:
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

        contas_setorial = [
            {"nome": "Vendas", "receita": vendas_receita, "custo": vendas_custo},
            {"nome": "Pós-Vendas", "receita": pos_vendas_receita, "custo": pos_vendas_custo},
        ]
        titulo = f"Resultados e Margens Brutas por Setor - {mes:02d}/{ano}"
        nomes = ["Vendas", "Pós-Vendas"]
        resultados = [(-vendas_receita - vendas_custo)/1000, (-pos_vendas_receita - pos_vendas_custo)/1000] # em milhares de reais
        margens = [(vendas_receita + vendas_custo)/vendas_receita * 100 if vendas_receita != 0 else 0,
                   (pos_vendas_receita + pos_vendas_custo)/pos_vendas_receita * 100 if pos_vendas_receita != 0 else 0]

    grafico = criar_grafico(nomes, resultados, margens, titulo)
    return grafico

def calcular_dados_mensais_por_setor(ano):
    dados_mensais = {
        'Vendas': {'meses': [], 'resultados': [], 'margens': []},
        'Pós-Vendas': {'meses': [], 'resultados': [], 'margens': []},
    }
    for mes in range(1, 13):
        # Chama a função existente para pegar os dados XML do mês
        dados_mes = realizar_requisicao_soap(1, ano)  # Função já presente no seu código
        
        # Filtra os setores e calcula os resultados e margens
        for setor in ['Vendas', 'Pós-Vendas']:
            resultado_setor = dados_mes[dados_mes['Setor'] == setor]['Resultado'].sum()
            margem_setor = dados_mes[dados_mes['Setor'] == setor]['Margem Bruta'].mean()
            
            dados_mensais[setor]['meses'].append(mes)
            dados_mensais[setor]['resultados'].append(resultado_setor)
            dados_mensais[setor]['margens'].append(margem_setor)
    return dados_mensais



# Configuração inicial do Streamlit
st.set_page_config(layout="wide")
 
# Layout ajustado com espaçamento adicional
col_param, col_space, col_graficos = st.columns([0.8, 0.2, 3])  # Aumente ou diminua os valores conforme necessário
col_graficos.title("Análise de Margens Contábeis")
col_graficos_esq, col_graficos_dir = col_graficos.columns([1,1.5])
# Coluna de parâmetros (lado esquerdo)
with col_param:
    st.markdown("### Selecione os parâmetros de análise")
    ano = st.number_input("Ano", min_value=2000, max_value=2100, value=2024, step=1)
    mes = st.number_input("Mês", min_value=1, max_value=12, value=11, step=1)
    col_graficos_esq.subheader("Análise Setorial")
    col_graficos_dir.subheader("Análise Subsetorial")

    if st.button("Analisar"):
        grafico_setorial = analise_margens(tipo="Análise Setorial", mes=mes, ano=ano)
        grafico_subsetorial = analise_margens(tipo="Análise Subsetorial", mes=mes, ano=ano)
        col_graficos_esq.plotly_chart(grafico_setorial, use_container_width=True)
        col_graficos_dir.plotly_chart(grafico_subsetorial, use_container_width=True)

# Recuperar parâmetros selecionados
#ano = st.session_state.get('ano', 2024)
#mes = st.session_state.get('mes', 9)