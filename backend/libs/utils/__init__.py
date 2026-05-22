# [Input] None
# [Output] Re-export common utilities for libs.utils consumers.
# [Pos] package root in backend/libs/utils
# [Sync] 2026-05-23: initial package — extracted from infrastructure.persistence._base
from libs.utils.env import read_int_env

__all__ = ["read_int_env"]
