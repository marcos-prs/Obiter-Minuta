from datetime import datetime, timezone
from app.schemas.output import (
    MinutaPackage,
    EstruturaPeca,
    Partes,
    ParteField,
    Preliminar,
    Fato,
    Tese,
    Pedido,
    Prova,
    CampoIncerto,
    QualidadeOutput,
    Metadados,
    Auditoria,
)
from app.services.converter import CONVERTER_VERSION


UNCERTAINTY_THRESHOLD = 0.7


def validate_and_enrich(
    semantic_result: dict,
    job_id: str,
    markdown: str,
    page_count: int,
    tipo_declarado: str,
    numero_processo: str | None,
    vara: str | None,
    origem: str | None,
    file_hash: str,
    modelo_ia: str,
) -> MinutaPackage:
    partes = _build_partes(semantic_result.get("partes", {}))
    preliminares = _build_preliminares(semantic_result.get("preliminares", []))
    fatos = _build_fatos(semantic_result.get("fatos", []))
    teses = _build_teses(semantic_result.get("teses", []))
    pedidos = _build_pedidos(semantic_result.get("pedidos", []))
    provas = _build_provas(semantic_result.get("provas", []))

    estrutura = EstruturaPeca(
        partes=partes,
        preliminares=preliminares,
        fatos=fatos,
        teses=teses,
        pedidos=pedidos,
        provas=provas,
    )

    campos_incertos = _find_uncertain_fields(estrutura)
    lacunas = semantic_result.get("lacunas", [])
    confianca_geral = _calc_overall_confidence(estrutura)
    requer_revisao = len(campos_incertos) > 0 or confianca_geral < 0.7

    tipo_detectado = semantic_result.get("tipo_detectado", tipo_declarado)
    tipo_confirmado = tipo_detectado == tipo_declarado

    metadados = Metadados(
        tipo_detectado=tipo_detectado,
        tipo_declarado=tipo_declarado,
        tipo_confirmado=tipo_confirmado,
        numero_processo=numero_processo,
        vara=vara,
        paginas_originais=page_count,
        origem=origem,
    )

    auditoria = Auditoria(
        hash_arquivo_entrada=file_hash,
        modelo_ia=modelo_ia,
        versao_conversor=CONVERTER_VERSION,
        pdf_descartado=True,
    )

    qualidade = QualidadeOutput(
        confianca_geral=confianca_geral,
        campos_incertos=campos_incertos,
        lacunas=lacunas,
        requer_revisao=requer_revisao,
    )

    return MinutaPackage(
        job_id=job_id,
        processado_em=datetime.now(timezone.utc),
        metadados=metadados,
        markdown=markdown,
        estrutura=estrutura,
        qualidade=qualidade,
        auditoria=auditoria,
    )


def _build_partes(data: dict) -> Partes:
    req = data.get("requerente")
    req_field = ParteField(**req) if req else None
    rdo = data.get("requerido")
    rdo_field = ParteField(**rdo) if rdo else None
    return Partes(requerente=req_field, requerido=rdo_field)


def _build_preliminares(items: list[dict]) -> list[Preliminar]:
    return [Preliminar(**i) for i in items if i.get("titulo")]


def _build_fatos(items: list[dict]) -> list[Fato]:
    return [Fato(**i) for i in items if i.get("texto")]


def _build_teses(items: list[dict]) -> list[Tese]:
    return [Tese(**i) for i in items if i.get("titulo")]


def _build_pedidos(items: list[dict]) -> list[Pedido]:
    return [Pedido(**i) for i in items if i.get("texto")]


def _build_provas(items: list[dict]) -> list[Prova]:
    return [Prova(**i) for i in items if i.get("descricao")]


def _find_uncertain_fields(estrutura: EstruturaPeca) -> list[CampoIncerto]:
    incertos = []

    if estrutura.partes.requerente and estrutura.partes.requerente.confianca < UNCERTAINTY_THRESHOLD:
        incertos.append(
            CampoIncerto(
                campo="partes.requerente.valor",
                motivo="Confianca abaixo do limite de incerteza",
                confianca=estrutura.partes.requerente.confianca,
            )
        )
    if estrutura.partes.requerido and estrutura.partes.requerido.confianca < UNCERTAINTY_THRESHOLD:
        incertos.append(
            CampoIncerto(
                campo="partes.requerido.valor",
                motivo="Confianca abaixo do limite de incerteza",
                confianca=estrutura.partes.requerido.confianca,
            )
        )
    for i, prel in enumerate(estrutura.preliminares):
        if prel.confianca < UNCERTAINTY_THRESHOLD:
            incertos.append(
                CampoIncerto(
                    campo=f"preliminares[{i}].texto",
                    motivo="Confianca abaixo do limite de incerteza",
                    confianca=prel.confianca,
                )
            )
    for i, fato in enumerate(estrutura.fatos):
        if fato.confianca < UNCERTAINTY_THRESHOLD:
            incertos.append(
                CampoIncerto(
                    campo=f"fatos[{i}].texto",
                    motivo="Confianca abaixo do limite de incerteza",
                    confianca=fato.confianca,
                )
            )
    for i, tese in enumerate(estrutura.teses):
        if tese.confianca < UNCERTAINTY_THRESHOLD:
            incertos.append(
                CampoIncerto(
                    campo=f"teses[{i}].texto",
                    motivo="Confianca abaixo do limite de incerteza",
                    confianca=tese.confianca,
                )
            )
    for i, pedido in enumerate(estrutura.pedidos):
        if pedido.confianca < UNCERTAINTY_THRESHOLD:
            incertos.append(
                CampoIncerto(
                    campo=f"pedidos[{i}].texto",
                    motivo="Confianca abaixo do limite de incerteza",
                    confianca=pedido.confianca,
                )
            )
    for i, prova in enumerate(estrutura.provas):
        if prova.confianca < UNCERTAINTY_THRESHOLD:
            incertos.append(
                CampoIncerto(
                    campo=f"provas[{i}].descricao",
                    motivo="Confianca abaixo do limite de incerteza",
                    confianca=prova.confianca,
                )
            )
    return incertos


def _calc_overall_confidence(estrutura: EstruturaPeca) -> float:
    confidences = []
    if estrutura.partes.requerente:
        confidences.append(estrutura.partes.requerente.confianca)
    if estrutura.partes.requerido:
        confidences.append(estrutura.partes.requerido.confianca)
    for p in estrutura.preliminares:
        confidences.append(p.confianca)
    for f in estrutura.fatos:
        confidences.append(f.confianca)
    for t in estrutura.teses:
        confidences.append(t.confianca)
    for p in estrutura.pedidos:
        confidences.append(p.confianca)
    for p in estrutura.provas:
        confidences.append(p.confianca)
    if not confidences:
        return 0.0
    weights = [1.0] * len(confidences)
    for i in range(min(2, len(confidences))):
        weights[i] = 1.5
    total_weight = sum(weights)
    return sum(c * w for c, w in zip(confidences, weights)) / total_weight
