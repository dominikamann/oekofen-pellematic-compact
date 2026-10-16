# Security policy

## Supported versions

Only the latest release receives fixes. Please update before reporting a problem.

## Reporting a vulnerability

Please report security problems privately via
[GitHub security advisories](https://github.com/dominikamann/oekofen-pellematic-compact/security/advisories/new)
instead of opening a public issue. You will get an answer within a few days.

## Keep your heater safe

- The JSON interface URL contains the heater's password. Never post it unredacted in issues,
  discussions or screenshots.
- Do not expose the heater's JSON port to the internet. The interface is meant for the local
  network; access from outside belongs behind a VPN.
- Keys without the `L_` prefix are writable. Extra values added via `json.properties` should be
  read-only `L_` keys only (see the README).
