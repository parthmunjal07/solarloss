class ArtifactNotFound(Exception):
    """No current review artifact exists for the requested experiment."""


class StorageUnavailable(Exception):
    """The artifact store could not complete an operation."""


class InvalidArtifact(Exception):
    """A stored review artifact is malformed or inconsistent."""


class InvalidExperimentId(Exception):
    """An experiment id cannot be used as an artifact key."""
