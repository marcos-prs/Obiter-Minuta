import json
from app.schemas.output import MinutaPackage


def package_result(minuta: MinutaPackage) -> dict:
    return minuta.model_dump(mode="json")


def package_result_json(minuta: MinutaPackage) -> str:
    return json.dumps(minuta.model_dump(mode="json"), indent=2, ensure_ascii=False)
