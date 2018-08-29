import os
import configparser
import ipaddress

from joule.models import config
from joule.errors import ConfigurationError


def run(custom_values=None, verify=True) -> config.JouleConfig:
    """provide a dict INI configuration to override defaults
       if verify is True, perform checks on settings to make sure they are appropriate"""
    my_configs = configparser.ConfigParser()
    my_configs.read_dict(config.DEFAULT_CONFIG)
    if custom_values is not None:
        my_configs.read_dict(custom_values)

    # ModuleDirectory
    module_directory = my_configs['Main']['ModuleDirectory']
    if not os.path.isdir(module_directory) and verify:
        raise ConfigurationError(
            "ModuleDirectory [%s] does not exist" % module_directory)
    # StreamDirectory
    stream_directory = my_configs['Main']['StreamDirectory']
    if not os.path.isdir(stream_directory) and verify:
        raise ConfigurationError(
            "StreamDirectory [%s] does not exist" % stream_directory)
    # DatabaseDirectory
    database_directory = my_configs['Main']['DatabaseDirectory']
    if not os.path.isdir(database_directory) and verify:
        raise ConfigurationError(
            "DatabaseDirectory [%s] does not exist" % database_directory)
    # IPAddress
    ip_address = my_configs['Main']['IPAddress']
    try:
        ipaddress.ip_address(ip_address)
    except ValueError as e:
        raise ConfigurationError("IPAddress is invalid") from e
    # Port
    try:
        port = int(my_configs['Main']['Port'])
        if port < 0 or port > 65535:
            raise ValueError()
    except ValueError as e:
        raise ConfigurationError("Jouled:Port must be between 0 - 65535") from e
    # Database
    database_name = my_configs['Main']['Database']

    # DataStore:Database
    store_configs = my_configs['DataStore']

    # DataStore:InsertPeriod
    try:
        insert_period = int(store_configs['InsertPeriod'])
        if insert_period <= 0:
            raise ValueError()
    except ValueError:
        raise ConfigurationError("DataStore:InsertPeriod must be a postive number")

    # DataStore:CleanupPeriod
    try:
        cleanup_period = int(store_configs['CleanupPeriod'])
        if cleanup_period <= 0 or cleanup_period < insert_period:
            raise ValueError()
    except ValueError:
        raise ConfigurationError("DataStore:CleanupPeriod must be a postive number > InsertPeriod")

    data_store = config.DataStoreConfig(insert_period, cleanup_period,
                                        database_name=store_configs['Database'])
    return config.JouleConfig(module_directory=module_directory,
                              stream_directory=stream_directory,
                              database_directory=database_directory,
                              ip_address=ip_address,
                              port=port,
                              database_name=database_name,
                              data_store=data_store)
