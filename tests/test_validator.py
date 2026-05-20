import pytest
from app.services.validator import validate_and_enrich, _find_uncertain_fields, _calc_overall_confidence
from app.schemas.output import EstruturaPeca, Partes, ParteField, Fato, Tese, Pedido


def test_validate_and_enrich_basic():
    semantic_result = {
        "tipo_detectado": "contestacao",
        "tipo_confirmado": True,
        "partes": {
            "requerente": {"valor": "Joao", "confianca": 0.9, "origem_trecho": "p.1"},
            "requerido": {"valor": "Maria", "confianca": 0.85, "origem_trecho": "p.1"},
        },
        "preliminares": [],
        "fatos": [],
        "teses": [],
        "pedidos": [],
        "provas": [],
        "lacunas": [],
    }

    minuta = validate_and_enrich(
        semantic_result=semantic_result,
        job_id="j_test123",
        markdown="# Test",
        page_count=5,
        tipo_declarado="contestacao",
        numero_processo="00123",
        vara=None,
        origem="test",
        file_hash="sha256:abc",
        modelo_ia="claude-test",
    )

    assert minuta.job_id == "j_test123"
    assert minuta.metadados.tipo_detectado == "contestacao"
    assert minuta.metadados.tipo_confirmado is True
    assert minuta.auditoria.pdf_descartado is True


def test_find_uncertain_fields():
    estrutura = EstruturaPeca(
        fatos=[
            Fato(sequencia=1, texto="fato certo", confianca=0.95, origem_trecho="p.1"),
            Fato(sequencia=2, texto="fato duvidoso", confianca=0.5, origem_trecho="p.2"),
        ],
        teses=[
            Tese(
                titulo="tese fraca",
                texto="argumento baixo",
                confianca=0.3,
                origem_trecho="p.3",
            ),
        ],
    )

    incertos = _find_uncertain_fields(estrutura)
    assert len(incertos) == 2
    assert incertos[0].campo == "fatos[1].texto"
    assert incertos[1].campo == "teses[0].texto"


def test_calc_overall_confidence():
    estrutura = EstruturaPeca(
        partes=Partes(
            requerente=ParteField(valor="A", confianca=0.9),
            requerido=ParteField(valor="B", confianca=0.8),
        ),
        fatos=[Fato(sequencia=1, texto="fato", confianca=0.7, origem_trecho="p.1")],
    )

    conf = _calc_overall_confidence(estrutura)
    assert 0.0 <= conf <= 1.0


def test_calc_overall_confidence_empty():
    estrutura = EstruturaPeca()
    conf = _calc_overall_confidence(estrutura)
    assert conf == 0.0
