from typing import List

from typing_extensions import Self

from dell_ai.system_utils.base import ComparableBaseModel


class AmdDriverInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        self.software_version_compare(
            "rocm_smi_version",
            others,
            "ROCM SMI Version",
        )
        self.software_version_compare("driver_version", others, "Driver version")
        self.software_version_compare("amd_ctk_version", others, "CTK Version")

    rocm_smi_version: str | None = None
    driver_version: str | None = None
    amd_ctk_version: str | None = None
