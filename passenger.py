class Passenger:
    """One passenger's request and the times recorded during their journey."""

    def __init__(self, id: str, request_time: int, source: int, destination: int):
        self.id = id
        self.request_time = request_time
        self.source = source
        self.destination = destination

        # None means this event has not happened yet. Time 0 is a valid time.
        self.assigned_elevator: int | None = None
        self.pickup_time: int | None = None
        self.drop_off_time: int | None = None

    @property
    def direction(self) -> str:
        """'up' or 'down': the way this passenger wants to travel."""
        return 'up' if self.destination > self.source else 'down'

    @property
    def wait_time(self) -> int | None:
        """Time from requesting the elevator to boarding it."""
        if self.pickup_time is None:
            return None
        return self.pickup_time - self.request_time

    @property
    def travel_time(self) -> int | None:
        """Time spent inside the elevator, available after drop-off."""
        if self.pickup_time is None or self.drop_off_time is None:
            return None
        return self.drop_off_time - self.pickup_time

    @property
    def total_time(self) -> int | None:
        """Time from the request to arrival at the destination."""
        if self.drop_off_time is None:
            return None
        return self.drop_off_time - self.request_time
