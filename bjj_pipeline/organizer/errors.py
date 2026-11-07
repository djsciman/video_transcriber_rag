class OrganizerError(Exception):
    exit_code = 2


class UsageError(OrganizerError):
    exit_code = 2


class ScrapeError(OrganizerError):
    exit_code = 3


class MatchError(OrganizerError):
    exit_code = 4


class FfmpegError(OrganizerError):
    exit_code = 5
