# Security, backups, and retention

## Encryption

Data is encrypted in transit with TLS 1.2 or newer and at rest with AES-256. Encryption keys are rotated every 90 days.

## Backups

Larkspur takes a full backup of every workspace each day and keeps backups for 35 days. Backups are stored in a second region. The recovery point objective is 24 hours and the recovery time objective is 4 hours.

## Deleted items

Deleted tasks and projects go to the trash and can be restored for 30 days. After 30 days they are removed permanently. Owners can empty the trash early.

## Deleting a workspace

When an owner deletes a workspace, it is disabled at once and permanently erased after 14 days. Backups that contain the workspace expire on their normal 35 day schedule.

## Audit logs

On the Business plan, audit logs record sign-ins, permission changes, exports, and token creation. Logs are kept for one year and can be streamed to a security tool through the API.
