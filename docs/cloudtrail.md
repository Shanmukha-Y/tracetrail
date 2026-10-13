# CloudTrail evidence

TraceTrail reads supplied local JSON records. It does not query AWS, configure
logging, verify an AWS account's coverage, or validate CloudTrail digest
signatures. A citation identifies the exact bytes of the supplied file and its
record index; it does not establish that AWS produced the file or that the
supplied window is complete.

## Inputs and queries

The store accepts a JSON object with a `Records` array, matching AWS's
[log-file examples](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-log-file-examples.html).
CloudTrail trail deliveries normally use `.json.gz`; decompress them locally
before ingestion. TraceTrail currently accepts uncompressed JSON only. Directory
inputs include every `.json` file below that directory, so keep hypothesis files
outside the log directory. Duplicate event IDs are rejected rather than merged.

`eventTime` is the request's completion time in UTC. The timeline sorts this
field, rather than assuming file order or delivery time describes the action
sequence. `sourceIPAddress` can be an address, an AWS service DNS name, or an
AWS-internal value. Matching this field does not identify a person. Some services
record error information within `responseElements`, so an absent top-level
`errorCode` alone is not a universal success test. TraceTrail's fixed propositions
use the narrower wording "without a recorded API error."
See the [CloudTrail field reference](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference-record-contents.html).

`userIdentity.accessKeyId` identifies the key used to sign a request, including a
temporary key. AWS can omit or empty this field. For assumed-role requests,
`sessionIssuer` describes the assumed role; it does not establish the human
operator. The session's `creationDate` describes when its temporary credentials
were issued. See the [identity reference](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference-user-identity.html).

AWS logs `AssumeRole` as `readOnly: true` while retaining its response elements,
except `secretAccessKey`. When the returned
`responseElements.credentials.accessKeyId` matches a later record's
`userIdentity.accessKeyId`, the records support a credential link. This special
STS response rule does not extend to ordinary read-only APIs.
See [IAM and STS logging](https://docs.aws.amazon.com/IAM/latest/UserGuide/cloudtrail-integration.html).

## What the API sequence establishes

`StopLogging` concerns the specified trail's recording and delivery. It does not
disable independent CloudTrail Event history. A stop/start sequence alone does
not establish every interval of delivery, other trails' state, or approval for a
change. The synthetic files are supplied event windows, not a claim that every
record came from the named trail. Seeing later records does not establish that
the stopped trail continued recording. See [StopLogging](https://docs.aws.amazon.com/awscloudtrail/latest/APIReference/API_StopLogging.html)
and [Event history](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-cloudtrail-events.html).

The live `GetTrailStatus` API returns `IsLogging`. An ordinary CloudTrail record
of this read-only request has null `responseElements`, so the request alone
cannot establish the returned trail state. TraceTrail reads logs only; a live
API response is outside its present evidence sources. See
[GetTrailStatus](https://docs.aws.amazon.com/awscloudtrail/latest/APIReference/API_GetTrailStatus.html)
and the [CloudTrail field reference](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference-record-contents.html).

S3 `GetObject` and `DeleteObject` are data events. CloudTrail does not log data
events by default, and Event history excludes them. Supplied object events
therefore assume appropriate data-event coverage. A recorded object request
does not establish credential theft, authorization by a person, or a later
transfer to an external destination. See
[S3 CloudTrail events](https://docs.aws.amazon.com/AmazonS3/latest/userguide/cloudtrail-logging-s3-info.html).

## Synthetic suite versions

All fixture accounts, credentials, resources, and events are invented. The
fixtures exercise evidence queries and annotation scoring; they are not
recordings of an incident.

The legacy v1 suite contained three realism errors: `AssumeRole` was marked
`readOnly: false`; several roles shared a hardcoded credential issuance date;
and its maintenance `GetTrailStatus` record embedded `isLogging: true` despite
being read-only. Its maintenance annotations treated that embedded value as
status evidence. Results from that suite retain these limitations and cannot
establish status inference from ordinary CloudTrail logs.

The [v2 manifest](../evaluation/cases-v2.json) corrects these fields and separates
start/status request facts from uncertainty about the trail's later state. Its
fixtures live in `fixtures/v2/`. The unrelated BackupRead session has no supplied
issuance event; its creation date is invented at its first observed event time,
not a discovered issuance. Preserve the legacy suite and its results; compare
models only within the same frozen suite, prompts, tools, and budgets. The
[evaluation guide](../evaluation/README.md) describes the current manifest and
the boundary between development and held-out cases.
