"""
General ledger reporting. Trial balance is computed with a real SQL aggregate
query (not just ORM object crunching in Python) since that's the actual shape
of the report: one row per account, summed straight from the journal lines.
"""
from decimal import Decimal

from django.db import connection

ZERO = Decimal('0')

TRIAL_BALANCE_SQL = """
    SELECT
        a.id AS account_id,
        a.code,
        a.name,
        a.account_type,
        a.subtype,
        COALESCE(SUM(CASE WHEN l.direction = 'DEBIT' THEN l.functional_amount ELSE 0 END), 0) AS total_debit,
        COALESCE(SUM(CASE WHEN l.direction = 'CREDIT' THEN l.functional_amount ELSE 0 END), 0) AS total_credit
    FROM ledger_account a
    JOIN ledger_journalline l ON l.account_id = a.id
    JOIN ledger_journalentry e ON l.journal_entry_id = e.id
    WHERE e.project_id = %s
    GROUP BY a.id, a.code, a.name, a.account_type, a.subtype
    ORDER BY a.code
"""

DEBIT_NORMAL_TYPES = ('ASSET', 'EXPENSE')


def trial_balance(project):
    """
    One row per account with activity, split into debit/credit columns the way
    a real trial balance is presented: an account's ending balance lands in
    whichever column matches its normal side, so a healthy ledger's two column
    totals are always equal.
    """
    with connection.cursor() as cursor:
        cursor.execute(TRIAL_BALANCE_SQL, [project.pk])
        columns = [col[0] for col in cursor.description]
        raw_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    rows = []
    total_debit_column = ZERO
    total_credit_column = ZERO

    for r in raw_rows:
        # Postgres (via psycopg2) returns NUMERIC aggregates as Decimal already;
        # SQLite returns plain floats for computed expressions. str() first avoids
        # constructing a Decimal from a float's binary representation either way.
        total_debit = Decimal(str(r['total_debit']))
        total_credit = Decimal(str(r['total_credit']))
        is_debit_normal = r['account_type'] in DEBIT_NORMAL_TYPES
        ending_balance = (total_debit - total_credit) if is_debit_normal else (total_credit - total_debit)

        debit_column = ending_balance if is_debit_normal else ZERO
        credit_column = ending_balance if not is_debit_normal else ZERO
        # An account can run against its normal side (e.g. a refund overshoots
        # revenue into a debit balance) -- keep the balance on its natural
        # column as a negative rather than silently flipping columns.
        total_debit_column += debit_column
        total_credit_column += credit_column

        rows.append({
            'code': r['code'],
            'name': r['name'],
            'account_type': r['account_type'],
            'subtype': r['subtype'],
            'debit': debit_column,
            'credit': credit_column,
        })

    return {
        'rows': rows,
        'total_debit': total_debit_column,
        'total_credit': total_credit_column,
        'is_balanced': total_debit_column == total_credit_column,
    }
