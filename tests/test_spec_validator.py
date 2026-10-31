from training.tinker import spec

P = ("On 22 May 2024 the photodiode channel I_PD3_THETA showed an unexpected run of zero values. "
     "Operators commanded a reboot of the ADCS. The drop may have been caused by a sensor fault.")


def test_label_is_deterministic_and_disciplined():
    g = spec.label(P)
    assert g["channel_id"] == ["CADC0888"] and g["sensor_type"] == ["photodiode"]
    assert g["event_date"] == ["2024-05-22"]
    assert g["root_cause"] is None            # hedged cause ("may have been") is NOT a root cause
    assert g["operational_response"].startswith("Operators commanded")


def test_roundtrip_lines_to_record():
    g = spec.label(P)
    rec, errs = spec.parse_lines(spec.to_lines(g))
    assert not errs and all(spec.field_equal(f, rec[f], g[f]) for f in spec.FIELDS)
    j = spec.to_record_json(rec)
    assert j["root_cause"] is None and "root_cause" in j["unknown_fields"]


def test_parser_strips_think_and_flags_missing():
    rec, errs = spec.parse_lines("<think>hmm</think>\nchannel_id: CADC0872\nunits: ?")
    assert rec["channel_id"] == ["CADC0872"] and rec["units"] == [] and errs


def test_validator_catches_hallucinations():
    rec = spec.label(P)
    rec["channel_id"] = ["CADC0888", "CADC0872"]
    rec["event_date"] = ["2024-05-22", "2023-01-01"]
    rec["observation"] = "A sentence that is not in the passage."
    rec["root_cause"] = "It may have been radiation."
    v = spec.validate(rec, P)
    assert {"observation:not_verbatim", "root_cause:not_verbatim"} <= set(v["flags"])
    assert any("CADC0872" in f for f in v["flags"]) and any("2023-01-01" in f for f in v["flags"])
    assert v["record"]["channel_id"] == ["CADC0888"] and v["record"]["root_cause"] is None


def test_unparseable_output():
    rec, errs = spec.parse_lines("I cannot help with that")
    assert rec is None and errs
