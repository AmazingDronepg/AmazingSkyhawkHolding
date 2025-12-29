import streamlit as st
import pandas as pd
import sqlite3
import datetime
from fpdf import FPDF
import os
import base64

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================
st.set_page_config(page_title="SkyHawk & Amazing CRM v33", layout="wide", page_icon="🚀")

PASTA_DO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_LOGO = os.path.join(PASTA_DO_SCRIPT, "logo_holding.png")


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================
def get_image_base64(path):
    if not os.path.exists(path): return ""
    try:
        with open(path, "rb") as image_file:
            return f"data:image/png;base64,{base64.b64encode(image_file.read()).decode()}"
    except:
        return ""


def calcular_cenarios_fiscais_detalhado(faturamento_mensal, empresa_tipo):
    faturamento_anual = faturamento_mensal * 12
    analise = {}

    if faturamento_anual <= 180000:
        faixa = "1 (Até 180k)";
        aliq_base = 0.06 if empresa_tipo == 'Engenharia' else 0.045
    elif faturamento_anual <= 360000:
        faixa = "2 (180k - 360k)";
        aliq_base = 0.112 if empresa_tipo == 'Engenharia' else 0.09
    elif faturamento_anual <= 720000:
        faixa = "3 (360k - 720k)";
        aliq_base = 0.135 if empresa_tipo == 'Engenharia' else 0.102
    else:
        faixa = "4+ (Acima de 720k)";
        aliq_base = 0.16 if empresa_tipo == 'Engenharia' else 0.14

    analise['faixa'] = faixa
    analise['faturamento_anual'] = faturamento_anual
    dicas = []

    if empresa_tipo == "Seguranca":
        analise['regime_provavel'] = "Simples Nacional - Anexo IV"
        imposto_simples = faturamento_mensal * aliq_base
        inss_patronal_est = faturamento_mensal * 0.40 * 0.20
        analise['custo_total_est'] = imposto_simples + inss_patronal_est
        dicas.append("ANÁLISE DE RISCO (ANEXO IV): Monitoramento paga INSS Patronal (20%) à parte.")
        dicas.append("RECOMENDAÇÃO: Avaliar Lucro Presumido se a folha for alta.")

    elif empresa_tipo == "Engenharia":
        folha_necessaria = faturamento_mensal * 0.28
        analise['regime_provavel'] = "Simples Nacional - Fator R"
        imposto_anexo_iii = faturamento_mensal * aliq_base
        imposto_anexo_v = faturamento_mensal * 0.155
        analise['custo_total_est'] = imposto_anexo_iii
        dicas.append(f"ESTRATÉGIA FATOR R: Mantenha folha acima de R$ {folha_necessaria:,.2f} (28%).")
        dicas.append(f"ECONOMIA: Aprox. R$ {imposto_anexo_v - imposto_anexo_iii:,.2f} mensais vs Anexo V.")

    analise['dicas'] = dicas
    return analise


def gerar_analise_roi(contrato_escolhido, total_mensal_escolhido, duracao):
    analise = {}
    custo_equipamento = 160000.00
    gap_mensal_economia = 8000.00
    meses_payback = custo_equipamento / gap_mensal_economia

    if "Venda" in contrato_escolhido:
        meses_lucro = duracao - meses_payback
        if meses_lucro > 0:
            lucro_projetado = meses_lucro * gap_mensal_economia
            titulo = f"💰 Decisão Lucrativa: Economia de R$ {lucro_projetado:,.2f}"
            texto_pdf = (
                f"ANÁLISE DE LUCRO REAL: Esta modalidade é a mais rentável para {duracao} meses. "
                f"O equipamento se paga no mês {int(meses_payback)}. Economia direta de R$ {lucro_projetado:,.2f}."
            )
        else:
            titulo = "⚠️ Alerta de Viabilidade Financeira"
            texto_pdf = (
                f"ANÁLISE CRÍTICA: Para {duracao} meses, a aquisição não atinge o break-even (20 meses). "
                "Comodato é mais seguro."
            )
        texto_html = f"<p style='color:#1b5e20'><b>{titulo}</b></p><p>{texto_pdf}</p>"
    else:
        if duracao >= 36:
            lucro_perdido = (duracao - meses_payback) * gap_mensal_economia
            titulo = "ℹ️ Análise Comparativa: Comodato vs Compra"
            texto_pdf = (
                f"ANÁLISE DE CENÁRIO: Comodato é seguro (Zero CAPEX). "
                f"Porém, na Compra, o equipamento se pagaria no mês 20, gerando economia de R$ {lucro_perdido:,.2f}."
            )
        else:
            titulo = "✅ Comodato: A Melhor Escolha para este Prazo"
            texto_pdf = (
                f"VEREDICTO: Para {duracao} meses, o Comodato é a única opção viável, "
                "evitando imobilização de R$ 160k sem retorno."
            )
        texto_html = f"<p style='color:#1b5e20'><b>{titulo}</b></p><p>{texto_pdf}</p>"

    analise['titulo'] = titulo
    analise['texto'] = texto_html
    analise['pdf_text'] = texto_pdf
    return analise


# =============================================================================
# BANCO DE DADOS
# =============================================================================
def init_db():
    conn = sqlite3.connect("skyhawk_v33.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS propostas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        tipo_contrato TEXT,
        duracao_meses INTEGER,
        resumo_servicos TEXT,
        valor_total REAL,
        fat_amazing REAL,
        fat_skyhawk REAL,
        empresa_destino TEXT,
        data_registro TEXT
    )
    """)
    conn.commit()
    conn.close()


def salvar_venda(cliente, contrato, duracao, servicos, total, fat_amz, fat_sky, empresa):
    conn = sqlite3.connect("skyhawk_v33.db")
    cursor = conn.cursor()
    data_hoje = datetime.datetime.now().strftime("%d/%m/%Y")
    cursor.execute("""
        INSERT INTO propostas (cliente, tipo_contrato, duracao_meses, resumo_servicos, valor_total, fat_amazing, fat_skyhawk, empresa_destino, data_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (cliente, contrato, duracao, servicos, total, fat_amz, fat_sky, empresa, data_hoje))
    conn.commit()
    conn.close()


def carregar_dados():
    conn = sqlite3.connect("skyhawk_v33.db")
    df = pd.read_sql_query("SELECT * FROM propostas", conn)
    conn.close()
    return df


def calcular_totais(carrinho):
    total = 0.0
    fat_sky = 0.0
    fat_amz = 0.0
    for item in carrinho:
        total += item['valor_total']
        if "Monitoramento" in item['nome']:
            fat_sky += item['valor_total']
        else:
            fat_amz += item['valor_total']

    if fat_sky > 0 and fat_amz > 0:
        empresa = "CONTRATO HÍBRIDO"
    elif fat_amz > 0:
        empresa = "AmazingDrone Solutions"
    else:
        empresa = "SkyHawk Security"
    return total, fat_sky, fat_amz, empresa


# =============================================================================
# GERADORES DE PDF (COM CORREÇÃO DE POSICIONAMENTO)
# =============================================================================
def gerar_proposta_pdf(cliente, contrato, duracao, carrinho, total, roi_data):
    pdf = FPDF()
    pdf.add_page()

    # --- CORREÇÃO DE POSICIONAMENTO ---
    if os.path.exists(ARQUIVO_LOGO):
        # Logo em Y=10, largura 100
        pdf.image(ARQUIVO_LOGO, x=55, y=10, w=100)

    # Aumentado o espaço vertical para 65 (antes era 50) para evitar sobreposição
    pdf.set_y(65)

    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "PROPOSTA COMERCIAL INTEGRADA", 0, 1, 'C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 5, "Amazing SkyHawk Holding", 0, 1, 'C')
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, f"Cliente: {cliente}", 0, 1)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Modalidade: {contrato} | Vigência: {duracao} meses", 0, 1)

    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, pdf.get_y(), 190, 45, 'F')
    pdf.set_xy(15, pdf.get_y() + 5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 6, "Analise de Viabilidade & Recomendacao:", 0, 1)
    pdf.set_font("Arial", '', 9)
    pdf.multi_cell(180, 5, roi_data['pdf_text'])

    pdf.ln(15)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(0, 77, 64);
    pdf.set_text_color(255, 255, 255)
    pdf.cell(110, 10, "Servico", 1, 0, 'L', True)
    pdf.cell(30, 10, "Qtd", 1, 0, 'C', True)
    pdf.cell(50, 10, "Total (R$)", 1, 1, 'R', True)

    pdf.set_text_color(0, 0, 0);
    pdf.set_font("Arial", '', 10)
    for item in carrinho:
        pdf.cell(110, 10, item['nome'][:55], 1)
        pdf.cell(30, 10, f"{item['qtd']} {item['unidade']}", 1, 0, 'C')
        pdf.cell(50, 10, f"{item['valor_total']:,.2f}", 1, 1, 'R')

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Total Mensal: R$ {total:,.2f}", 0, 1, 'R')

    pdf.set_y(-45);
    y_sig = pdf.get_y();
    pdf.set_font("Arial", '', 8)
    pdf.line(10, y_sig, 65, y_sig);
    pdf.text(15, y_sig + 5, "Diretoria SkyHawk Security")
    pdf.line(75, y_sig, 130, y_sig);
    pdf.text(80, y_sig + 5, "Engenharia AmazingDrone")
    pdf.line(140, y_sig, 195, y_sig);
    pdf.text(145, y_sig + 5, "De Acordo (Cliente)")

    return pdf.output(dest='S').encode('latin-1')


def gerar_relatorio_geral_completo_pdf(df):
    pdf = FPDF()
    pdf.add_page()

    # --- CORREÇÃO DE POSICIONAMENTO ---
    if os.path.exists(ARQUIVO_LOGO):
        pdf.image(ARQUIVO_LOGO, x=55, y=10, w=100)

    # Aumentado o espaço vertical para 65
    pdf.set_y(65)

    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 10, "RELATÓRIO GERAL DE INTELIGÊNCIA", 0, 1, 'C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 5, f"Data: {datetime.datetime.now().strftime('%d/%m/%Y')} | Holding Consolidada", 0, 1, 'C')
    pdf.ln(10)

    total_geral = df['valor_total'].sum()
    total_sky = df['fat_skyhawk'].sum()
    total_amz = df['fat_amazing'].sum()

    analise_sky = calcular_cenarios_fiscais_detalhado(total_sky, "Seguranca")
    analise_amz = calcular_cenarios_fiscais_detalhado(total_amz, "Engenharia")

    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, pdf.get_y(), 190, 30, 'F')
    y_start = pdf.get_y()

    pdf.set_xy(10, y_start + 5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(63, 10, "FATURAMENTO HOLDING", 0, 0, 'C')
    pdf.cell(63, 10, "SKYHAWK", 0, 0, 'C')
    pdf.cell(63, 10, "AMAZING", 0, 1, 'C')

    pdf.set_font("Arial", 'B', 14);
    pdf.set_text_color(0, 77, 64)
    pdf.cell(63, 10, f"R$ {total_geral:,.2f}", 0, 0, 'C')
    pdf.set_text_color(0, 0, 0)
    pdf.cell(63, 10, f"R$ {total_sky:,.2f}", 0, 0, 'C')
    pdf.cell(63, 10, f"R$ {total_amz:,.2f}", 0, 1, 'C')
    pdf.ln(15)

    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "ESTRATEGIA TRIBUTARIA E ELISAO FISCAL", 0, 1, 'L')
    pdf.ln(2)

    pdf.set_fill_color(224, 242, 241)
    pdf.rect(10, pdf.get_y(), 190, 55, 'F')
    pdf.set_xy(15, pdf.get_y() + 5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 6, f"1. SKYHAWK SECURITY (Recorrencia: R$ {total_sky:,.2f}/mes)", 0, 1)
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 5,
             f"Estimativa Anual: R$ {analise_sky['faturamento_anual']:,.2f} | Regime: {analise_sky['regime_provavel']}",
             0, 1)
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(0, 5, "Analise de Otimizacao:", 0, 1)
    pdf.set_font("Arial", '', 9)
    for dica in analise_sky['dicas']:
        pdf.multi_cell(180, 5, f"- {dica}")
    pdf.ln(5)

    pdf.set_fill_color(255, 243, 224)
    pdf.rect(10, pdf.get_y(), 190, 55, 'F')
    pdf.set_xy(15, pdf.get_y() + 5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 6, f"2. AMAZING DRONE SOLUTIONS (Recorrencia: R$ {total_amz:,.2f}/mes)", 0, 1)
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 5,
             f"Estimativa Anual: R$ {analise_amz['faturamento_anual']:,.2f} | Regime: {analise_amz['regime_provavel']}",
             0, 1)
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(0, 5, "Analise de Otimizacao (Fator R):", 0, 1)
    pdf.set_font("Arial", '', 9)
    for dica in analise_amz['dicas']:
        pdf.multi_cell(180, 5, f"- {dica}")

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Detalhamento de Contratos", 0, 1, 'L')
    pdf.set_font("Arial", 'B', 8)
    pdf.set_fill_color(0, 77, 64);
    pdf.set_text_color(255, 255, 255)
    pdf.cell(10, 8, "ID", 1, 0, 'C', True)
    pdf.cell(50, 8, "Cliente", 1, 0, 'C', True)
    pdf.cell(25, 8, "Contrato", 1, 0, 'C', True)
    pdf.cell(30, 8, "Total", 1, 0, 'C', True)
    pdf.cell(37.5, 8, "Fat. Sky", 1, 0, 'C', True)
    pdf.cell(37.5, 8, "Fat. Amz", 1, 1, 'C', True)

    pdf.set_font("Arial", '', 8);
    pdf.set_text_color(0, 0, 0)
    for index, row in df.iterrows():
        pdf.cell(10, 8, str(row['id']), 1, 0, 'C')
        pdf.cell(50, 8, str(row['cliente'])[:25], 1, 0, 'C')
        pdf.cell(25, 8, str(row['tipo_contrato']).split(' ')[0], 1, 0, 'C')
        pdf.cell(30, 8, f"{row['valor_total']:,.2f}", 1, 0, 'C')
        pdf.cell(37.5, 8, f"{row['fat_skyhawk']:,.2f}", 1, 0, 'C')
        pdf.cell(37.5, 8, f"{row['fat_amazing']:,.2f}", 1, 1, 'C')

    return pdf.output(dest='S').encode('latin-1')


def gerar_proposta_html(cliente, contrato, duracao, carrinho, total, roi_data):
    img_b64 = get_image_base64(ARQUIVO_LOGO)
    img_tag = f'<img src="{img_b64}" class="logo-img">' if img_b64 else ''
    itens_html = ""
    for item in carrinho:
        desc_extra = ""
        if "Monitoramento" in item['nome']:
            extras = item['qtd'] - 3
            desc = "(Base 3 Rondas)"
            if extras > 0: desc = f"(Base 3 Rondas + {extras} Extras)"
            desc_extra = f"<br><small>{desc}</small>"
        itens_html += f"<tr><td>{item['nome']} <small>({item['qtd']} {item['unidade']})</small>{desc_extra}</td><td style='text-align:right'>R$ {item['valor_total']:.2f}</td></tr>"

    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Helvetica', sans-serif; padding: 40px; color: #333; }}
            .header-container {{ text-align: center; border-bottom: 4px solid #004d40; padding-bottom: 20px; }}
            .logo-img {{ height: 120px; width: auto; object-fit: contain; }}
            .roi-box {{ background-color: #f1f8e9; padding: 25px; border-left: 6px solid #33691e; margin: 30px 0; border-radius: 8px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 25px; }}
            th {{ background-color: #004d40; color: white; padding: 15px; text-align: left; }}
            td {{ border-bottom: 1px solid #ddd; padding: 15px; }}
            .total {{ text-align: right; font-size: 28px; font-weight: bold; margin-top: 30px; color: #004d40; }}
            .footer {{ margin-top: 50px; text-align: center; color: #888; font-size: 12px; }}
            .signatures {{ margin-top: 80px; display: flex; justify-content: space-between; }}
            .sig-line {{ width: 30%; border-top: 1px solid #333; text-align: center; font-size: 12px; padding-top: 10px; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="header-container">
            {img_tag}
            <h1 style="margin:15px 0 0 0; color:#004d40; font-size:24px;">PROPOSTA TÉCNICA E COMERCIAL</h1>
        </div>
        <div style="margin-top: 30px;">
            <p><strong>Cliente:</strong> {cliente}</p>
            <p><strong>Modalidade:</strong> {contrato}</p>
            <p><strong>Vigência:</strong> {duracao} Meses</p>
        </div>
        <div class="roi-box">
            <h3 style="margin-top:0; color:#1b5e20">{roi_data['titulo']}</h3>
            {roi_data['texto']}
        </div>
        <h3 style="color:#004d40; border-bottom: 2px solid #eee; padding-bottom: 10px;">Detalhamento Financeiro</h3>
        <table>
            <tr><th>Descrição do Serviço</th><th style="text-align:right">Investimento Mensal</th></tr>
            {itens_html}
        </table>
        <div class="total">Total Mensal: R$ {total:,.2f}</div>
        <div class="signatures">
            <div class="sig-line">Diretoria<br>SkyHawk Security</div>
            <div class="sig-line">Engenharia<br>AmazingDrone</div>
            <div class="sig-line">De Acordo<br>{cliente}</div>
        </div>
        <div class="footer"><p>Proposta válida por 10 dias úteis. Operações homologadas DECEA/ANAC.</p></div>
    </body>
    </html>
    """
    return html


# =============================================================================
# INTERFACE PRINCIPAL
# =============================================================================
def main():
    init_db()
    if 'carrinho' not in st.session_state: st.session_state['carrinho'] = []

    with st.sidebar:
        if os.path.exists(ARQUIVO_LOGO):
            img_b64 = get_image_base64(ARQUIVO_LOGO)
            if img_b64:
                st.markdown(
                    f"""
                    <div style="background-color: white; padding: 30px 10px; border-radius: 12px; text-align: center; margin-bottom: 25px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                        <img src="{img_b64}" style="max-width: 90%; height: auto;">
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.image(ARQUIVO_LOGO, use_container_width=True)
        else:
            st.warning("Logo não encontrada")

        st.divider()
        menu = st.radio("Navegação", ["Nova Proposta", "Relatórios Gerenciais"])

    if menu == "Nova Proposta":
        st.title("🚀 Gerador de Proposta Inteligente")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("1. Cliente")
            with st.container(border=True):
                cliente = st.text_input("Empresa / Cliente")
                c_tipo, c_prazo = st.columns(2)
                contrato = c_tipo.selectbox("Modelo", ["Comodato (Aluguel)", "Venda + Software (SaaS)"])
                duracao = c_prazo.selectbox("Prazo (Meses)", [12, 24, 36, 48, 60], index=2)

            st.subheader("2. Seleção de Serviços")
            with st.container(border=True):
                servico = st.selectbox("Serviço", ["Monitoramento", "Volumetria", "Inspeções", "Mapeamento"])

                if servico == "Monitoramento":
                    if "Comodato" in contrato:
                        tipo_preco = "Comodato"
                        if duracao == 12:
                            preco_base = 46000.00;
                            label_duracao = "1 Ano (Alto Risco + 30% Margem)"
                        elif duracao == 24:
                            preco_base = 34000.00;
                            label_duracao = "2 Anos"
                        elif duracao == 36:
                            preco_base = 30000.00;
                            label_duracao = "3 Anos (Padrão)"
                        elif duracao == 48:
                            preco_base = 28000.00;
                            label_duracao = "4 Anos"
                        else:
                            preco_base = 26000.00;
                            label_duracao = "5 Anos"
                    else:
                        tipo_preco = "SaaS (Venda)"
                        if duracao == 12:
                            preco_base = 26000.00;
                            label_duracao = "1 Ano"
                        elif duracao == 24:
                            preco_base = 24000.00;
                            label_duracao = "2 Anos"
                        elif duracao == 36:
                            preco_base = 22000.00;
                            label_duracao = "3 Anos (Padrão)"
                        elif duracao == 48:
                            preco_base = 20500.00;
                            label_duracao = "4 Anos"
                        else:
                            preco_base = 19000.00;
                            label_duracao = "5 Anos"

                    st.info(f"ℹ️ **Tabela {tipo_preco} - {label_duracao}:** R$ {preco_base:,.2f}")
                    rondas_extras = st.number_input("Rondas Extras (3 inclusas)", 0, 50, 0)
                    valor_calc = preco_base + (rondas_extras * 850.00)
                    qtd_tot = 3 + rondas_extras
                    st.write(f"Total Mensal: **R$ {valor_calc:,.2f}**")
                    if st.button("Adicionar Monitoramento"):
                        st.session_state['carrinho'].append(
                            {"nome": f"Monitoramento {tipo_preco} ({label_duracao})", "qtd": qtd_tot,
                             "unidade": "rondas", "valor_unit": valor_calc / qtd_tot, "valor_total": valor_calc})
                        st.rerun()

                elif servico == "Volumetria":
                    c1, c2 = st.columns(2)
                    qv = c1.number_input("Qtd Vols", 1, 100, 1)
                    qb = c2.number_input("Qtd Bat", 1, 50, 4)
                    val = qv * qb * 2000
                    st.write(f"Total: R$ {val:,.2f}")
                    if st.button("Adicionar Volumetria"): st.session_state['carrinho'].append(
                        {"nome": f"Volumetria ({qb} Bat)", "qtd": qv, "unidade": "vols", "valor_unit": val / qv,
                         "valor_total": val}); st.rerun()
                else:
                    c1, c2 = st.columns(2)
                    q = c1.number_input("Qtd", 1, 100, 1)
                    v = c2.number_input("Valor", 0.0, step=100.0)
                    if st.button(f"Adicionar {servico}"): st.session_state['carrinho'].append(
                        {"nome": servico, "qtd": q, "unidade": "unid", "valor_unit": v,
                         "valor_total": q * v}); st.rerun()

        with col2:
            st.subheader("3. Fechamento")
            if st.session_state['carrinho']:
                for i, item in enumerate(st.session_state['carrinho']):
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.write(f"**{item['nome']}**");
                    c2.write(f"R$ {item['valor_total']:,.2f}")
                    if c3.button("🗑️", key=f"del_{i}"): st.session_state['carrinho'].pop(i); st.rerun()

                total, _, _, _ = calcular_totais(st.session_state['carrinho'])
                roi = gerar_analise_roi(contrato, total, duracao)
                st.success(f"Total Mensal: R$ {total:,.2f}")

                c1, c2 = st.columns(2)
                if cliente:
                    pdf = gerar_proposta_pdf(cliente, contrato, duracao, st.session_state['carrinho'], total, roi)
                    c1.download_button("📄 PDF Proposta", pdf, "Proposta.pdf", "application/pdf")
                    html = gerar_proposta_html(cliente, contrato, duracao, st.session_state['carrinho'], total, roi)
                    c2.download_button("🌐 HTML Proposta", html, "Proposta.html", "text/html")

                if st.button("💾 Fechar Contrato", type="primary"):
                    _, fs, fa, emp = calcular_totais(st.session_state['carrinho'])
                    res = ", ".join([x['nome'] for x in st.session_state['carrinho']])
                    salvar_venda(cliente, contrato, duracao, res, total, fa, fs, emp)
                    st.success("Salvo!");
                    st.session_state['carrinho'] = [];
                    st.rerun()

    elif menu == "Relatórios Gerenciais":
        st.title("📊 Inteligência Contábil & Vendas")
        df = carregar_dados()

        if not df.empty:
            total_geral = df['valor_total'].sum()
            total_sky = df['fat_skyhawk'].sum()
            total_amz = df['fat_amazing'].sum()

            c1, c2, c3 = st.columns(3)
            c1.metric("Faturamento Total", f"R$ {total_geral:,.2f}")
            c2.metric("SkyHawk", f"R$ {total_sky:,.2f}")
            c3.metric("Amazing", f"R$ {total_amz:,.2f}")

            st.dataframe(df, use_container_width=True)
            pdf_completo = gerar_relatorio_geral_completo_pdf(df)
            st.download_button("📥 Baixar Relatório Geral Completo (PDF)", pdf_completo, "Relatorio_Geral_Completo.pdf",
                               "application/pdf", type="primary")
        else:
            st.info("Nenhuma venda registrada ainda.")


if __name__ == "__main__":
    main()
