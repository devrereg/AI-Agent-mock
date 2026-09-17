import boto3
import json


class SecretsManager:
    _cache: dict[str, dict] = {}

    @classmethod
    def load(cls, secret_name: str, region: str = "ap-northeast-2") -> dict:
        if secret_name in cls._cache:
            return cls._cache[secret_name]

        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_name)

        secret = json.loads(response["SecretString"])
        cls._cache[secret_name] = secret
        return secret