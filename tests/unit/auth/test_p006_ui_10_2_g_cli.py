from pathlib import Path


def test_g_cli_exposes_verify_only_and_declares_no_side_effects():
    root = Path(__file__).resolve().parents[3]
    cli = root / "verification/auth/p006_ui_10_2_g_final_aws_persistence_authority_qualification.py"
    text = cli.read_text(encoding="utf-8")
    assert 'choices=("verify",)' in text
    for expected in (
        '"migrationWritePerformed": False',
        '"databaseWritePerformed": False',
        '"syntheticAuthorityCreated": False',
        '"privateSourceRowsPrinted": False',
        '"mailSent": False',
        '"publicUrlActivated": False',
        '"productionAuthenticationCutoverPerformed": False',
    ):
        assert expected in text
    assert "ADMIT" not in text
    assert "adapter-proof" not in text
