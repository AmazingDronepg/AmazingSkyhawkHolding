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
st.set_page_config(page_title="SkyHawk & Amazing CRM v21", layout="wide", page_icon="🚁")

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


def calcular_cenarios_fiscais(faturamento_mensal, empresa_nome):
    faturamento_anual_est = faturamento_mensal * 12
    analise = {}

    aliq_simples = 0.06;
    faixa = "1 (Até 180k)"
    if faturamento_anual_est > 180000: aliq_simples = 0.112; faixa = "2 (180k - 360k)"
    if faturamento_anual_est > 360000: aliq_simples = 0.135; faixa = "3 (360k - 720k)"
    if faturamento_anual_est > 720000: aliq_simples = 0.16; faixa = "4 (720k - 1.8M)"

    analise['simples_valor'] = faturamento_mensal * aliq_simples
    analise['presumido_valor'] = faturamento_mensal * 0.1633
    analise['faturamento_anual'] = faturamento_anual_est
    analise['faixa'] = faixa

    dicas = []
    if "SkyHawk" in empresa_nome:
        dicas.append(">> ATENÇÃO (Segurança): O Monitoramento pode cair no Anexo IV (INSS Patronal à parte).")
    else:
        dicas.append(">> Fator R (Engenharia): Mantenha a folha > 28% do faturamento para garantir Anexo III.")

    if faturamento_anual_est > 3600000:
        dicas.append(">> ALERTA: Faturamento alto! Considere Lucro Presumido.")
    else:
        dicas.append(f">> Simples Nacional (Faixa {faixa}) parece eficiente.")

    analise['dicas'] = dicas
    return analise


def gerar_analise_roi(contrato_escolhido, total_mensal, duracao):
    analise = {}
    custo_equipamento = 160000.00

    if "Comodato" in contrato_escolhido:
        analise['titulo'] = f"Análise Financeira: COMODATO ({duracao} Meses)"

        explicacao_preco = ""
        if duracao <= 12:
            explicacao_preco = "<b>Precificação de Curto Prazo:</b> O valor mensal inclui amortização acelerada do ativo (R$ 160k) + margem de risco de 30%, garantindo a cobertura total do investimento em 1 ano."
        elif duracao >= 48:
            explicacao_preco = "<b>Vantagem de Longo Prazo:</b> Como o equipamento se paga nos primeiros anos, aplicamos descontos agressivos por fidelidade."

        analise['texto'] = f"""
        <p><b>1. Estratégia CAPEX Zero:</b> Economia imediata de <b>R$ {custo_equipamento:,.2f}</b> (custo do drone). O valor é diluído na mensalidade.</p>
        <p><b>2. Benefício Fiscal (OPEX):</b> O valor total da fatura abate no cálculo do IRPJ (Lucro Real).</p>
        <p>{explicacao_preco}</p>
        """
        analise[
            'pdf_text'] = f"Modelo Comodato ({duracao} meses): Isenção de investimento inicial (R$ {custo_equipamento:,.2f}). Mensalidade calibrada para cobertura do ativo e risco operacional."

    else:
        analise['titulo'] = f"Análise Financeira: AQUISIÇÃO + SAAS ({duracao} Meses)"
        analise['texto'] = f"""
        <p><b>1. Aquisição (CAPEX):</b> Investimento inicial de <b>R$ {custo_equipamento:,.2f}</b>. O drone torna-se patrimônio da empresa.</p>
        <p><b>2. Mensalidade (OPEX):</b> Cobre apenas Software e Inteligência (SaaS), resultando em menor custo fixo mensal.</p>
        """
        analise[
            'pdf_text'] = f"Modelo Aquisição: Compra do ativo (R$ {custo_equipamento:,.2f}) + Mensalidade de Serviço (SaaS). Foco em redução de custo mensal a longo prazo."

    return analise


# =============================================================================
# BANCO DE DADOS
# =============================================================================
def init_db():
    conn = sqlite3.connect("skyhawk_v21.db")
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
    conn = sqlite3.connect("skyhawk_v21.db")
    cursor = conn.cursor()
    data_hoje = datetime.datetime.now().strftime("%d/%m/%Y")
    cursor.execute("""
        INSERT INTO propostas (cliente, tipo_contrato, duracao_meses, resumo_servicos, valor_total, fat_amazing, fat_skyhawk, empresa_destino, data_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (cliente, contrato, duracao, servicos, total, fat_amz, fat_sky, empresa, data_hoje))
    conn.commit()
    conn.close()


def carregar_dados():
    conn = sqlite3.connect("skyhawk_v21.db")
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
# GERADORES DE DOCUMENTOS
# =============================================================================
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
            <h3 style="margin-top:0; color:#1b5e20">💰 Análise de Valor & Investimento</h3>
            {roi_data['texto']}
        </div>
        <h3 style="color:#004d40; border-bottom: 2px solid #eee; padding-bottom: 10px;">Detalhamento Financeiro</h3>
        <table>
            <tr><th>Descrição do Serviço</th><th style="text-align:right">Investimento Mensal</th></tr>
            {itens_html}
        </table>
        <div class="total">Total Mensal: R$ {total:,.2f}</div>
        <div class="signatures">
            <div class="sig-line">Diretoria Comercial<br>Amazing SkyHawk Holding</div>
            <div class="sig-line">De Acordo<br>{cliente}</div>
        </div>
        <div style="margin-top: 50px; text-align: center; color: #888; font-size: 12px;">
            <p>Proposta válida por 10 dias úteis. Operações homologadas DECEA/ANAC.</p>
        </div>
    </body>
    </html>
    """
    return html


def gerar_proposta_pdf(cliente, contrato, duracao, carrinho, total, roi_data):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(ARQUIVO_LOGO):
        pdf.image(ARQUIVO_LOGO, x=55, y=10, w=100)

    pdf.set_y(50)
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
    pdf.rect(10, pdf.get_y(), 190, 40, 'F')
    pdf.set_xy(15, pdf.get_y() + 5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 6, "Análise de ROI & Investimento:", 0, 1)
    pdf.set_font("Arial", '', 9)
    pdf.multi_cell(180, 5, roi_data['pdf_text'])

    pdf.ln(15)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(0, 77, 64)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(110, 10, "Serviço", 1, 0, 'L', True)
    pdf.cell(30, 10, "Qtd", 1, 0, 'C', True)
    pdf.cell(50, 10, "Total (R$)", 1, 1, 'R', True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 10)
    for item in carrinho:
        pdf.cell(110, 10, item['nome'][:55], 1)
        pdf.cell(30, 10, f"{item['qtd']} {item['unidade']}", 1, 0, 'C')
        pdf.cell(50, 10, f"{item['valor_total']:,.2f}", 1, 1, 'R')

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Total Mensal: R$ {total:,.2f}", 0, 1, 'R')

    pdf.set_y(-45)
    y_sig = pdf.get_y()
    pdf.set_font("Arial", '', 10)
    pdf.line(60, y_sig, 150, y_sig)
    pdf.text(85, y_sig + 5, "Amazing SkyHawk Holding")
    return pdf.output(dest='S').encode('latin-1')


def gerar_relatorio_interno_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(ARQUIVO_LOGO):
        pdf.image(ARQUIVO_LOGO, x=55, y=10, w=100)

    pdf.ln(50)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "RELATÓRIO DE GESTÃO E PERFORMANCE", 0, 1, 'C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 5, f"Data: {datetime.datetime.now().strftime('%d/%m/%Y')} | Ref: Consolidado de Vendas", 0, 1, 'C')
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 8)
    pdf.set_fill_color(230, 230, 230)
    # Ajuste de largura total: 190mm
    pdf.cell(10, 8, "ID", 1, 0, 'C', True)
    pdf.cell(50, 8, "Cliente", 1, 0, 'C', True)
    pdf.cell(25, 8, "Contrato", 1, 0, 'C', True)
    pdf.cell(30, 8, "Total Venda", 1, 0, 'C', True)
    pdf.cell(37.5, 8, "Fat. SkyHawk", 1, 0, 'C', True)
    pdf.cell(37.5, 8, "Fat. Amazing", 1, 1, 'C', True)

    pdf.set_font("Arial", '', 8)
    total_geral = 0;
    total_sky = 0;
    total_amz = 0
    for index, row in df.iterrows():
        total_geral += row['valor_total']
        total_sky += row['fat_skyhawk']
        total_amz += row['fat_amazing']
        pdf.cell(10, 8, str(row['id']), 1, 0, 'C')
        pdf.cell(50, 8, str(row['cliente'])[:25], 1, 0, 'C')
        pdf.cell(25, 8, str(row['tipo_contrato']).split(' ')[0], 1, 0, 'C')
        pdf.cell(30, 8, f"{row['valor_total']:,.2f}", 1, 0, 'C')
        pdf.cell(37.5, 8, f"{row['fat_skyhawk']:,.2f}", 1, 0, 'C')
        pdf.cell(37.5, 8, f"{row['fat_amazing']:,.2f}", 1, 1, 'C')
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "ANÁLISE TRIBUTÁRIA POR EMPRESA", 0, 1, 'L')
    pdf.ln(2)

    fiscais_sky = calcular_cenarios_fiscais(total_sky, "SkyHawk")
    pdf.set_fill_color(224, 242, 241)
    pdf.rect(10, pdf.get_y(), 190, 45, 'F')
    pdf.set_xy(15, pdf.get_y() + 5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 6, f"SKYHAWK SECURITY (Total: R$ {total_sky:,.2f})", 0, 1)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 5,
             f"Estimativa Anual: R$ {fiscais_sky['faturamento_anual']:,.2f} | Enquadramento: Simples Nacional Faixa {fiscais_sky['faixa']}",
             0, 1)
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(90, 6, f"Imposto Est. (Simples): R$ {fiscais_sky['simples_valor']:,.2f}/mês", 0, 0)
    pdf.cell(90, 6, f"Imposto Est. (Presumido): R$ {fiscais_sky['presumido_valor']:,.2f}/mês", 0, 1)
    pdf.set_font("Arial", 'I', 8)
    for dica in fiscais_sky['dicas']: pdf.multi_cell(180, 4, dica)
    pdf.ln(10)

    fiscais_amz = calcular_cenarios_fiscais(total_amz, "Amazing")
    pdf.set_fill_color(255, 243, 224)
    pdf.rect(10, pdf.get_y(), 190, 45, 'F')
    pdf.set_xy(15, pdf.get_y() + 5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 6, f"AMAZING DRONE SOLUTIONS (Total: R$ {total_amz:,.2f})", 0, 1)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 5,
             f"Estimativa Anual: R$ {fiscais_amz['faturamento_anual']:,.2f} | Enquadramento: Simples Nacional Faixa {fiscais_amz['faixa']}",
             0, 1)
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(90, 6, f"Imposto Est. (Simples): R$ {fiscais_amz['simples_valor']:,.2f}/mês", 0, 0)
    pdf.cell(90, 6, f"Imposto Est. (Presumido): R$ {fiscais_amz['presumido_valor']:,.2f}/mês", 0, 1)
    pdf.set_font("Arial", 'I', 8)
    for dica in fiscais_amz['dicas']: pdf.multi_cell(180, 4, dica)

    return pdf.output(dest='S').encode('latin-1')


# =============================================================================
# INTERFACE PRINCIPAL
# =============================================================================
def main():
    init_db()
    if 'carrinho' not in st.session_state: st.session_state['carrinho'] = []

    with st.sidebar:
        if os.path.exists(ARQUIVO_LOGO):
            st.image(ARQUIVO_LOGO, use_container_width=True)
        st.divider()
        menu = st.radio("Navegação", ["Nova Proposta", "Relatórios Gerenciais"])

    if menu == "Nova Proposta":
        st.title("🚁 Gerador de Proposta Inteligente")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("1. Cliente")
            with st.container(border=True):
                cliente = st.text_input("Empresa / Cliente")
                c_tipo, c_prazo = st.columns(2)
                contrato = c_tipo.selectbox("Modelo", ["Comodato (Aluguel)", "Venda + Software (SaaS)"])
                duracao = c_prazo.number_input("Prazo (Meses)", 1, 60, 36)

            st.subheader("2. Seleção de Serviços")
            with st.container(border=True):
                servico = st.selectbox("Serviço", ["Monitoramento", "Volumetria", "Inspeções", "Mapeamento"])

                if servico == "Monitoramento":

                    if "Comodato" in contrato:
                        tipo_preco = "Comodato"
                        if duracao <= 12:
                            # 30% DE LUCRO/RISCO SOBRE O CUSTO TOTAL (160k + 264k)
                            preco_base = 46000.00
                            label_duracao = "1 Ano (Alto Risco + 30% Margem)"
                        elif duracao <= 24:
                            preco_base = 34000.00
                            label_duracao = "2 Anos"
                        elif duracao <= 36:
                            preco_base = 30000.00
                            label_duracao = "3 Anos (Padrão)"
                        elif duracao <= 48:
                            preco_base = 28000.00
                            label_duracao = "4 Anos"
                        else:
                            preco_base = 26000.00
                            label_duracao = "5 Anos"
                    else:
                        tipo_preco = "SaaS (Venda)"
                        if duracao <= 12:
                            preco_base = 26000.00
                            label_duracao = "1 Ano"
                        elif duracao <= 24:
                            preco_base = 24000.00
                            label_duracao = "2 Anos"
                        elif duracao <= 36:
                            preco_base = 22000.00
                            label_duracao = "3 Anos (Padrão)"
                        elif duracao <= 48:
                            preco_base = 20500.00
                            label_duracao = "4 Anos"
                        else:
                            preco_base = 19000.00
                            label_duracao = "5 Anos"

                    st.info(f"ℹ️ **Tabela {tipo_preco} - {label_duracao}:** R$ {preco_base:,.2f}")
                    if tipo_preco == "Comodato" and duracao <= 12:
                        st.caption("⚠️ Preço reajustado para cobrir Ativo + Operação + 30% Margem em 12 meses.")

                    rondas_extras = st.number_input("Rondas Extras (3 inclusas)", 0, 50, 0)
                    valor_calc = preco_base + (rondas_extras * 850.00)
                    qtd_tot = 3 + rondas_extras

                    st.write(f"Total Mensal: **R$ {valor_calc:,.2f}**")
                    if st.button("Adicionar Monitoramento"):
                        st.session_state['carrinho'].append({
                            "nome": f"Monitoramento {tipo_preco} ({label_duracao})",
                            "qtd": qtd_tot,
                            "unidade": "rondas",
                            "valor_unit": valor_calc / qtd_tot,
                            "valor_total": valor_calc
                        })
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
                    c1.write(f"**{item['nome']}**")
                    c2.write(f"R$ {item['valor_total']:,.2f}")
                    if c3.button("X", key=i): st.session_state['carrinho'].pop(i); st.rerun()

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
                    st.success("Salvo!")
                    st.session_state['carrinho'] = []
                    st.rerun()

    elif menu == "Relatórios Gerenciais":
        st.title("📊 Inteligência Contábil & Vendas")
        df = carregar_dados()
        st.dataframe(df, use_container_width=True)
        if not df.empty:
            pdf = gerar_relatorio_interno_pdf(df)
            st.download_button("📥 Baixar Relatório Gerencial (PDF)", pdf, "Relatorio_Gestao.pdf", "application/pdf")


if __name__ == "__main__":
    main()