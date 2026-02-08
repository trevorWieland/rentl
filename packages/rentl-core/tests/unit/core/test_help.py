"""Unit tests for command help module."""

from __future__ import annotations

import pytest

from rentl_core.help import CommandInfo, get_command_help, list_commands


class TestCommandInfo:
    """Tests for CommandInfo model."""

    def test_command_info_creation(self) -> None:
        """CommandInfo can be created with all required fields."""
        info = CommandInfo(
            name="test-command",
            brief="Test command description",
            detailed_help="Detailed help for test command",
            args=["ARG1"],
            options=["--option VALUE"],
            examples=["test-command ARG1"],
        )
        assert info.name == "test-command"
        assert info.brief == "Test command description"
        assert info.detailed_help == "Detailed help for test command"
        assert "ARG1" in info.args
        assert "--option VALUE" in info.options
        assert "test-command ARG1" in info.examples

    def test_command_info_empty_name_fails(self) -> None:
        """CommandInfo requires non-empty name."""
        with pytest.raises(ValueError, match="String should have at least 1 character"):
            CommandInfo(
                name="",
                brief="Test command",
                detailed_help="Details",
                args=[],
                options=[],
                examples=[],
            )

    def test_command_info_empty_brief_fails(self) -> None:
        """CommandInfo requires non-empty brief."""
        with pytest.raises(ValueError, match="String should have at least 1 character"):
            CommandInfo(
                name="test",
                brief="",
                detailed_help="Details",
                args=[],
                options=[],
                examples=[],
            )

    def test_command_info_empty_detailed_help_fails(self) -> None:
        """CommandInfo requires non-empty detailed_help."""
        with pytest.raises(ValueError, match="String should have at least 1 character"):
            CommandInfo(
                name="test",
                brief="Brief",
                detailed_help="",
                args=[],
                options=[],
                examples=[],
            )


class TestGetCommandHelp:
    """Tests for get_command_help function."""

    def test_get_command_help_version(self) -> None:
        """get_command_help returns info for version command."""
        info = get_command_help("version")
        assert info.name == "version"
        assert len(info.brief) > 0
        assert len(info.detailed_help) > 0

    def test_get_command_help_init(self) -> None:
        """get_command_help returns info for init command."""
        info = get_command_help("init")
        assert info.name == "init"
        assert "initialize" in info.brief.lower() or "init" in info.brief.lower()

    def test_get_command_help_invalid_command(self) -> None:
        """get_command_help raises ValueError for invalid command name."""
        with pytest.raises(ValueError, match="Invalid command name 'badcommand'"):
            get_command_help("badcommand")

    def test_get_command_help_invalid_error_includes_valid_commands(self) -> None:
        """get_command_help error message lists valid commands."""
        with pytest.raises(ValueError, match=r"Valid commands:.*version"):
            get_command_help("badcommand")

    @pytest.mark.parametrize(
        "command_name",
        [
            "version",
            "init",
            "validate-connection",
            "export",
            "run-pipeline",
            "run-phase",
            "status",
            "help",
            "doctor",
            "explain",
        ],
    )
    def test_all_commands_have_complete_info(self, command_name: str) -> None:
        """All registered commands have complete information."""
        info = get_command_help(command_name)
        assert info.name == command_name
        assert len(info.brief) > 0
        assert len(info.detailed_help) > 0
        # args, options, examples can be empty lists for some commands

    def test_version_command_content(self) -> None:
        """Version command has expected content."""
        info = get_command_help("version")
        assert "version" in info.brief.lower()
        assert len(info.args) == 0
        assert len(info.options) == 0
        assert len(info.examples) > 0

    def test_init_command_content(self) -> None:
        """Init command has expected content."""
        info = get_command_help("init")
        assert "initialize" in info.brief.lower() or "init" in info.brief.lower()
        assert "rentl.toml" in info.detailed_help or "config" in info.detailed_help

    def test_help_command_content(self) -> None:
        """Help command has expected content."""
        info = get_command_help("help")
        assert "help" in info.brief.lower()
        assert len(info.examples) > 0

    def test_doctor_command_content(self) -> None:
        """Doctor command has expected content."""
        info = get_command_help("doctor")
        assert "diagnostic" in info.brief.lower() or "doctor" in info.brief.lower()
        assert "check" in info.detailed_help.lower()

    def test_explain_command_content(self) -> None:
        """Explain command has expected content."""
        info = get_command_help("explain")
        assert "explain" in info.brief.lower() or "phase" in info.brief.lower()
        assert "phase" in info.detailed_help.lower()

    def test_run_pipeline_command_content(self) -> None:
        """run-pipeline command has expected content."""
        info = get_command_help("run-pipeline")
        assert "pipeline" in info.brief.lower()
        assert len(info.examples) > 0

    def test_run_phase_command_content(self) -> None:
        """run-phase command has expected content."""
        info = get_command_help("run-phase")
        assert "phase" in info.brief.lower()
        assert "--phase" in " ".join(info.options)

    def test_run_pipeline_help_matches_cli_signature(self) -> None:
        """run-pipeline help text matches the actual CLI flag signature.

        Regression test for signpost 4: ensure help registry stays in sync
        with the real CLI. The CLI uses --target-language (singular, repeatable),
        not --target-languages (plural, comma-separated).
        """
        info = get_command_help("run-pipeline")

        # Options should document the singular flag
        options_text = " ".join(info.options)
        assert "--target-language" in options_text, (
            "Help should advertise --target-language (singular)"
        )
        assert "--target-languages" not in options_text, (
            "Help should NOT advertise --target-languages (plural)"
        )

        # Examples should demonstrate repeatable usage, not comma-separated
        examples_text = " ".join(info.examples)
        if "target-language" in examples_text:
            # If examples show target-language usage, it should be repeatable form
            assert (
                "--target-language en --target-language" in examples_text
                or examples_text.count("--target-language") <= 1
            ), "Examples should show repeatable flag usage, not comma-separated"
            assert "en,es" not in examples_text, (
                "Examples should not show comma-separated language codes"
            )

    def test_export_help_matches_cli_signature(self) -> None:
        """Export help text matches the actual CLI flag signature.

        Regression test for signpost 5: ensure export help registry stays in sync
        with the real CLI. The CLI uses --column-order (repeatable option),
        not comma-separated input.
        """
        info = get_command_help("export")

        # Options should document the repeatable flag
        options_text = " ".join(info.options)
        assert "--column-order" in options_text, (
            "Help should advertise --column-order flag"
        )
        # Should describe it as repeatable, not comma-separated
        column_order_line = next(
            (opt for opt in info.options if "--column-order" in opt), ""
        )
        assert "repeatable" in column_order_line.lower() or (
            "comma" not in column_order_line.lower()
        ), "Help should not describe --column-order as comma-separated"

        # Examples should not demonstrate comma-separated column-order usage
        examples_text = " ".join(info.examples)
        if "column-order" in examples_text:
            # If examples show column-order usage, it should be repeatable form
            assert (
                "--column-order" in examples_text
                and "," not in examples_text.split("--column-order")[1].split()[0]
            ), "Examples should show repeatable flag usage, not comma-separated"


class TestListCommands:
    """Tests for list_commands function."""

    def test_list_commands_returns_all_ten(self) -> None:
        """list_commands returns all 10 commands."""
        commands = list_commands()
        assert len(commands) == 10

    def test_list_commands_returns_tuples(self) -> None:
        """list_commands returns list of (name, brief) tuples."""
        commands = list_commands()
        for name, brief in commands:
            assert isinstance(name, str)
            assert isinstance(brief, str)
            assert len(name) > 0
            assert len(brief) > 0

    def test_list_commands_sorted_alphabetically(self) -> None:
        """list_commands returns commands sorted alphabetically."""
        commands = list_commands()
        names = [name for name, _ in commands]
        assert names == sorted(names)

    def test_list_commands_includes_core_commands(self) -> None:
        """list_commands includes expected core commands."""
        commands = list_commands()
        command_names = {name for name, _ in commands}
        expected_names = {
            "version",
            "init",
            "validate-connection",
            "export",
            "run-pipeline",
            "run-phase",
            "status",
            "help",
            "doctor",
            "explain",
        }
        assert command_names == expected_names

    def test_list_commands_briefs_non_empty(self) -> None:
        """list_commands returns non-empty briefs for all commands."""
        commands = list_commands()
        for _, brief in commands:
            assert len(brief) > 0
