class ConfigurationError(Exception):
    """
    Error setting up an object due to incorrect configuration
    """
    pass


class SubscriptionError(Exception):
    """
    Error subscribing to a stream that is not available
    """
    pass


class ConnectionError(Exception):
    """
    Error connecting to a Joule server
    """
    pass


class DataError(Exception):
    """
    Error generated by backend storage (nilmdb or timescale)
    """
    pass


class DecimationError(DataError):
    """
    Requested data is not sufficiently decimated
    """
    pass


class ApiError(Exception):
    """
    Error generated by an API call
    """
    pass


class StreamNotFound(ApiError):
    """
    Requested stream does not exist
    """
    pass
