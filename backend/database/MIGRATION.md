# Database Upgrade Path

The current production-ready adapter is SQLite using Python's built-in `sqlite3`.
`config.yaml` already includes profiles for PostgreSQL, MySQL, and MongoDB, but
the active model functions still use SQLite SQL directly.

## Recommended Production Path

1. Keep local development on SQLite until deployment requirements are clear.
2. For PostgreSQL or MySQL, migrate model functions into repository classes using
   SQLAlchemy.
3. Move table definitions from raw SQL into SQLAlchemy ORM models.
4. Use the scaffold in `database/sqlalchemy_adapter.py` for engine/session setup.
5. Export current data from Reports as Excel/JSON.
6. Import or transform the exported data into the new database.
7. Set:

```text
DATABASE_ENGINE=postgresql
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/smart_invoice
```

or:

```text
DATABASE_ENGINE=mysql
DATABASE_URL=mysql+pymysql://user:password@host:3306/smart_invoice
```

## MongoDB Note

MongoDB is document-oriented. It should use a separate repository implementation
because invoice, items, payment, client, and product records would be modeled
differently than relational SQL tables.
