import yaml
import clickhouse_connect

class ClickhouseConnector:
    """
    Initializes the Clickhouse parameters and provides a way to access them.
    """
    def __init__(self, clickhouse_params):
        """
        Initializes the Clickhouse parameters and creates a clickhouse client.
        """
        self.clickhouse_params = clickhouse_params
        self.clickhouse_host = self.clickhouse_params['host']
        self.clickhouse_port = self.clickhouse_params['port']
        self.clickhouse_username = self.clickhouse_params['username']
        self.clickhouse_password = self.clickhouse_params['password']
        self.clickhouse_database_name = self.clickhouse_params['database_name']
        self.clickhouse_options_table_name = self.clickhouse_params['option_table']
        self.clickhouse_indices_table_name = self.clickhouse_params['spot_table']

    def get_clickhouse_client(self):
        return clickhouse_connect.get_client(host=self.clickhouse_host, port=self.clickhouse_port, username=self.clickhouse_username,
         password=self.clickhouse_password, database=self.clickhouse_database_name)