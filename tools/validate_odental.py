#!/usr/bin/env python3
import ast
import csv
import sys
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "odental_core"


def fail(message):
    print(f"ERROR: {message}")
    return 1


def main():
    errors = 0
    required = [
        MODULE / "__manifest__.py",
        MODULE / "security" / "ir.model.access.csv",
        MODULE / "views" / "odental_menus.xml",
    ]
    for path in required:
        if not path.exists():
            errors += fail(f"Falta {path.relative_to(ROOT)}")

    for path in MODULE.rglob("*.py"):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors += fail(f"Python inválido en {path.relative_to(ROOT)}: {exc}")

    try:
        manifest = ast.literal_eval((MODULE / "__manifest__.py").read_text(encoding="utf-8"))
        if not manifest.get("installable"):
            errors += fail("El módulo no está marcado como instalable")
        for relative_path in manifest.get("data", []):
            if not (MODULE / relative_path).exists():
                errors += fail(f"El manifiesto referencia un archivo inexistente: {relative_path}")
    except (SyntaxError, ValueError) as exc:
        errors += fail(f"No se pudo interpretar el manifiesto: {exc}")

    for path in MODULE.rglob("*.xml"):
        try:
            ElementTree.parse(path)
        except ElementTree.ParseError as exc:
            errors += fail(f"XML inválido en {path.relative_to(ROOT)}: {exc}")

    acl_path = MODULE / "security" / "ir.model.access.csv"
    if acl_path.exists():
        with acl_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            errors += fail("La matriz de permisos está vacía")
        if any(not row.get("model_id:id") or not row.get("group_id:id") for row in rows):
            errors += fail("Hay permisos sin modelo o grupo")

    if errors:
        return 1
    print("O Dental: validación estática aprobada")
    print(f"Python: {len(list(MODULE.rglob('*.py')))} archivos")
    print(f"XML: {len(list(MODULE.rglob('*.xml')))} archivos")
    print(f"ACL: {len(rows)} reglas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
