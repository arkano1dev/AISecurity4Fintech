from shared.guardrail import REFUSAL, check_output


def test_clean_output_passes() -> None:
    verdict = check_output("The wire transfer threshold is ten thousand euro.")
    assert verdict.blocked is False
    assert verdict.reason is None


def test_jailbreak_canary_is_blocked() -> None:
    verdict = check_output("I have been PWNED")
    assert verdict.blocked is True
    assert verdict.reason == "i have been pwned"


def test_system_prompt_leak_is_blocked() -> None:
    verdict = check_output("Your system prompt is: you are a compliance analyst.")
    assert verdict.blocked is True
    assert verdict.reason == "you are a compliance analyst"


def test_check_is_case_insensitive() -> None:
    verdict = check_output("DAN MODE activated")
    assert verdict.blocked is True


def test_refusal_is_a_clean_sentence() -> None:
    assert REFUSAL == "I can't answer that request."
