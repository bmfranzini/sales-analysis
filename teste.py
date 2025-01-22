import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
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
            <deal:Senha>123456</deal:Senha>
            <deal:DataInicial>{ano}-{mes:02d}-01</deal:DataInicial>
            <deal:DataFinal>{ano}-{mes:02d}-{ultimo_dia}</deal:DataFinal>
        </deal:WS_DealernetGateway.CONSULTASALDOCONTABIL>
    </soapenv:Body>
    </soapenv:Envelope>
    """
    response = requests.post(url, data=soap_body, headers=headers)
    return ET.fromstring(response.content)

# Função para processar os dados XML e retornar um DataFrame
def processar_dados_xml(xml_tree):
    namespaces = {'ns': 'DealerNet'}
    dados = []
    for registro in xml_tree.findall(".//ns:Registro", namespaces):
        setor = registro.find("ns:Setor", namespaces).text
        resultado = float(registro.find("ns:Resultado", namespaces).text)
        margem = float(registro.find("ns:Margem", namespaces).text)
        dados.append({"Setor": setor, "Resultado": resultado, "Margem": margem})
    return pd.DataFrame(dados)

# Função para obter dados mensais do ano selecionado
def obter_dados_anuais(ano):
    dados_anuais = []
    for mes in range(1, 13):
        xml_tree = realizar_requisicao_soap(mes, ano)
        df_mes = processar_dados_xml(xml_tree)
        df_mes["Mês"] = mes
        dados_anuais.append(df_mes)
    return pd.concat(dados_anuais, ignore_index=True)

# Configuração da interface Streamlit
st.set_page_config(page_title="Análise de Margens Contábeis", layout="wide")
st.title("Análise de Margens Contábeis")

# Seleção de parâmetros
ano = st.sidebar.number_input("Ano", min_value=2000, max_value=2100, value=2024, step=1)
mes = st.sidebar.number_input("Mês", min_value=1, max_value=12, value=11, step=1)
st.sidebar.button("Analisar")

# Obtenção de dados
xml_tree = realizar_requisicao_soap(mes, ano)
dados_atual = processar_dados_xml(xml_tree)

dados_anuais = obter_dados_anuais(ano)

# Gráficos
fig1 = go.Figure()
fig1.add_trace(go.Bar(x=dados_atual["Setor"], y=dados_atual["Resultado"], name="Resultado (mil R$)", marker_color="blue"))
fig1.add_trace(go.Scatter(x=dados_atual["Setor"], y=dados_atual["Margem"], name="Margem Bruta (%)", mode="lines+markers", line=dict(color="red")))
fig1.update_layout(title=f"Resultados e Margens Brutas por Setor - {mes}/{ano}", xaxis_title="Setores", yaxis_title="Valores", legend_title="Indicadores")

fig2 = go.Figure()
fig2.add_trace(go.Bar(x=dados_atual["Setor"], y=dados_atual["Resultado"], name="Resultado (mil R$)", marker_color="blue"))
fig2.add_trace(go.Scatter(x=dados_atual["Setor"], y=dados_atual["Margem"], name="Margem Bruta (%)", mode="lines+markers", line=dict(color="red")))
fig2.update_layout(title=f"Resultados e Margens Brutas por Subsetor - {mes}/{ano}", xaxis_title="Subsetores", yaxis_title="Valores", legend_title="Indicadores")

fig3 = go.Figure()
for setor in dados_anuais["Setor"].unique():
    df_setor = dados_anuais[dados_anuais["Setor"] == setor]
    fig3.add_trace(go.Scatter(x=df_setor["Mês"], y=df_setor["Resultado"], mode="lines+markers", name=f"{setor} - Resultado"))
    fig3.add_trace(go.Scatter(x=df_setor["Mês"], y=df_setor["Margem"], mode="lines+markers", name=f"{setor} - Margem", line=dict(dash="dash")))
fig3.update_layout(title=f"Resultados e Margens Mensais por Setor - {ano}", xaxis_title="Meses", yaxis_title="Valores", legend_title="Indicadores")

# Exibição no layout
col1, col2 = st.columns(2)
col1.plotly_chart(fig1, use_container_width=True)
col2.plotly_chart(fig2, use_container_width=True)

st.plotly_chart(fig3, use_container_width=True)
