from clickhouse_connect import get_client

class ClickHouse:
    def __init__(self, host = 'localhost', username = 'default', password = '' ,database_name = 'default', port = 8123):
        self.host = host
        self.username = username
        self.password = password
        self.database_name = database_name
        self.port = port
        self.database_name = database_name
        self.client = None
        # self.table_sql_mapping = {
        #     'options': 'ingestion/queries/options/createTable.sql',
        #     'indices': 'ingestion/queries/spot/createTable.sql'
        # }
        self.db_connect()
        print(f"Connected to ClickHouse database: {database_name} at {host}:{port} as {username}")
    def db_connect(self):
        self.client = get_client(host = self.host, username=self.username, password=self.password, database=self.database_name, port=self.port)

    def get_client(self):
        return self.client