"""OPS-SAT channel catalogue as published in the OPSSAT-AD paper (Sci Data 2025)."""
CHANNELS = {
    "CADC0872": ("I_B_FB_MM_0", "magnetometer"),
    "CADC0873": ("I_B_FB_MM_1", "magnetometer"),
    "CADC0874": ("I_B_FB_MM_2", "magnetometer"),
    "CADC0884": ("I_PD1_THETA", "photodiode"),
    "CADC0886": ("I_PD2_THETA", "photodiode"),
    "CADC0888": ("I_PD3_THETA", "photodiode"),
    "CADC0890": ("I_PD4_THETA", "photodiode"),
    "CADC0892": ("I_PD5_THETA", "photodiode"),
    "CADC0894": ("I_PD6_THETA", "photodiode"),
}


def channel_name(ch: str) -> str | None:
    return CHANNELS.get(ch, (None, None))[0]


def channel_kind(ch: str) -> str | None:
    return CHANNELS.get(ch, (None, None))[1]
