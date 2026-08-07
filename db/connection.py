import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn():
    """Abre uma conexão nova com o Postgres do Inventra."""
    return psycopg2.connect(DATABASE_URL)
