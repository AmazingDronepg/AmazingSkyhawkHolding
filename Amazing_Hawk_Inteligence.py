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
st.set_page_config(page_title="SkyHawk & Amazing CRM v29", layout="wide", page_icon="🚀")

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
        dicas.append(">> ATENÇÃO: O CNAE de Monitoramento pode exigir Anexo IV. Verifique a folha de pagamento.")
    else:
        dicas.append(">> FATOR R: Mantenha a folha > 28% do faturamento para garantir Anexo III.")

    analise['dicas'] = dicas
    return analise


def gerar_analise_roi(contrato_escolhido, total_mensal_escolhido, duracao):
    analise = {}
    custo_equipamento = 160000.00
    gap_mensal_economia = 8000.00
    meses_payback = custo_equipamento / gap_mensal_economia  # 20 Meses

    if "Venda" in contrato_escolhido:
        meses_lucro = duracao - meses_payback
        if meses_lucro > 0:
            lucro_projetado = meses_lucro * gap_mensal_economia
            titulo = f"💰 Decisão Lucrativa: Você economiza R$ {lucro_projetado:,.2f}"
            texto_html = f"""
            <p style='color:#1b5e20; font-size:16px;'><b>★ Excelente Escolha Estratégica!</b></p>
            <p>Ao adquirir o equipamento, você atinge o <b>Ponto de Equilíbrio no mês {int(meses_payback)}</b>.</p>
            <p>Nos {int(meses_lucro)} meses restantes, sua empresa gera uma <b>Economia Líquida de R$ {lucro_projetado:,.2f}</b> comparado ao aluguel.</p>
            """
            texto_pdf = (
                f"ANÁLISE DE LUCRO REAL: Esta modalidade é a mais rentável para o prazo de {duracao} meses. "
                f"O equipamento se paga no mês {int(meses_payback)}. A partir daí, sua empresa acumula uma economia direta de R$ {lucro_projetado:,.2f}."
            )
        else:
            titulo = "⚠️ Alerta de Viabilidade Financeira"
            texto_html = f"""
            <p style='color:#b71c1c;'><b>Atenção: O prazo de {duracao} meses é curto para amortizar a compra.</b></p>
            <p>O equipamento leva 20 meses para 'se pagar'. Para este prazo, o custo total da compra será maior que o aluguel.</p>
            <p><b>Recomendação:</b> Considere o modelo COMODATO.</p>
            """
            texto_pdf = (
                f"ANÁLISE CRÍTICA: Para o prazo de {duracao} meses, a aquisição não atinge o ponto de equilíbrio (20 meses). "
                "Financeiramente, o modelo de Comodato (Aluguel) é mais seguro."
            )
    else:
        if duracao >= 36:
            lucro_perdido = (duracao - meses_payback) * gap_mensal_economia
            titulo = f"ℹ️ Análise Comparativa: Comodato vs Compra"
            texto_html = f"""
            <p><b>Você escolheu Comodato (Sem investimento inicial).</b> Ótimo para fluxo de caixa.</p>
            <p style='color:#e65100;'><b>Nota:</b> Se optasse pela COMPRA neste prazo, teria uma economia total de <b>R$ {lucro_perdido:,.2f}</b>.</p>
            """
            texto_pdf = (
                f"ANÁLISE DE CENÁRIO: O modelo Comodato oferece segurança total e zero investimento inicial. "
                f"Porém, no modelo de Compra, o equipamento se pagaria no mês 20, gerando economia de R$ {lucro_perdido:,.2f}."
            )
        else:
            titulo = "✅ Comodato: A Melhor Escolha para este Prazo"
            texto_html = f"""
            <p style='color:#1b5e20;'><b>Recomendação Oficial: O Comodato é superior para {duracao} meses.</b></p>
            <p>Como o equipamento custa R$ 160k, comprá-lo para usar por apenas {duracao} meses geraria prejuízo.</p>
            """
            texto_pdf = (
                f"VEREDICTO: Para contratos de {duracao} meses, o Comodato é a única opção financeiramente viável, "
                "evitando a imobilização de R$ 160.000,00 sem tempo hábil para retorno."
            )

    analise['titulo'] = titulo
    analise['texto'] = texto_html
    analise['pdf_text'] = texto_pdf
    return analise


# =============================================================================
# BANCO DE DADOS
# =============================================================================
def init_db():
    conn = sqlite3.connect("skyhawk_v29.db")
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
    conn = sqlite3.connect("skyhawk_v29.db")
    cursor = conn.cursor()
    data_hoje = datetime.datetime.now().strftime("%d/%m/%Y")
    cursor.execute("""
        INSERT INTO propostas (cliente, tipo_contrato, duracao_meses, resumo_servicos, valor_total, fat_amazing, fat_skyhawk, empresa_destino, data_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (cliente, contrato, duracao, servicos, total, fat_amz, fat_sky, empresa, data_hoje))
    conn.commit()
    conn.close()


def carregar_dados():
    conn = sqlite3.connect("skyhawk_v29.db")
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
# GERADORES DE PDF E HTML (PROPOSTA)
# =============================================================================
def gerar_proposta_pdf(cliente, contrato, duracao, carrinho, total, roi_data):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(ARQUIVO_LOGO): pdf.image(ARQUIVO_LOGO, x=55, y=10, w=100)

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

    # ROI
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, pdf.get_y(), 190, 45, 'F')
    pdf.set_xy(15, pdf.get_y() + 5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 6, "Analise de Viabilidade & Recomendacao:", 0, 1)
    pdf.set_font("Arial", '', 9)
    pdf.multi_cell(180, 5, roi_data['pdf_text'])

    # Tabela
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

    # Assinaturas
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


def gerar_relatorio_geral_completo_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(ARQUIVO_LOGO): pdf.image(ARQUIVO_LOGO, x=55, y=10, w=100)

    pdf.ln(50)
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 10, "RELATÓRIO GERAL ESTRATÉGICO", 0, 1, 'C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 5, f"Data: {datetime.datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'C')
    pdf.ln(10)

    total_geral = df['valor_total'].sum()
    total_sky = df['fat_skyhawk'].sum()
    total_amz = df['fat_amazing'].sum()

    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, pdf.get_y(), 190, 30, 'F')
    y_start = pdf.get_y()

    pdf.set_xy(10, y_start + 5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(63, 10, "FATURAMENTO GLOBAL", 0, 0, 'C')
    pdf.cell(63, 10, "SKYHAWK", 0, 0, 'C')
    pdf.cell(63, 10, "AMAZING", 0, 1, 'C')

    pdf.set_font("Arial", 'B', 14);
    pdf.set_text_color(0, 77, 64)
    pdf.cell(63, 10, f"R$ {total_geral:,.2f}", 0, 0, 'C')
    pdf.set_text_color(0, 0, 0)
    pdf.cell(63, 10, f"R$ {total_sky:,.2f}", 0, 0, 'C')
    pdf.cell(63, 10, f"R$ {total_amz:,.2f}", 0, 1, 'C')

    pdf.ln(15)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Contratos Fechados", 0, 1, 'L')
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


# =============================================================================
# INTERFACE PRINCIPAL
# =============================================================================
def main():
    init_db()
    if 'carrinho' not in st.session_state: st.session_state['carrinho'] = []

    with st.sidebar:
        if os.path.exists(ARQUIVO_LOGO): st.image(ARQUIVO_LOGO, use_container_width=True)
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

                # --- BOTÕES DE DOWNLOAD SOLICITADOS ---
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
