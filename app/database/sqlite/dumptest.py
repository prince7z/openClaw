from app.database.sqlite.database import get_db_connection
from rich.console import Console
from rich.table import Table


console = Console()

# extract all table from the sql database and dump in beautiful table 
async def main():
    conn = await get_db_connection()
    try:
        # Get all non-system tables
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ) as cursor:
            tables = [row[0] for row in await cursor.fetchall()]

        if not tables:
            console.print("[yellow]No tables found in the database.[/yellow]")
            return

        for table_name in tables:
            # Get table schema to retrieve column names
            async with conn.execute(f"PRAGMA table_info({table_name})") as cursor:
                columns_info = await cursor.fetchall()
                # columns_info rows format: (cid, name, type, notnull, dflt_value, pk)
                column_names = [col[1] for col in columns_info]

            # Fetch all rows from the table
            async with conn.execute(f"SELECT * FROM {table_name}") as cursor:
                rows = await cursor.fetchall()

            # Construct and print the table
            table = Table(title=f"Table: {table_name}", show_header=True, header_style="bold magenta")
            for col_name in column_names:
                table.add_column(col_name)

            for row in rows:
                table.add_row(*(str(val) if val is not None else "NULL" for val in row))

            console.print(table)
            console.print()

    except Exception as e:
        console.print_exception()       

    finally:
        await conn.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())