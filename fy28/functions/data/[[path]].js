// Everything under /data is a published endpoint — JSON, CSV, plain text. Same rule as
// /docs: an HTML answer here means the file is not there.
// See functions/_notfound.js for why this is a Function and not a _redirects rule.
import { assetOr404 } from '../_notfound.js'

export const onRequest = assetOr404
