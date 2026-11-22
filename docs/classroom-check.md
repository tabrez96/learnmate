# Classroom check

## Purpose

Before any Classroom feature is built, find out whether the student's school-managed Google account can grant the app
read-only access to Google Classroom and Drive. A debug-only screen asks for the read-only scopes, lists the account's
courses, finds one coursework item with attachments and reads the metadata of its first Drive file.

## Setup

1. In a Google Cloud project, enable the Google Classroom API and the Google Drive API.
2. Configure the OAuth consent screen (External, Testing mode) and add both test accounts as test users.
3. Create an OAuth client of type Android with package `app.learnmate` and the debug SHA-1 from
   `cd android && ./gradlew signingReport`.
4. Put the client id in `android/local.properties` as `google.androidClientId=...`.

## Procedure

1. Run `./gradlew installDebug` from `android/`.
2. Open "Classroom check" and tap "Sign in and check".
3. Pick the account and copy the on-screen lines.
4. If the Google screen shows an error (for example "Access blocked" or `admin_policy_enforced`), copy its exact text.
5. Remove the app's access afterwards at myaccount.google.com/permissions.

## Results

| Account                | Signed in   | Scopes granted | Courses     | Attachments | Drive       | Exact error |
| ---------------------- | ----------- | -------------- | ----------- | ----------- | ----------- | ----------- |
| Personal account       | Not run yet | Not run yet    | Not run yet | Not run yet | Not run yet | Not run yet |
| School-managed account | Not run yet | Not run yet    | Not run yet | Not run yet | Not run yet | Not run yet |

## Decision

Pending: filled in after both runs. Keep one of the two outcomes below and delete the other.

- Sign-in works: the Classroom tickets use Google Classroom sign-in, with upload as the fallback when a link fails.
- Blocked: the Classroom tickets ship the upload fallback only; nothing else in the plan changes.

## Server responses

The server maps Google's API answers to these codes, and the app shows `classroom_access_denied` as S02's "Classroom
sign-in blocked" error state, with upload as the fallback.

| Google answer                | Server status | `error` code               |
| ---------------------------- | ------------- | -------------------------- |
| Classroom 401                | 409           | `classroom_sign_in_again`  |
| Classroom 403                | 403           | `classroom_access_denied`  |
| Classroom 404                | 404           | `classroom_not_found`      |
| Drive 401                    | 409           | `classroom_sign_in_again`  |
| Drive 403                    | 403           | `classroom_access_denied`  |
| Drive 404                    | 403           | `classroom_access_denied`  |
| Link is not a Classroom post | 422           | `classroom_link_invalid`   |
| Nothing usable attached      | 422           | `classroom_no_files`       |
| File over the size limit     | 413           | `classroom_file_too_large` |
| More files than the limit    | 422           | `classroom_too_many_files` |
| 429, 5xx or network error    | 502           | `classroom_unavailable`    |

A school admin block shows up on the device's Google screen ("Access blocked", `admin_policy_enforced`), before any
token reaches the server. When a token is granted and access is refused later, Google answers 403, which maps to
`classroom_access_denied`.

## Notes

- Schools often block third-party apps for accounts marked under 18 unless the school's admin allows the app. That shows
  up as a Google "Access blocked" screen, not as an error in the app.
- The token is never stored, logged or shown. The screen only exists in debug builds.
