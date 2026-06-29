from src.shared.exceptions import DomainError


class CampaignError(DomainError):
    code = "campaign_error"


class CampaignNotFoundError(CampaignError):
    code = "campaign_not_found"

    def __init__(
        self,
        *,
        campaign_id: int,
        message: str | None = None,
        cause: BaseException | None = None,
    ) -> None:
        self.campaign_id = campaign_id
        super().__init__(message or f"Campaign {campaign_id} not found", cause=cause)


class CampaignStreamNotFoundError(CampaignError):
    code = "campaign_stream_not_found"

    def __init__(
        self,
        *,
        stream_id: int,
        message: str | None = None,
        cause: BaseException | None = None,
    ) -> None:
        self.stream_id = stream_id
        super().__init__(
            message or f"Campaign stream {stream_id} not found",
            cause=cause,
        )


class CampaignOfferBatchError(CampaignError):
    code = "campaign_offer_batch_error"

    def __init__(self, message: str, cause: BaseException | None = None) -> None:
        super().__init__(message, cause=cause)


class KeitaroOperationError(CampaignError):
    code = "keitaro_operation_error"

    def __init__(
        self,
        *,
        operation: str,
        message: str,
        cause: BaseException | None = None,
    ) -> None:
        self.operation = operation
        super().__init__(message, cause=cause)


class DictionariesNotLoadedError(CampaignError):
    code = "dictionaries_not_loaded"

    def __init__(self, message: str = "Dictionaries are not loaded") -> None:
        super().__init__(message)
