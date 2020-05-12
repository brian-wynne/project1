import pandas
from books_sql import SQLEngine


class SQLImport:

    def start_csv_import(self):
        engine = SQLEngine()

        engine.connect_to_db()

        csv = 'books.csv'
        reader = pandas.read_csv(csv)
        reader.to_sql(con=engine.cursor(), index_label='id', name='books', if_exists='replace')

        engine.disconnect_from_db()


SQLImport.start_csv_import(SQLImport)