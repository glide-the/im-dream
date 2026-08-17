"""PostgreSQL repositories bind to a connection owned by PostgresUnitOfWork.

Concrete Dream repositories are intentionally introduced with their aggregate
migrations.  This package marker prevents infrastructure code from acquiring
its own connections and bypassing the explicit transaction boundary.
"""

