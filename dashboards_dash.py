import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import requests
import xml.etree.ElementTree as ET
import numpy as np

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

# Função para extrair valores das contas
def obter_valor_conta(cdata_root, conta_id):
    for item in cdata_root.findall(".//SDT_SaldoContabilItem"):
        if item.find("ContaIDNivel").text == conta_id:
            saldo_inicial = item.find("SaldoInicial").text
            saldo_final = item.find("SaldoFinal").text
            return np.round(float(saldo_final) - float(saldo_inicial), 2)
    return None

# Configuração inicial do Dash
app = dash.Dash(__name__)
app.title = "Análise de Margens Contábeis"

app.layout = html.Div([
    html.H1("Análise de Margens Contábeis", style={"textAlign": "center"}),

    html.Div([
        html.Label("Tipo de Análise:"),
        dcc.Dropdown(
            id="tipo-analise",
            options=[
                {"label": "Análise Setorial", "value": "Análise Setorial"},
                {"label": "Análise Subsetorial", "value": "Análise Subsetorial"},
            ],
            value="Análise Setorial",
        ),

        html.Label("Ano:"),
        dcc.Input(id="ano", type="number", value=2025, min=2000, max=2100),

        html.Label("Mês:"),
        dcc.Dropdown(
            id="mes",
            options=[{"label": f"{m:02d}", "value": m} for m in range(1, 13)],
            value=1,
        ),

        html.Button("Analisar", id="botao-analisar", n_clicks=0),
    ], style={"width": "50%", "margin": "auto"}),

    dcc.Graph(id="grafico-resultados")
])

@app.callback(
    Output("grafico-resultados", "figure"),
    Input("botao-analisar", "n_clicks"),
    [Input("tipo-analise", "value"), Input("mes", "value"), Input("ano", "value")],
)
def atualizar_grafico(n_clicks, tipo, mes, ano):
    cdata_root = realizar_requisicao_soap(mes, ano)
    if cdata_root is None:
        return go.Figure()

    if tipo == "Análise Subsetorial":
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
    else:
        contas = [
            {"nome": "Vendas", "receita": "3.1.1.001.000001", "custo": "3.3.1.001.000001"},
            {"nome": "Pós-Vendas", "receita": "3.1.1.002.000001", "custo": "3.3.1.002.000001"},
        ]

    nomes, resultados, margens = calcular_resultados_margens(contas, cdata_root)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=nomes, y=resultados, name="Resultado (mil R$)", marker_color="DodgerBlue"))
    fig.add_trace(go.Scatter(x=nomes, y=margens, name="Margem Bruta (%)", mode="lines+markers", marker_color="OrangeRed"))

    fig.update_layout(
        title=f"{tipo} - {mes:02d}/{ano}",
        xaxis_title="Subsetores" if tipo == "Análise Subsetorial" else "Setores",
        yaxis_title="Valores",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig

if __name__ == "__main__":
    app.run_server(debug=True)
