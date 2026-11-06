# Single sign-on

Single sign-on (SSO) is available on the Business plan. Larkspur supports SAML 2.0 and OpenID Connect.

## Setting up SAML

An owner opens Settings, Security, and selects Configure SSO. Copy the Assertion Consumer Service URL and the Entity ID into your identity provider, then paste the provider's metadata URL back into Larkspur. Select Test connection before you enforce SSO.

## Enforcing SSO

When SSO is enforced, members must sign in through the identity provider. Password sign-in is turned off for everyone except owners, who keep a password as a recovery path. This prevents a misconfigured provider from locking the whole workspace out.

## Just-in-time provisioning

With just-in-time provisioning on, a person who signs in through the identity provider for the first time gets a member account automatically. Removing someone from the identity provider does not delete their Larkspur account. Use SCIM to deprovision accounts automatically.

## Troubleshooting

If members are locked out after an SSO change, an owner can sign in with a password and turn off enforcement under Settings, Security. The most common cause is a certificate that expired or was rotated in the identity provider.
