// Everything under /docs is an archive file — never an HTML page. If the asset server
// answered with the app shell, the document is missing and must say so.
// See functions/_notfound.js for why this is a Function and not a _redirects rule.
import { assetOr404 } from '../_notfound.js'

export const onRequest = assetOr404
