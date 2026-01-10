import yaml


class LoadYamlfile:
    def __init__(self, file_path='settings.yaml'):
        with open(file_path, 'r') as f:
            self.config = yaml.safe_load(f)

    def get(self, key, subkey=None, default=None):
        value = self.config.get(key, default)

        if subkey is None:
            return value

        if isinstance(value, dict):
            return value.get(subkey, default)

        raise TypeError(f"Value for '{key}' is not a dict")