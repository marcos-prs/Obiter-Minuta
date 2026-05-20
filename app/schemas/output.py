from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class ParteField(BaseModel):
    valor: str
    confianca: float = Field(ge=0.0, le=1.0)
    origem_trecho: str | None = None


class Partes(BaseModel):
    requerente: ParteField | None = None
    requerido: ParteField | None = None


class Preliminar(BaseModel):
    titulo: str
    texto: str
    confianca: float = Field(ge=0.0, le=1.0)
    origem_trecho: str | None = None


class Fato(BaseModel):
    sequencia: int
    texto: str
    confianca: float = Field(ge=0.0, le=1.0)
    origem_trecho: str | None = None


class Tese(BaseModel):
    titulo: str
    fundamento_legal: list[str] = Field(default_factory=list)
    texto: str
    confianca: float = Field(ge=0.0, le=1.0)
    origem_trecho: str | None = None


class Pedido(BaseModel):
    tipo: Literal["principal", "subsidiario", "honorarios", "outro"]
    texto: str
    confianca: float = Field(ge=0.0, le=1.0)
    origem_trecho: str | None = None


class Prova(BaseModel):
    tipo: str
    descricao: str
    referencia_doc: str | None = None
    confianca: float = Field(ge=0.0, le=1.0)
    origem_trecho: str | None = None


class EstruturaPeca(BaseModel):
    partes: Partes = Field(default_factory=Partes)
    preliminares: list[Preliminar] = Field(default_factory=list)
    fatos: list[Fato] = Field(default_factory=list)
    teses: list[Tese] = Field(default_factory=list)
    pedidos: list[Pedido] = Field(default_factory=list)
    provas: list[Prova] = Field(default_factory=list)


class CampoIncerto(BaseModel):
    campo: str
    motivo: str
    confianca: float = Field(ge=0.0, le=1.0)


class QualidadeOutput(BaseModel):
    confianca_geral: float = Field(ge=0.0, le=1.0)
    campos_incertos: list[CampoIncerto] = Field(default_factory=list)
    lacunas: list[str] = Field(default_factory=list)
    requer_revisao: bool


class Metadados(BaseModel):
    tipo_detectado: str | None = None
    tipo_declarado: str
    tipo_confirmado: bool = True
    numero_processo: str | None = None
    vara: str | None = None
    paginas_originais: int = 0
    origem: str | None = None


class Auditoria(BaseModel):
    hash_arquivo_entrada: str
    modelo_ia: str
    versao_conversor: str
    pdf_descartado: bool = True


class MinutaPackage(BaseModel):
    job_id: str
    versao_schema: str = "1.0"
    processado_em: datetime
    metadados: Metadados
    markdown: str
    estrutura: EstruturaPeca
    qualidade: QualidadeOutput
    auditoria: Auditoria
