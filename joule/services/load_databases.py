from typing import Dict
import logging
import configparser
from joule.models import DatabaseConfig, ConfigurationError, config
from joule.services.helpers import load_configs

logger = logging.getLogger('joule')

Databases = Dict[str, DatabaseConfig]


def run(path: str) -> Databases:
    configs = load_configs(path)
    databases: Databases = {}
    for file_path, data in configs.items():
        try:
            data: configparser.ConfigParser = data["Main"]
        except KeyError:
            raise ConfigurationError("missing [Main] section")
        try:
            backend = _validate_backend(data["backend"])
            name = data["name"]
            # defaults
            (port, username, password, path, url) = (0, None, None, '', '')
            if (backend == config.BACKEND.TIMESCALE or
                    backend == config.BACKEND.POSTGRES or
                    backend == config.BACKEND.NILMDB):
                url = data["url"]
                if 'port' in data:
                    port = _validate_port(data["port"])
                elif backend == config.BACKEND.NILMDB:
                    port = 80
                else:
                    port = 1234  # TODO: what is the default port for postgres?
                if 'username' in data:
                    username = data['username']
                if 'password' in data:
                    password = data['password']
            if backend == config.BACKEND.SQLITE:
                path = data["path"]
            databases[name] = DatabaseConfig(backend, path, url, port, username, password)
        except KeyError as e:
            logger.error("Invalid database [%s]: [Main] missing %s" %
                         (file_path, e.args[0]))
        except ConfigurationError as e:
            logger.error("Invalid database [%s]: %s" % (file_path, e))
    return databases


def _validate_backend(backend: str) -> config.BACKEND:
    try:
        return config.BACKEND[backend.upper()]
    except KeyError as e:
        valid_types = ", ".join([m.name.lower() for m in config.BACKEND])
        raise ConfigurationError("invalid backend [%s], choose from [%s]" %
                                 (backend, valid_types)) from e


def _validate_port(port: str) -> int:
    # Port
    try:
        port = int(port)
        if port < 0 or port > 65535:
            raise ValueError()
        return port
    except ValueError as e:
        raise ConfigurationError("Port must be between 0 - 65535") from e