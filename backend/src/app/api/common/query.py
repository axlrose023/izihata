from sqlalchemy import SQLColumnExpression
from sqlalchemy.sql.elements import ColumnElement


def literal_contains(
    column: SQLColumnExpression[str | None], text: str
) -> ColumnElement[bool]:
    return column.icontains(text.strip(), autoescape=True)
