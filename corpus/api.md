# REST API

The Larkspur API lets you read and write projects, tasks, and comments.

## Authentication

Create a personal access token under Settings, Developer. Send it in the Authorization header as a bearer token. Tokens inherit the permissions of the person who created them. Workspace admins can revoke any token.

## Rate limits

Each token can make 600 requests per minute. Bulk endpoints count as one request per call but accept at most 100 items. When you go over the limit the API returns status 429 with a Retry-After header that gives the number of seconds to wait.

## Pagination

List endpoints return 50 items by default and up to 200 with the limit parameter. Responses include a next_cursor field. Pass it as the cursor parameter to get the next page. A missing next_cursor means you have reached the end.

## Webhooks

Webhooks send a POST request when tasks are created, updated, or completed. Each request carries a signature header computed with HMAC SHA-256 and your webhook secret. Failed deliveries are retried with exponential backoff for up to 24 hours.

## Versioning

The API is versioned by date. Send the Larkspur-Version header to pin a version. Breaking changes are announced at least 90 days ahead.
