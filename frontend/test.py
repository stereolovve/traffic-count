import psycopg2
conn = psycopg2.connect(
    dbname="contadordb",
    user="postgres",
    password="Senh@011",
    host="localhost",
    port="5432"
)
print("Conectou!")