# Expiry Notification Object Name

## Goal

Make every MAX expiry notification immediately identifiable by object.

## Approved Format

Add the object's name as the first line, using the exact `Site.name` value:

```text
Объект: АМЕТИСТОВЫЙ

🔔 <existing notification title>
...
```

The object name is dynamic; the example is the Ametistovy site currently used by the customer.

## Behavior and Scope

- Apply the prefix to both urgent and planned expiry notifications.
- Apply it to manual triggers and scheduled sends through the shared notification flow.
- Store the same complete message in the notification log that is sent to MAX recipients.
- Keep expiry thresholds, recipient selection, and the rest of each notification body unchanged.

## Implementation

Load the `Site` for the resolved `site_id` in `trigger_notifications` and pass its name to the shared message formatter. The formatter prepends the approved object line before the existing title and batch list.

## Verification

- Add a regression test that checks the logged message starts with the site's name and retains the existing notification title and batch data.
- Cover urgent and planned messages; the shared formatter path covers both manual and scheduled triggers.
- Run the focused notification tests and the full backend test suite.
