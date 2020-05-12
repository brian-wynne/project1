import sqlalchemy


class SQLEngine:
    _conn = None
    _cursor = None

    def connect_to_db(self):
        try:
            self._conn = sqlalchemy.create_engine('postgresql://books:book@localhost:5432/project1')
            self._conn.connect()
        except sqlalchemy.exc.OperationalError:
            print('[SQL] Error connection to database')
            return
        finally:
            print('[SQL] Connection established')

    def disconnect_from_db(self):
        if not self.is_connected():
            return

        try:
            ex = self._conn.connect()
            ex.close()
        except sqlalchemy.exc.OperationalError:
            print('[SQL] Error when closing connection to database')
            return
        finally:
            print('[SQL] Connection dropped')

    def query(self, exec):
        if not self.is_connected():
            return

        try:
            q = self._conn.connect()
            self._cursor = q.execute(exec)
        except sqlalchemy.exc.ProgrammingError:
            print('[SQL] :ProgrammingError: Error running query:\n' + exec)
            return []

        return self._cursor


    def is_connected(self):
        if self._conn is not None:
            return True

        return False

    def cursor(self):
        if not self.is_connected():
            return None

        return self._conn
