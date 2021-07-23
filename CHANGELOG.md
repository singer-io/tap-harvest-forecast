# Changelog

## 1.1.3
  * Bug fixes to get the tap running again successfully [#24](https://github.com/singer-io/tap-harvest-forecast/pull/24)
    * Reverted change to how replication keys are assigned to fix AttributeError
    * Removed incomplete activate_version feature that was accidentally included

## 1.1.2
  *  Bug fix in `sync_endpoints` [#21](https://github.com/singer-io/tap-harvest-forecast/pull/21)

## [1.1.1](https://github.com/singer-io/tap-harvest-forecast/tree/v1.1.1) (2021-04-19)

[Full Changelog](https://github.com/singer-io/tap-harvest-forecast/compare/v1.1.0...v1.1.1)

**Merged pull requests:**

- Adding dummy circle file which only runs json validate [\#18](https://github.com/singer-io/tap-harvest-forecast/pull/18) ([asaf-erlich](https://github.com/asaf-erlich))
- Hotfix/forecast issue 13 [\#17](https://github.com/singer-io/tap-harvest-forecast/pull/17) ([cdilga](https://github.com/cdilga))

## 1.0.1
  * Update version of `requests` to `2.20.0` in response to CVE 2018-18074

## 1.0.0
  * Adds field selection and discovery mode [#1](https://github.com/singer-io/tap-harvest-forecast/pull/1)
  * Uses refresh token from OAuth flow instead of personal access token [#2](https://github.com/singer-io/tap-harvest-forecast/pull/2)

## 0.0.1
  * Initial release
