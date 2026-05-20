import json
from anthropic import Anthropic
from app.config import get_settings

SYSTEM_PROMPT = """Voce e um assistente juridico especializado em analisar pecas processuais brasileiras.
Sua tarefa e extrair informacoes estruturadas de documentos juridicos.

Regras:
1. Nao invente campos sem base documental. Se nao encontrar, deixe vazio ou marque confianca baixa.
2. Sempre indique a origem do trecho (pagina, paragrafo) quando possivel.
3. A confianca deve ser entre 0.0 e 1.0.
4. Identifique corretamente o tipo da peca (inicial, contestacao, tutela, replica, recurso).
5. Campos com confianca < 0.7 devem ser marcados como incertos.

Retorne APENAS JSON valido, sem markdown ou texto adicional."""


def analyze_semantic(
    markdown: str,
    tipo_declarado: str,
    numero_processo: str | None = None,
    vara: str | None = None,
    origem: str | None = None,
) -> dict:
    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)

    context_parts = [f"Tipo declarado: {tipo_declarado}"]
    if numero_processo:
        context_parts.append(f"Numero do processo: {numero_processo}")
    if vara:
        context_parts.append(f"Vara: {vara}")
    context = "\n".join(context_parts)

    prompt = f"""Analise a seguinte peca juridica e retorne um JSON estruturado.

Contexto:
{context}

Documento:
{markdown[:80000]}

Retorne o JSON seguindo exatamente este schema:
{{
  "tipo_detectado": "string",
  "tipo_confirmado": boolean,
  "partes": {{
    "requerente": {{"valor": "string", "confianca": number, "origem_trecho": "string"}},
    "requerido": {{"valor": "string", "confianca": number, "origem_trecho": "string"}}
  }},
  "preliminares": [{{"titulo": "string", "texto": "string", "confianca": number, "origem_trecho": "string"}}],
  "fatos": [{{"sequencia": number, "texto": "string", "confianca": number, "origem_trecho": "string"}}],
  "teses": [{{"titulo": "string", "fundamento_legal": ["string"], "texto": "string", "confianca": number, "origem_trecho": "string"}}],
  "pedidos": [{{"tipo": "principal|subsidiario|honorarios|outro", "texto": "string", "confianca": number, "origem_trecho": "string"}}],
  "provas": [{{"tipo": "string", "descricao": "string", "referencia_doc": "string", "confianca": number, "origem_trecho": "string"}}],
  "lacunas": ["string"]
}}"""

    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    content = message.content[0].text
    return _parse_json_response(content)


def _parse_json_response(content: str) -> dict:
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        if content.startswith("json"):
            content = content[4:].strip()
    return json.loads(content)
