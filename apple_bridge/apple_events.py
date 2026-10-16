"""Apple Calendar and Reminders automation via osascript.

Every call names the calendar / reminders list explicitly, so the bridge only
touches the collections you configure. The first run triggers macOS Automation
prompts for Calendar and Reminders.
"""
from __future__ import annotations

import json
import subprocess

_SCRIPT = r'''
on jsonQuote(valueText)
    if valueText is missing value then return "\"\""
    set valueText to valueText as text
    set valueText to my replaceText(valueText, "\\", "\\\\")
    set valueText to my replaceText(valueText, "\"", "\\\"")
    set valueText to my replaceText(valueText, return, "\\n")
    set valueText to my replaceText(valueText, linefeed, "\\n")
    set valueText to my replaceText(valueText, tab, "\\t")
    return "\"" & valueText & "\""
end jsonQuote

on replaceText(sourceText, searchText, replacementText)
    set savedDelimiters to AppleScript's text item delimiters
    set AppleScript's text item delimiters to searchText
    set parts to every text item of sourceText
    set AppleScript's text item delimiters to replacementText
    set resultText to parts as text
    set AppleScript's text item delimiters to savedDelimiters
    return resultText
end replaceText

on pad2(valueNumber)
    if valueNumber < 10 then return "0" & (valueNumber as text)
    return valueNumber as text
end pad2

on dateISO(dateValue)
    set monthNumber to (month of dateValue) as integer
    return ((year of dateValue) as text) & "-" & my pad2(monthNumber) & "-" & my pad2(day of dateValue) & "T" & my pad2(hours of dateValue) & ":" & my pad2(minutes of dateValue) & ":" & my pad2(seconds of dateValue)
end dateISO

on dateFromISO(dateText)
    set dateValue to current date
    set day of dateValue to 1
    set year of dateValue to (text 1 thru 4 of dateText) as integer
    set monthNames to {January, February, March, April, May, June, July, August, September, October, November, December}
    set month of dateValue to item ((text 6 thru 7 of dateText) as integer) of monthNames
    set day of dateValue to (text 9 thru 10 of dateText) as integer
    set hours of dateValue to (text 12 thru 13 of dateText) as integer
    set minutes of dateValue to (text 15 thru 16 of dateText) as integer
    set seconds of dateValue to (text 18 thru 19 of dateText) as integer
    return dateValue
end dateFromISO

on eventJSON(targetEvent)
    tell application "Calendar"
        return "{\"id\":" & my jsonQuote(uid of targetEvent) & ",\"title\":" & my jsonQuote(summary of targetEvent) & ",\"start\":" & my jsonQuote(my dateISO(start date of targetEvent)) & ",\"end\":" & my jsonQuote(my dateISO(end date of targetEvent)) & ",\"notes\":" & my jsonQuote(description of targetEvent) & "}"
    end tell
end eventJSON

on run argv
    set actionName to item 1 of argv

    if actionName is "list_calendars" then
        set outputText to "["
        tell application "Calendar"
            repeat with c in calendars
                if outputText is not "[" then set outputText to outputText & ","
                set outputText to outputText & my jsonQuote(name of c)
            end repeat
        end tell
        return outputText & "]"
    end if

    set collectionName to item 2 of argv

    if actionName is "check" then
        set reminderCollectionName to item 3 of argv
        set calendarFound to false
        set remindersFound to false
        tell application "Calendar"
            try
                set targetCalendar to first calendar whose name is collectionName
                set calendarFound to true
            end try
        end tell
        tell application "Reminders"
            try
                set targetList to first list whose name is reminderCollectionName
                set remindersFound to true
            end try
        end tell
        return "{\"calendar_available\":" & calendarFound & ",\"reminders_available\":" & remindersFound & "}"
    end if

    if actionName is "list_events" then
        set rangeStart to my dateFromISO(item 3 of argv)
        set rangeEnd to my dateFromISO(item 4 of argv)
        set outputText to "["
        tell application "Calendar"
            set targetCalendar to first calendar whose name is collectionName
            repeat with targetEvent in (every event of targetCalendar whose start date < rangeEnd and end date > rangeStart)
                if outputText is not "[" then set outputText to outputText & ","
                set outputText to outputText & my eventJSON(targetEvent)
            end repeat
        end tell
        return outputText & "]"
    end if

    if actionName is "list_reminders" then
        set outputText to "["
        tell application "Reminders"
            set targetList to first list whose name is collectionName
            repeat with targetReminder in (every reminder of targetList whose completed is false)
                if outputText is not "[" then set outputText to outputText & ","
                set reminderDue to due date of targetReminder
                set dueValue to "null"
                if reminderDue is not missing value then set dueValue to my jsonQuote(my dateISO(reminderDue))
                set outputText to outputText & "{\"id\":" & my jsonQuote(id of targetReminder) & ",\"title\":" & my jsonQuote(name of targetReminder) & ",\"notes\":" & my jsonQuote(body of targetReminder) & ",\"due\":" & dueValue & ",\"completed\":false}"
            end repeat
        end tell
        return outputText & "]"
    end if

    if actionName is "create_event" then
        set eventTitle to item 3 of argv
        set eventStart to my dateFromISO(item 4 of argv)
        set eventEnd to my dateFromISO(item 5 of argv)
        set eventNotes to item 6 of argv
        tell application "Calendar"
            set targetCalendar to first calendar whose name is collectionName
            set targetEvent to make new event at end of events of targetCalendar with properties {summary:eventTitle, start date:eventStart, end date:eventEnd, description:eventNotes}
            return "{\"id\":" & my jsonQuote(uid of targetEvent) & "}"
        end tell
    end if

    if actionName is "update_event" then
        set eventId to item 3 of argv
        tell application "Calendar"
            set targetCalendar to first calendar whose name is collectionName
            set targetEvent to first event of targetCalendar whose uid is eventId
            set summary of targetEvent to item 4 of argv
            set start date of targetEvent to my dateFromISO(item 5 of argv)
            set end date of targetEvent to my dateFromISO(item 6 of argv)
            set description of targetEvent to item 7 of argv
            return "{\"id\":" & my jsonQuote(uid of targetEvent) & "}"
        end tell
    end if

    if actionName is "create_reminder" then
        set reminderTitle to item 3 of argv
        set reminderNotes to item 4 of argv
        set reminderDueText to item 5 of argv
        tell application "Reminders"
            set targetList to first list whose name is collectionName
            if reminderDueText is "-" then
                set targetReminder to make new reminder at end of reminders of targetList with properties {name:reminderTitle, body:reminderNotes}
            else
                set targetReminder to make new reminder at end of reminders of targetList with properties {name:reminderTitle, body:reminderNotes, due date:(my dateFromISO(reminderDueText))}
            end if
            return "{\"id\":" & my jsonQuote(id of targetReminder) & "}"
        end tell
    end if

    if actionName is "update_reminder" then
        set reminderId to item 3 of argv
        set reminderDueText to item 6 of argv
        tell application "Reminders"
            set targetList to first list whose name is collectionName
            set targetReminder to first reminder of targetList whose id is reminderId
            set name of targetReminder to item 4 of argv
            set body of targetReminder to item 5 of argv
            if reminderDueText is "-" then
                set due date of targetReminder to missing value
            else
                set due date of targetReminder to my dateFromISO(reminderDueText)
            end if
            return "{\"id\":" & my jsonQuote(id of targetReminder) & "}"
        end tell
    end if

    error "Unsupported Apple Calendar/Reminders operation"
end run
'''

TIMEOUT_SECONDS = 150
TIMEOUT_ATTEMPTS = 2


def call_apple_events(*arguments: str) -> dict | list:
    """Run one action. Calendar/Reminders can stall for a minute while iCloud
    syncs, so a timeout is retried once before giving up."""
    for attempt in range(1, TIMEOUT_ATTEMPTS + 1):
        try:
            result = subprocess.run(
                ["/usr/bin/osascript", "-e", _SCRIPT, *arguments],
                check=False, capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
            )
            break
        except subprocess.TimeoutExpired as error:
            if attempt == TIMEOUT_ATTEMPTS:
                raise RuntimeError(
                    f"Calendar/Reminders automation timed out after {TIMEOUT_ATTEMPTS} attempts of {TIMEOUT_SECONDS}s"
                ) from error
    if result.returncode:
        message = f"Calendar/Reminders automation failed (exit {result.returncode})"
        if result.stderr.strip():
            message += f": {result.stderr.strip()}"
        raise RuntimeError(message)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("Calendar/Reminders returned invalid JSON") from error
