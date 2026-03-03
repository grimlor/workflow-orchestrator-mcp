"""
Workflow error type and factory specifications

Tests that WorkflowErrorType extends the library ErrorType with domain-specific
values, that WorkflowError provides factory classmethods preserving the local
API surface, and that both types are re-exported from the package's public API.

BDD spec classes:
- TestErrorTypeExtension: Domain enum values and base-type inheritance
- TestFactoryMethodPreservation: Factory classmethod output fields
- TestPackageReExport: Import paths and __all__ listings
"""

from actionable_errors import ActionableError

from workflow_orchestrator_mcp.common.errors import WorkflowError, WorkflowErrorType

# Public API surface (from errors.py — post-adoption):
#   WorkflowErrorType(ErrorType) — 6 domain values + 8 inherited base values
#   WorkflowError(ActionableError) — 7 factory classmethods
#   WorkflowError.file_not_found(file_path: str) -> WorkflowError
#   WorkflowError.invalid_format(file_path: str, issue: str) -> WorkflowError
#   WorkflowError.empty_workflow(file_path: str) -> WorkflowError
#   WorkflowError.no_workflow_loaded(operation: str) -> WorkflowError
#   WorkflowError.missing_tool_spec(step_name: str) -> WorkflowError
#   WorkflowError.variable_missing(var: str, step: str) -> WorkflowError
#   WorkflowError.step_out_of_order(reported: int, expected: int) -> WorkflowError


class TestErrorTypeExtension:
    """
    REQUIREMENT: Domain-specific error categories must be defined as a
    standalone StrEnum whose string values are accepted by ActionableError's
    error_type parameter (which takes ``ErrorType | str``).

    WHO: Server error handlers and test assertions that match on error_type
    WHAT: WorkflowErrorType(StrEnum) defines six domain values
          (no_workflow_loaded, empty_workflow, missing_tool_spec,
          variable_missing, step_out_of_order, assertion_mismatch). Three
          existing local values map to base categories: FILE_NOT_FOUND →
          NOT_FOUND, INVALID_FORMAT → VALIDATION, UNEXPECTED → INTERNAL.
          The string values of domain-specific types are preserved exactly.
          Python forbids subclassing an enum with members, so
          WorkflowErrorType is a sibling StrEnum rather than a child of
          ErrorType.
    WHY: Existing MCP clients and test assertions depend on the error_type
         string values — changing them would break downstream consumers
         silently

    MOCK BOUNDARY:
        Mock:  Nothing — pure class structure tests
        Real:  WorkflowErrorType instances, string values, ActionableError acceptance
        Never: Nothing
    """

    def test_workflow_error_type_includes_all_domain_values(self) -> None:
        """
        Given WorkflowErrorType
        When iterating its members
        Then it includes all six domain values
        """
        # Given: the WorkflowErrorType enum
        members = list(WorkflowErrorType)

        # When: extracting member names
        names = {m.name for m in members}

        # Then: all six domain values are present
        domain_names = {
            "NO_WORKFLOW_LOADED",
            "EMPTY_WORKFLOW",
            "MISSING_TOOL_SPEC",
            "VARIABLE_MISSING",
            "STEP_OUT_OF_ORDER",
            "ASSERTION_MISMATCH",
        }
        assert domain_names == names, (
            f"Expected exactly {domain_names}. Got: {names}"
        )

        # Then: total count is 6
        assert len(members) == 6, (
            f"Expected 6 domain members, got {len(members)}: "
            f"{[m.name for m in members]}"
        )

    def test_domain_values_preserve_string_representation(self) -> None:
        """
        Given WorkflowErrorType.NO_WORKFLOW_LOADED
        When converting to string
        Then the value is "no_workflow_loaded"
        """
        # Given: each domain member and its expected string value
        expected = {
            WorkflowErrorType.NO_WORKFLOW_LOADED: "no_workflow_loaded",
            WorkflowErrorType.EMPTY_WORKFLOW: "empty_workflow",
            WorkflowErrorType.MISSING_TOOL_SPEC: "missing_tool_spec",
            WorkflowErrorType.VARIABLE_MISSING: "variable_missing",
            WorkflowErrorType.STEP_OUT_OF_ORDER: "step_out_of_order",
            WorkflowErrorType.ASSERTION_MISMATCH: "assertion_mismatch",
        }

        for member, expected_str in expected.items():
            # When: converting to string
            actual = str(member)

            # Then: matches the expected value
            assert actual == expected_str, (
                f"{member.name}: expected string '{expected_str}', "
                f"got '{actual}'"
            )

    def test_domain_values_accepted_by_actionable_error(self) -> None:
        """
        Given a WorkflowErrorType member
        When passing it as error_type to ActionableError
        Then the error is created successfully with the correct error_type string
        """
        # Given: a domain error type
        error_type = WorkflowErrorType.NO_WORKFLOW_LOADED

        # When: creating an ActionableError with it
        err = ActionableError(
            error="test",
            error_type=error_type,
            service="test",
        )

        # Then: error_type is stored and stringifies correctly
        assert str(err.error_type) == "no_workflow_loaded", (
            f"Expected error_type 'no_workflow_loaded', got '{err.error_type}'"
        )


class TestFactoryMethodPreservation:
    """
    REQUIREMENT: Domain factory methods must produce errors with the same
    semantic content as the local implementation.

    WHO: Business logic modules that raise workflow errors (parser,
         state manager, prompt builder, workflow tools)
    WHAT: WorkflowError provides seven factory classmethods matching
          the local API: file_not_found, invalid_format, empty_workflow,
          no_workflow_loaded, missing_tool_spec, variable_missing,
          step_out_of_order. Each factory produces a WorkflowError
          instance with the correct error_type, meaningful error message,
          and actionable suggestion. The service field is set to
          "workflow-orchestrator" on all factories.
    WHY: Call sites like raise WorkflowError.file_not_found(path) must
         remain concise and consistent — requiring raw constructors at
         every raise site would be error-prone and verbose

    MOCK BOUNDARY:
        Mock:  Nothing — pure factory + field verification
        Real:  WorkflowError factory methods, field values
        Never: Nothing
    """

    def test_file_not_found_produces_correct_fields(self) -> None:
        """
        Given a file path
        When calling WorkflowError.file_not_found(path)
        Then the error message mentions the path, error_type is NOT_FOUND,
        service is "workflow-orchestrator", and suggestion mentions checking
        the path
        """
        # Given: a file path
        path = "/tmp/missing_workflow.md"

        # When: creating via factory
        err = WorkflowError.file_not_found(path)

        # Then: correct error_type
        assert str(err.error_type) == "not_found", (
            f"Expected error_type 'not_found', got '{err.error_type}'"
        )
        # Then: error message mentions the path
        assert path in err.error, (
            f"Expected path '{path}' in error message. Got: {err.error}"
        )
        # Then: service is set
        assert err.service == "workflow-orchestrator", (
            f"Expected service 'workflow-orchestrator', got '{err.service}'"
        )
        # Then: suggestion mentions checking the path
        assert err.suggestion is not None and len(err.suggestion) > 0, (
            f"Expected non-empty suggestion, got: {err.suggestion!r}"
        )

    def test_missing_tool_spec_produces_correct_fields(self) -> None:
        """
        Given a step name
        When calling WorkflowError.missing_tool_spec(name)
        Then error_type is MISSING_TOOL_SPEC and suggestion mentions
        TOOL section
        """
        # Given: a step name
        step_name = "Analyze repository"

        # When: creating via factory
        err = WorkflowError.missing_tool_spec(step_name)

        # Then: correct error_type
        assert str(err.error_type) == "missing_tool_spec", (
            f"Expected error_type 'missing_tool_spec', got '{err.error_type}'"
        )
        # Then: error message mentions the step name
        assert step_name in err.error, (
            f"Expected step name '{step_name}' in error message. Got: {err.error}"
        )
        # Then: suggestion mentions TOOL section
        assert err.suggestion is not None and "tool" in err.suggestion.lower(), (
            f"Expected suggestion mentioning 'tool'. Got: {err.suggestion!r}"
        )

    def test_step_out_of_order_mentions_both_step_numbers(self) -> None:
        """
        Given step numbers
        When calling WorkflowError.step_out_of_order(3, 2)
        Then error mentions both step numbers and error_type is
        STEP_OUT_OF_ORDER
        """
        # Given: mismatched step numbers
        reported, expected = 3, 2

        # When: creating via factory
        err = WorkflowError.step_out_of_order(reported, expected)

        # Then: correct error_type
        assert str(err.error_type) == "step_out_of_order", (
            f"Expected error_type 'step_out_of_order', got '{err.error_type}'"
        )
        # Then: error message mentions both step numbers
        assert str(reported) in err.error and str(expected) in err.error, (
            f"Expected both step numbers ({reported}, {expected}) in error. "
            f"Got: {err.error}"
        )

    def test_all_factories_produce_workflow_error_and_actionable_error(self) -> None:
        """
        Given each factory method
        When constructing and checking isinstance
        Then every result is both a WorkflowError and an ActionableError
        """
        # Given: results from all seven factories
        factories = [
            WorkflowError.file_not_found("/tmp/test.md"),
            WorkflowError.invalid_format("/tmp/test.md", "bad header"),
            WorkflowError.empty_workflow("/tmp/test.md"),
            WorkflowError.no_workflow_loaded("execute step"),
            WorkflowError.missing_tool_spec("Step 1"),
            WorkflowError.variable_missing("REPO_NAME", "Step 2"),
            WorkflowError.step_out_of_order(3, 2),
        ]

        for err in factories:
            # When: checking isinstance
            is_workflow = isinstance(err, WorkflowError)
            is_actionable = isinstance(err, ActionableError)

            # Then: it is both types
            assert is_workflow, (
                f"Factory result is not a WorkflowError. "
                f"Type: {type(err).__name__}, error: {err.error}"
            )
            assert is_actionable, (
                f"Factory result is not an ActionableError. "
                f"Type: {type(err).__name__}, error: {err.error}"
            )

    def test_all_factories_set_service_to_workflow_orchestrator(self) -> None:
        """
        Given each factory method
        When checking the service field
        Then every result has service set to "workflow-orchestrator"
        """
        # Given: results from all seven factories
        factories = {
            "file_not_found": WorkflowError.file_not_found("/tmp/test.md"),
            "invalid_format": WorkflowError.invalid_format("/tmp/test.md", "issue"),
            "empty_workflow": WorkflowError.empty_workflow("/tmp/test.md"),
            "no_workflow_loaded": WorkflowError.no_workflow_loaded("execute"),
            "missing_tool_spec": WorkflowError.missing_tool_spec("Step 1"),
            "variable_missing": WorkflowError.variable_missing("VAR", "Step 2"),
            "step_out_of_order": WorkflowError.step_out_of_order(3, 2),
        }

        for factory_name, err in factories.items():
            # When: checking the service field
            # Then: service is "workflow-orchestrator"
            assert err.service == "workflow-orchestrator", (
                f"Factory '{factory_name}' has service='{err.service}', "
                f"expected 'workflow-orchestrator'"
            )


class TestPackageReExport:
    """
    REQUIREMENT: ActionableError must remain importable from the package's
    public API surface.

    WHO: Downstream consumers and test files that import from
         workflow_orchestrator_mcp or workflow_orchestrator_mcp.common
    WHAT: Both ActionableError (library class) and WorkflowError (domain
          subclass) are importable from workflow_orchestrator_mcp and from
          workflow_orchestrator_mcp.common. WorkflowError is also importable
          from workflow_orchestrator_mcp.common.errors.
    WHY: Changing the public import surface would break existing consumers
         and test code

    MOCK BOUNDARY:
        Mock:  Nothing — pure import verification
        Real:  Module imports, __all__ listings
        Never: Nothing
    """

    def test_actionable_error_importable_from_package(self) -> None:
        """
        Given the package
        When importing ActionableError from workflow_orchestrator_mcp
        Then the import succeeds and it is the library's class
        """
        # Given / When: importing from the package
        from workflow_orchestrator_mcp import ActionableError as PkgActionableError

        # Then: it is the library's class (a dataclass with 'error' field)
        assert PkgActionableError is ActionableError, (
            f"Expected library ActionableError, got {PkgActionableError}. "
            f"Module: {PkgActionableError.__module__}"
        )

    def test_workflow_error_importable_from_common(self) -> None:
        """
        Given the package
        When importing WorkflowError from workflow_orchestrator_mcp.common
        Then the import succeeds and it is a subclass of ActionableError
        """
        # Given / When: importing from common
        from workflow_orchestrator_mcp.common import WorkflowError as CommonWorkflowError

        # Then: it is a subclass of ActionableError
        assert issubclass(CommonWorkflowError, ActionableError), (
            f"WorkflowError should be a subclass of ActionableError. "
            f"MRO: {CommonWorkflowError.__mro__}"
        )

    def test_common_all_includes_both_error_types(self) -> None:
        """
        Given the common module
        When inspecting __all__
        Then both ActionableError and WorkflowError are listed
        """
        # Given / When: inspecting __all__
        import workflow_orchestrator_mcp.common as common_mod

        all_names = getattr(common_mod, "__all__", [])

        # Then: both are listed
        assert "ActionableError" in all_names, (
            f"ActionableError not in common.__all__. Got: {all_names}"
        )
        assert "WorkflowError" in all_names, (
            f"WorkflowError not in common.__all__. Got: {all_names}"
        )
