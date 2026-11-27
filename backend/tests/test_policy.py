import pytest
from ajusta_core.policy import Action, ApprovalRequired, authorize_action


def test_allows_non_consequential_action():
    assert authorize_action(Action("format_response")) is True


def test_blocks_consequential_action_without_approval():
    with pytest.raises(ApprovalRequired):
        authorize_action(Action("publish_content", consequential=True))


def test_allows_consequential_action_after_explicit_approval():
    assert authorize_action(Action("publish_content", consequential=True, approved_by_user=True)) is True
