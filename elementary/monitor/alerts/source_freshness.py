import datetime
from typing import Optional

from elementary.clients.slack.schema import SlackMessageSchema
from elementary.monitor.alerts.alert import Alert
from elementary.utils.json_utils import prettify_json_str_set
from elementary.utils.log import get_logger
from elementary.utils.time import (
    convert_datetime_utc_str_to_timezone_str,
    DATETIME_FORMAT,
)


logger = get_logger(__name__)


class SourceFreshnessAlert(Alert):
    TABLE_NAME = "alerts_source_freshness"

    def __init__(
        self,
        unique_id: str,
        snapshotted_at: Optional[str],
        max_loaded_at: Optional[str],
        max_loaded_at_time_ago_in_s: Optional[float],
        source_name: str,
        identifier: str,
        freshness_error_after: str,
        freshness_warn_after: str,
        freshness_filter: str,
        path: str,
        error: str,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.unique_id = unique_id
        self.snapshotted_at = (
            convert_datetime_utc_str_to_timezone_str(snapshotted_at, self.timezone)
            if snapshotted_at
            else None
        )
        self.max_loaded_at = (
            convert_datetime_utc_str_to_timezone_str(max_loaded_at, self.timezone)
            if max_loaded_at
            else None
        )
        self.max_loaded_at_time_ago_in_s = max_loaded_at_time_ago_in_s
        self.source_name = source_name
        self.identifier = identifier
        self.freshness_error_after = freshness_error_after
        self.freshness_warn_after = freshness_warn_after
        self.freshness_filter = freshness_filter
        self.path = path
        self.error = error

    def to_slack(self, is_slack_workflow: bool = False) -> SlackMessageSchema:
        icon = self._get_slack_status_icon()
        slack_message = self._initial_slack_message()

        # Alert info section
        self._add_header_to_slack_msg(
            slack_message, f"{icon} dbt source freshness alert"
        )
        self._add_context_to_slack_msg(
            slack_message,
            [
                f"*Source:* {self.alias}     |",
                f"*Status:* {self.status}     |",
                f"*{self.detected_at.strftime(DATETIME_FORMAT)}*",
            ],
        )
        self._add_divider(slack_message)

        compacted_sections = [
            f"*Tags*\n{prettify_json_str_set(self.tags) if self.tags else '_No tags_'}",
            f"*Owners*\n{prettify_json_str_set(self.owners) if self.owners else '_No owners_'}",
            f"*Subscribers*\n{prettify_json_str_set(self.subscribers) if self.subscribers else '_No subscribers_'}",
        ]
        self._add_compacted_sections_to_slack_msg(
            slack_message, compacted_sections, add_to_attachment=True
        )

        # Pad till "See more"
        self._add_empty_section_to_slack_msg(slack_message, add_to_attachment=True)
        self._add_empty_section_to_slack_msg(slack_message, add_to_attachment=True)
        self._add_empty_section_to_slack_msg(slack_message, add_to_attachment=True)

        # Result sectiom
        self._add_text_section_to_slack_msg(
            slack_message, f":mag: *Run*", add_to_attachment=True
        )
        self._add_divider(slack_message, add_to_attachment=True)

        self._add_text_section_to_slack_msg(
            slack_message,
            f"```{self.message.strip()}```",
            add_to_attachment=True,
        )

        if self.status == "runtime error":
            self._add_context_to_slack_msg(
                slack_message, [f"*Run message*"], add_to_attachment=True
            )
            self._add_text_section_to_slack_msg(
                slack_message,
                f"Failed to calculate the source freshness\n" f"```{self.error}```",
                add_to_attachment=True,
            )
        else:
            compacted_sections = [
                f"*Time Elapsed*\n{datetime.timedelta(seconds=self.max_loaded_at_time_ago_in_s)}",
                f"*Last Record At*\n{self.max_loaded_at}",
                f"*Sampled At*\n{self.snapshotted_at}",
            ]
            self._add_compacted_sections_to_slack_msg(
                slack_message, compacted_sections, add_to_attachment=True
            )

        # Configuration section
        if (
            self.freshness_error_after
            or self.freshness_warn_after
            or self.freshness_filter
            or self.path
        ):
            self._add_text_section_to_slack_msg(
                slack_message,
                f":hammer_and_wrench: *Configuration*",
                add_to_attachment=True,
            )
            self._add_divider(slack_message, add_to_attachment=True)

            if self.freshness_error_after:
                self._add_context_to_slack_msg(
                    slack_message, [f"*Error after*"], add_to_attachment=True
                )
                self._add_text_section_to_slack_msg(
                    slack_message,
                    f"`{self.freshness_error_after}`",
                    add_to_attachment=True,
                )

            if self.freshness_warn_after:
                self._add_context_to_slack_msg(
                    slack_message, [f"*Warn after*"], add_to_attachment=True
                )
                self._add_text_section_to_slack_msg(
                    slack_message,
                    f"`{self.freshness_warn_after}`",
                    add_to_attachment=True,
                )

            if self.freshness_filter:
                self._add_context_to_slack_msg(
                    slack_message, [f"*Filter*"], add_to_attachment=True
                )
                self._add_text_section_to_slack_msg(
                    slack_message,
                    f"`{self.freshness_filter}`",
                    add_to_attachment=True,
                )

            if self.path:
                self._add_context_to_slack_msg(
                    slack_message, [f"*Path*"], add_to_attachment=True
                )
                self._add_text_section_to_slack_msg(
                    slack_message,
                    f"`{self.path}`",
                    add_to_attachment=True,
                )
        return SlackMessageSchema(**slack_message)
