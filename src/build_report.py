"""Capa e quatro páginas de relatório, com código e artefatos incorporados."""

import hashlib
import json
import zipfile
from pathlib import Path
import matplotlib
from pypdf import PdfReader, PdfWriter
from pypdf.generic import TextStringObject
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle, Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
DEST = ROOT / "report"
M = 42
W, H = A4
CW = W - 2 * M
INK = "#202020"
TEAL = "#333333"
GRAY = "#666666"
PALE = "#f5f5f5"
AMBER = "#444444"
SAND = "#eaeaea"
CODE = [
    str(p.relative_to(ROOT))
    for folder in ("src", "tests")
    for p in sorted((ROOT / folder).glob("*.py"))
]


def n(value):
    return f"{value:,}".replace(",", ".")


def d(value, digits=4):
    return f"{value:.{digits}f}".replace(".", ",")


def text(x, y, value, size=10, bold=False, color=INK):
    C.setFillColor(colors.HexColor(color))
    C.setFont("Bold" if bold else "Body", size)
    C.drawString(x, y, str(value))


def para(x, top, width, value, size=9.5, color=INK, leading=None):
    style = ParagraphStyle(
        "p",
        fontName="Body",
        fontSize=size,
        leading=leading or size * 1.37,
        textColor=colors.HexColor(color),
    )
    p = Paragraph(value, style)
    _, height = p.wrap(width, H)
    p.drawOn(C, x, top - height)
    return top - height


def rect(x, top, width, height, fill=PALE):
    C.setFillColor(colors.HexColor(fill))
    C.rect(x, top - height, width, height, stroke=0, fill=1)


def arrow(x1, y, x2):
    C.setStrokeColor(colors.HexColor(TEAL))
    C.setLineWidth(1.2)
    C.line(x1, y, x2, y)
    C.line(x2 - 4, y + 3, x2, y)
    C.line(x2 - 4, y - 3, x2, y)


def section(y, number, title):
    text(M, y, number, 8, True, TEAL)
    text(M, y - 30, title, 23, True)


def page(number, label):
    C.setStrokeColor(colors.HexColor(TEAL))
    C.setLineWidth(0.8)
    C.line(M, H - 36, W - M, H - 36)
    text(M, H - 27, "BLOCKCHAIN-2S2026 | COLDCARD - ML", 8, False, GRAY)
    text(
        M,
        25,
        "Lucas Panonko Assis Belchior | 12311BCC068 | 22/10/2026",
        7.4,
        False,
        GRAY,
    )
    text(W - M - 27, 25, f"{number+1} / 5", 7.4, False, GRAY)
    section(H - 62, label[0], label[1])


def table(top, rows, widths, row_height=28, size=8.3):
    body = []
    for i, row in enumerate(rows):
        style = ParagraphStyle(
            "cell",
            fontName="Bold" if i == 0 else "Body",
            fontSize=size,
            leading=size * 1.3,
            textColor=colors.white if i == 0 else colors.HexColor(INK),
        )
        body.append([Paragraph(str(v), style) for v in row])
    t = Table(body, colWidths=widths, rowHeights=[row_height] * len(rows))
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(INK)),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.HexColor(PALE), colors.white],
                ),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#d1dddd")),
            ]
        )
    )
    _, height = t.wrap(CW, H)
    t.drawOn(C, M, top - height)
    return top - height


def image(path, x, top, width):
    im = Image(str(path))
    height = im.imageHeight / im.imageWidth * width
    im.drawWidth = width
    im.drawHeight = height
    im.drawOn(C, x, top - height)
    return top - height


def main():
    global C
    fonts = Path(matplotlib.get_data_path()) / "fonts/ttf"
    for name, file in [("Body", "DejaVuSans.ttf"), ("Bold", "DejaVuSans-Bold.ttf")]:
        pdfmetrics.registerFont(TTFont(name, str(fonts / file)))
    pdfmetrics.registerFontFamily(
        "Body", normal="Body", bold="Bold", italic="Body", boldItalic="Bold"
    )
    r = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    census = json.loads((OUT / "census.json").read_text(encoding="utf-8"))
    model = r["selected"]
    chosen = r["candidates"][model]["test"]
    DEST.mkdir(parents=True, exist_ok=True)
    tmp = ROOT / "tmp/pdfs"
    tmp.mkdir(parents=True, exist_ok=True)
    C = canvas.Canvas(str(tmp / "compact_body.pdf"), pagesize=A4)
    C.setTitle("ColdCard - ML: pipeline e resultados")
    C.setAuthor("Lucas Panonko Assis Belchior - 12311BCC068")

    # Capa simples, sem gráficos ou numeração.
    C.setFillColor(colors.HexColor(INK))
    C.setFont("Bold", 14)
    C.drawCentredString(W / 2, 720, "Blockchain-2S2026")
    C.setFont("Body", 12)
    C.drawCentredString(W / 2, 656, "Lucas Panonko Assis Belchior")
    C.setFont("Body", 10)
    C.drawCentredString(W / 2, 635, "Matrícula: 12311BCC068")
    C.setFont("Bold", 25)
    C.drawCentredString(W / 2, 448, "ColdCard - ML")
    C.setFont("Body", 12)
    C.drawCentredString(W / 2, 419, "Detecção de transações com aprendizado de máquina")
    C.setFont("Body", 10)
    C.drawCentredString(W / 2, 105, "22 de outubro de 2026")
    C.setFont("Body", 8)
    C.setFillColor(colors.HexColor(GRAY))
    C.drawCentredString(W / 2, 82, "github.com/LuksbellN/ColdCard-ML")
    C.linkURL(
        "https://github.com/LuksbellN/ColdCard-ML",
        (W / 2 - 115, 77, W / 2 + 115, 93),
        relative=0,
    )
    C.showPage()

    # 1. Visão geral: resultados primeiro, seguidos do fluxo do experimento.
    page(1, ("01 / VISÃO GERAL", "Visão geral do experimento"))
    para(
        M,
        733,
        CW,
        "<b>Objetivo:</b> reconhecer padrões de transações que enviam BTC ao "
        "coletor informado no exercício, comparando modelos de classificação.",
    )
    gap = 10
    kw = (CW - 2 * gap) / 3
    for i, (value, label) in enumerate(
        [
            ("493.473", "transações analisadas"),
            ("504", "transações positivas"),
            ("594,4773 BTC", "recebidos pelo coletor"),
        ]
    ):
        x = M + i * (kw + gap)
        rect(x, 680, kw, 77)
        text(x + 12, 649, value, 19, True, TEAL)
        para(x + 12, 633, kw - 20, label, 8.3)
    text(M, 577, "Pipeline do trabalho", 12, True, TEAL)
    stages = [
        ("01", "98 blocos", "Ler os JSONs"),
        ("02", "Transações", "Excluir coinbase"),
        ("03", "Rótulos", "Identificar envios"),
        ("04", "35 atributos", "Descrever padrões"),
        ("05", "Modelos", "Treinar e avaliar"),
    ]
    bw = (CW - 4 * 13) / 5
    for i, (step, label, detail) in enumerate(stages):
        x = M + i * (bw + 13)
        rect(x, 558, bw, 86)
        text(x + 9, 540, step, 8, True, TEAL)
        para(x + 9, 529, bw - 16, "<b>" + label + "</b>", 9)
        para(x + 9, 505, bw - 16, detail, 7.7)
        if i < 4:
            arrow(x + bw + 2, 515, x + bw + 11)
    text(M, 447, "Como os exemplos recebem um rótulo", 12, True, TEAL)
    half = (CW - 12) / 2
    for x, label, desc, fill in [
        (M, "POSITIVA (1)", "Alguma saída envia BTC ao coletor.", PALE),
        (M + half + 12, "REFERÊNCIA (0)", "Nenhuma saída envia ao coletor.", "#f1f3f4"),
    ]:
        rect(x, 431, half, 60, fill)
        text(x + 12, 410, label, 9, True)
        para(x + 12, 397, half - 24, desc, 8.7)
    para(M, 359, CW, "Coletor: <b>" + census["collector"] + "</b>", 8.2)
    para(
        M,
        339,
        CW,
        "A classe positiva representa só <b>0,1021%</b> da base. "
        "As demais transações são negativas de referência, sem comprovação de legitimidade. "
        "A associação com roubo segue a hipótese do enunciado.",
        9,
    )
    rect(M, 276, CW, 115)
    text(M + 14, 252, "Resultado do modelo escolhido por validação", 11, True, TEAL)
    text(M + 14, 224, "167 de 168 casos encontrados", 20, True)
    para(
        M + 14,
        207,
        CW - 28,
        "<b>Recall: 99,40%</b> | <b>Precisão: 21,66%</b> | "
        "<b>604 falsos alarmes</b><br/>O modelo recupera quase todos os positivos deste teste, "
        "mas seus alertas exigem revisão.",
        9,
    )
    para(
        M,
        139,
        CW,
        "<b>Recorte:</b> 98 blocos não contínuos, alturas 960179 a 960802, "
        "entre 30/07 e 03/08/2026 (UTC). Foram excluídas 98 coinbase; não houve duplicatas. "
        "Nas positivas, foram gastos 1.329 UTXOs de 504 endereços de entrada distintos. "
        "Endereços não equivalem a pessoas.",
        8.7,
    )
    para(
        M,
        80,
        CW,
        "Valor exato recebido: <b>594,47725695 BTC</b>. "
        "O recorte fornecido não representa toda a blockchain.",
        8.6,
        GRAY,
    )
    C.showPage()

    # 2. Explicação visual da preparação, separação e validação.
    page(2, ("02 / METODOLOGIA", "Preparação e treinamento"))
    text(
        M, 733, "O modelo observa a estrutura, sem receber o endereço coletor", 10, True
    )
    groups = [
        ("Quantidade e tamanho", "Entradas, saídas, bytes e vbytes."),
        ("Valores e taxas", "Somas, dispersão, concentração e sat/vB."),
        ("Estrutura técnica", "Versão, locktime, scripts, witness e RBF."),
    ]
    for i, (head, body) in enumerate(groups):
        x = M + i * (kw + gap)
        rect(x, 714, kw, 72)
        para(x + 10, 700, kw - 20, "<b>" + head + "</b>", 9)
        para(x + 10, 676, kw - 20, body, 8.2)
    para(
        M,
        628,
        CW,
        "<b>35 atributos:</b> aplicamos log1p a 16 medidas de tamanho, contagem e "
        "valor. Na logística, padronizamos os atributos com médias e desvios calculados só "
        "no treino. Hashes, horários, alturas, endereços e o estado futuro das saídas ficam fora do modelo.",
        9,
    )
    text(M, 560, "Separação por blocos inteiros", 12, True, TEAL)
    devw = CW * 0.75
    rect(M, 542, devw - 5, 76, PALE)
    rect(M + devw + 5, 542, CW - devw - 5, 76, SAND)
    text(M + 12, 520, "DESENVOLVIMENTO", 9, True, TEAL)
    text(M + 12, 498, "370.218 transações | 336 positivas", 11, True)
    text(M + 12, 480, "74 blocos para treinar e escolher configurações", 8.5)
    para(M + devw + 14, 528, CW - devw - 22, "<b>TESTE RESERVADO</b>", 8.1, AMBER)
    para(
        M + devw + 14,
        503,
        CW - devw - 22,
        "123.255 transações<br/>168 positivas<br/>24 blocos",
        8.4,
    )
    para(
        M,
        452,
        CW,
        "Nenhum bloco é compartilhado entre desenvolvimento e teste. "
        "A distribuição equilibra positivos e tamanho das partições; sementes 42 e 43 "
        "tornam a separação reproduzível.",
        8.8,
    )
    text(
        M,
        405,
        "Validação cruzada: treinar em duas partes, validar na terceira",
        11,
        True,
        TEAL,
    )
    left = M + 92
    cellw = (CW - 92) / 3
    for j, label in enumerate(
        ["Parte A: 159 positivas", "Parte B: 110 positivas", "Parte C: 67 positivas"]
    ):
        para(left + j * cellw, 386, cellw - 5, label, 7.9)
    for i in range(3):
        y = 360 - i * 31
        text(M, y - 18, f"Rodada {i+1}", 9)
        for j in range(3):
            x = left + j * cellw
            rect(x, y, cellw - 5, 25, SAND if i == j else PALE)
            text(
                x + 11,
                y - 17,
                "VALIDAR" if i == j else "TREINAR",
                8.5,
                True,
                AMBER if i == j else TEAL,
            )
    para(
        M,
        254,
        CW,
        "Cada parte aparece uma vez como validação. Comparamos a média de "
        "<b>Average Precision (AP)</b> nas três rodadas e escolhemos a configuração antes "
        "de olhar o resultado do teste.",
        9,
    )
    table(
        214,
        [
            ["Modelos comparados", "Como funcionam / configurações"],
            ["Dummy (referência)", "Usa apenas a frequência das classes."],
            [
                "Regressão logística",
                "Combina atributos em um escore. C = 0,1 ou 1,0; pesos de classe balanceados.",
            ],
            [
                "Random Forest",
                "Combina escores de 100 árvores de decisão. Profundidade 8 ou 16; mínimo de 5 amostras por folha; pesos balanceados.",
            ],
        ],
        [151, CW - 151],
        row_height=33,
        size=8.5,
    )
    para(
        M,
        68,
        CW,
        "Os modelos usam a base completa, sem amostragem ou dados sintéticos. "
        "Limiar fixo: escore ≥ 0,5 gera um alerta. O teste não foi usado para ajustar esse limiar.",
        8.5,
        GRAY,
    )
    C.showPage()

    # 3. Validação, métricas, matriz e curvas na mesma página.
    page(3, ("03 / RESULTADOS", "Resultados dos modelos"))
    names = {
        "Dummy": "Dummy",
        "Logistica C=0.1": "Logística C=0,1 *",
        "Logistica C=1.0": "Logística C=1,0",
        "Random Forest depth=8": "RF profundidade 8",
        "Random Forest depth=16": "RF profundidade 16",
    }
    rows = [
        [
            "Modelo",
            "AP<br/>valid.",
            "Precisão",
            "Recall",
            "F1",
            "AP<br/>teste",
            "ROC-AUC",
        ]
    ]
    for name, v in r["candidates"].items():
        t = v["test"]
        rows.append(
            [
                names[name],
                d(v["cv_ap_mean"]),
                d(t["precision"] * 100, 2) + "%",
                d(t["recall"] * 100, 2) + "%",
                d(t["f1"]),
                d(t["ap"]),
                d(t["roc_auc"]),
            ]
        )
    table(731, rows, [134] + [(CW - 134) / 6] * 6, row_height=29, size=7.8)
    para(
        M,
        547,
        CW,
        "<b>* Selecionado:</b> logística C=0,1, pela maior AP média de validação "
        "(0,4723 ± 0,3985 de desvio padrão). RF com profundidade 8 foi melhor neste teste, "
        "mas a escolha anterior foi mantida. A variação entre blocos é grande.",
        9,
    )
    text(M, 490, "Matriz de confusão do modelo selecionado", 11, True, TEAL)
    mx = M + 78
    my = 450
    mw = 100
    mh = 40
    text(mx + 10, 463, "Predito: ref.", 8)
    text(mx + mw + 9, 463, "Predito: caso", 8)
    for i, (label, vals) in enumerate(
        [
            ("Referência", [chosen["tn"], chosen["fp"]]),
            ("ColdCard", [chosen["fn"], chosen["tp"]]),
        ]
    ):
        text(M, my - i * mh - 24, label, 8.1)
        for j, value in enumerate(vals):
            x = mx + j * mw
            top = my - i * mh
            rect(x, top, mw - 4, mh - 4, PALE if i == j else SAND)
            text(x + 14, top - 25, n(value), 15, True, TEAL if i == j else AMBER)
    para(
        M + 300,
        451,
        CW - 300,
        "<b>167 acertos positivos</b><br/>604 falsos alarmes<br/>"
        "1 caso não detectado<br/><br/><b>771 alertas</b>, dos quais 21,66% são positivos.",
        9,
    )
    para(
        M,
        353,
        CW,
        "<b>Precisão:</b> quantos alertas são positivos. <b>Recall:</b> quantos "
        "positivos foram encontrados. <b>F1:</b> equilíbrio entre os dois. "
        "<b>AP:</b> resume precisão e recall ao variar o limiar (não é a área trapezoidal).",
        8.7,
    )
    bottom = image(OUT / "plots/curves.png", M, 303, CW)
    para(
        M,
        bottom - 5,
        CW,
        "Curvas no teste reservado. A linha horizontal na PR marca a prevalência "
        "(0,1363%). Mesmo sem detectar positivos, o Dummy atinge 99,8637% de acurácia: "
        "acurácia alta e ROC-AUC alta, isoladamente, escondem falsos alarmes.",
        8.3,
        GRAY,
    )
    C.showPage()

    # 4. Inferência, verificações adicionais e acesso ao código.
    page(4, ("04 / DISCUSSÃO", "Análise dos resultados"))
    text(M, 733, "Um caso real que o modelo não detectou", 11, True, TEAL)
    rect(M, 718, CW, 96, SAND)
    ew = (CW - 32) / 3
    for i, (head, value) in enumerate(
        [
            ("Transação", "200 entradas / 1 saída"),
            ("Escore calculado", "0,4549"),
            ("Decisão com limiar 0,5", "Não gera alerta"),
        ]
    ):
        x = M + 12 + i * ew
        para(x, 705, ew - 12, head, 8.1, AMBER)
        para(x, 682, ew - 15, "<b>" + value + "</b>", 11)
        if i < 2:
            arrow(x + ew - 19, 669, x + ew - 7)
    para(
        M + 12,
        645,
        CW - 24,
        "O rótulo real é positivo: 0,31149028 BTC ao coletor. "
        "A estrutura difere da mediana das positivas (1 entrada / 1 saída).",
        8.5,
    )
    para(
        M,
        610,
        CW,
        "Hash: 43520bd70cc83ebc27a6071f9e97f478b9b7ef7329bab7b69eebba1e60f6bc59",
        7.4,
        GRAY,
    )
    text(M, 580, "Verificações adicionais do modelo selecionado", 11, True, TEAL)
    a = r["source_audit"]["selected_metrics"]
    t = r["temporal"]["metrics"]
    table(
        562,
        [
            ["Avaliação", "Transações", "Positivas", "Precisão", "Recall", "AP"],
            [
                "Teste principal",
                n(chosen["n"]),
                str(chosen["positives"]),
                d(chosen["precision"] * 100, 2) + "%",
                d(chosen["recall"] * 100, 2) + "%",
                d(chosen["ap"]),
            ],
            [
                "Sem origens compartilhadas",
                n(a["n"]),
                str(a["positives"]),
                d(a["precision"] * 100, 2) + "%",
                d(a["recall"] * 100, 2) + "%",
                d(a["ap"]),
            ],
            [
                "Temporal exploratória",
                n(t["n"]),
                str(t["positives"]),
                d(t["precision"] * 100, 4) + "%",
                d(t["recall"] * 100, 2) + "%",
                d(t["ap"]),
            ],
        ],
        [151, 83, 62, 76, 68, CW - 440],
        row_height=29,
        size=7.9,
    )
    para(
        M,
        434,
        CW,
        "<b>Origens:</b> mantém apenas transações sem endereço de entrada visto no "
        "desenvolvimento, sem reajustar o modelo. Não identifica pessoas ou carteiras. "
        "<b>Temporal:</b> reajusta nos blocos anteriores à altura 960766 e avalia os últimos "
        "25% dos blocos; usa configuração já escolhida. Tem apenas 1 positivo, portanto é "
        "exploratória, não um novo teste intocado.",
        8.5,
    )
    text(M, 357, "Conclusão", 11, True, TEAL)
    para(
        M,
        340,
        CW,
        "Há padrões úteis neste recorte, mas <b>alta recuperação não garante "
        "alertas confiáveis</b>. As 168 positivas do teste vêm de um único bloco; 500 das "
        "504 positivas estão em quatro blocos próximos. A validação é instável e os dados "
        "dependem de um coletor conhecido. Não há evidência de generalização para novos "
        "ataques ou para toda a blockchain.",
        9,
    )
    C.save()

    included = [
        ROOT / f for f in CODE + ["README.md", "requirements.txt", "data/README.md"]
    ]
    included += [
        OUT / f
        for f in [
            "census.json",
            "results.json",
            "environment.json",
            "test_predictions.csv.gz",
            "positive_transactions.csv",
            "errors.csv",
            "selected_model.joblib",
            "plots/curves.png",
            "plots/confusion_importance.png",
            "plots/positive_blocks.png",
        ]
    ]
    manifest = {
        str(f.relative_to(ROOT))
        .replace("\\", "/"): hashlib.sha256(f.read_bytes())
        .hexdigest()
        for f in included
    }
    bundle = DEST / "ColdCard_ML_artefatos.zip"
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for f in included:
            z.write(f, str(f.relative_to(ROOT)))
        z.writestr("manifest_sha256.json", json.dumps(manifest, indent=2))
    writer = PdfWriter(clone_from=str(tmp / "compact_body.pdf"))
    embedded = writer.add_attachment(bundle.name, bundle.read_bytes())
    embedded.description = TextStringObject(
        "Código completo, dados de resultados e instruções de reprodução"
    )
    writer.add_metadata(
        {
            "/Title": "ColdCard - ML: pipeline e resultados",
            "/Author": "Lucas Panonko Assis Belchior - 12311BCC068",
        }
    )
    output = DEST / "ColdCard_ML_Lucas_Belchior.pdf"
    with output.open("wb") as f:
        writer.write(f)
    print(
        "PDF",
        output,
        "PAGES",
        len(PdfReader(output).pages),
        "BYTES",
        output.stat().st_size,
    )


if __name__ == "__main__":
    main()
