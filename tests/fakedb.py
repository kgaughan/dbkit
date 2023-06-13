"""
A fake DB-API 2 driver.
"""

# DB names used to trigger certain behaviours.
INVALID_DB = "invalid-db"
INVALID_CURSOR = "invalid-cursor"
HAPPY_OUT = "happy-out"

apilevel = "2.0"
threadsafety = 2
paramstyle = "qmark"


def connect(database):
    return Connection(database)


class Connection:
    """
    A fake connection.
    """

    def __init__(self, database):
        super().__init__()
        self.database = database
        self.session = []
        self.cursors = set()
        self.executed = 0
        if database == INVALID_DB:
            self.valid = False
            raise OperationalError()
        self.valid = True

    def close(self):
        if not self.valid:
            raise ProgrammingError("Cannot close a closed connection.")
        self.valid = False
        for cursor in self.cursors:
            cursor.close()
        self.session.append("close")
        if self.database == INVALID_DB:
            raise OperationalError()

    def commit(self):
        self.session.append("commit")

    def rollback(self):
        self.session.append("rollback")

    def cursor(self):
        self.session.append("cursor")
        if not self.valid:
            raise InterfaceError()
        return Cursor(self)


class Cursor:
    """
    A fake cursor.
    """

    def __init__(self, connection):
        self.connection = connection
        self.result = None
        if connection.database == INVALID_CURSOR:
            self.valid = False
            raise OperationalError("You've tripped INVALID_CURSOR!")
        connection.cursors.add(self)
        self.valid = True
        self.rowcount = -1

    def close(self):
        self.connection.session.append("cursor-close")
        if not self.valid:
            raise InterfaceError("Cursor is closed")
        self.connection.cursors.remove(self)
        self.valid = False

    def execute(self, stmt, args=()):
        if not self.valid or not self.connection.valid:
            raise InterfaceError()
        stmt = stmt.lstrip().lower()
        # It's the ping!
        if stmt == "select 1":
            return self
        (stmt_type,) = stmt.split(" ", 1)
        if stmt_type in ("select", "update", "insert", "delete"):
            self.result = None if args == () else args
            self.connection.session.append(stmt_type)
            self.connection.executed += 1
        else:
            self.result = None
            raise ProgrammingError()

    def callproc(self, procname, args=()):
        if not self.valid or not self.connection.valid:
            raise InterfaceError()
        self.result = None if len(args) == 0 else args
        self.connection.session.append("proc:" + procname)
        self.connection.executed += 1

    def fetchone(self):
        if not self.valid:
            raise InterfaceError("Cursor is closed")
        result = self.result
        self.result = None
        return result

    def fetchall(self):
        return ()


class Warning(Exception):
    pass


class Error(Exception):
    pass


class InterfaceError(Error):
    pass


class DatabaseError(Error):
    pass


class DataError(DatabaseError):
    pass


class OperationalError(DatabaseError):
    pass


class IntegrityError(DatabaseError):
    pass


class InternalError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


class NotSupportedError(DatabaseError):
    pass
