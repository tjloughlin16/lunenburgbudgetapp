#!/usr/bin/env bash
# ONE-TIME AWS SETUP FOR TEXTRACT. Paste into AWS CloudShell (the >_ icon in the console's top
# bar), signed in as the account owner. It runs as YOU, so no admin key ever exists on a laptop.
#
#   1. paste it into CloudShell wrapped as a file (scripts/aws/copy_setup.sh puts exactly that on
#      the clipboard) -- never as bare lines: `set -e` and `exit` would close the CloudShell session
#   2. bash setup_textract.sh you@example.com      <- where the budget alerts go
#   3. copy the two key lines it prints at the end -- AWS shows the secret ONCE
#   4. on the laptop, in your OWN terminal (not through Claude, so the secret stays out of the
#      transcript):   aws configure --profile lunenburg-textract     region: us-east-1
#
# What it makes, and nothing else:
#   user    lunenburg-textract           may call AnalyzeDocument and DetectDocumentText, and read
#                                        its own budget. Nothing else: no S3, no IAM, no billing.
#   policy  LunenburgTextractDeny        denies all of Textract. Attached by the budget, never by hand.
#   role    LunenburgTextractBudgetAction what AWS Budgets assumes to attach that policy, and the
#                                        only thing it may do is attach or detach that one policy
#                                        to or from that one user.
#   budget  lunenburg-textract           $LIMIT_USD a month of Textract. Emails at 50% and 80% actual
#                                        and 100% forecast; at 100% ACTUAL it attaches the deny policy
#                                        AUTOMATICALLY. Budgets refresh a few times a day, so this
#                                        is a backstop: scripts/textract_spend.py caps at $50 first.
#
# Re-running is safe: anything that already exists is left as it is.
set -euo pipefail

ALERT_EMAIL="${1:-}"              # where the budget alerts go: the first argument
LIMIT_USD="10"                    # above textract_spend.py's $8 cap on purpose (TJ, 31 Oct 2026)
USER=lunenburg-textract
BUDGET=lunenburg-textract

case "$ALERT_EMAIL" in *@*.*) ;; *) echo "usage: bash setup_textract.sh you@example.com"; exit 1;; esac

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
echo "account $ACCOUNT"

# --- the user, and what it may do --------------------------------------------------------------
aws iam get-user --user-name "$USER" >/dev/null 2>&1 || aws iam create-user --user-name "$USER" >/dev/null
aws iam put-user-policy --user-name "$USER" --policy-name LunenburgTextractUse --policy-document "{
  \"Version\": \"2012-10-17\",
  \"Statement\": [
    {\"Effect\": \"Allow\",
     \"Action\": [\"textract:AnalyzeDocument\", \"textract:DetectDocumentText\"],
     \"Resource\": \"*\"},
    {\"Effect\": \"Allow\",
     \"Action\": \"budgets:ViewBudget\",
     \"Resource\": \"arn:aws:budgets::$ACCOUNT:budget/$BUDGET\"}
  ]}"
echo "user $USER: Textract read + its own budget"

# --- the cut-off -------------------------------------------------------------------------------
DENY_ARN="arn:aws:iam::$ACCOUNT:policy/LunenburgTextractDeny"
aws iam get-policy --policy-arn "$DENY_ARN" >/dev/null 2>&1 || aws iam create-policy \
  --policy-name LunenburgTextractDeny --policy-document '{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Deny", "Action": "textract:*", "Resource": "*"}]}' >/dev/null

ROLE=LunenburgTextractBudgetAction
aws iam get-role --role-name "$ROLE" >/dev/null 2>&1 || aws iam create-role --role-name "$ROLE" \
  --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Principal": {"Service": "budgets.amazonaws.com"},
                 "Action": "sts:AssumeRole"}]}' >/dev/null
aws iam put-role-policy --role-name "$ROLE" --policy-name AttachTextractDeny --policy-document "{
  \"Version\": \"2012-10-17\",
  \"Statement\": [{\"Effect\": \"Allow\",
     \"Action\": [\"iam:AttachUserPolicy\", \"iam:DetachUserPolicy\"],
     \"Resource\": \"arn:aws:iam::$ACCOUNT:user/$USER\",
     \"Condition\": {\"ArnEquals\": {\"iam:PolicyARN\": \"$DENY_ARN\"}}}]}"
ROLE_ARN="arn:aws:iam::$ACCOUNT:role/$ROLE"
echo "cut-off: $DENY_ARN, attachable only by $ROLE"

# --- the budget and its action -----------------------------------------------------------------
if ! aws budgets describe-budget --account-id "$ACCOUNT" --budget-name "$BUDGET" >/dev/null 2>&1; then
  aws budgets create-budget --account-id "$ACCOUNT" \
    --budget "{\"BudgetName\": \"$BUDGET\", \"BudgetType\": \"COST\", \"TimeUnit\": \"MONTHLY\",
               \"BudgetLimit\": {\"Amount\": \"$LIMIT_USD\", \"Unit\": \"USD\"},
               \"CostFilters\": {\"Service\": [\"Amazon Textract\"]}}" \
    --notifications-with-subscribers "[
      {\"Notification\": {\"NotificationType\": \"ACTUAL\", \"ComparisonOperator\": \"GREATER_THAN\",
        \"Threshold\": 50, \"ThresholdType\": \"PERCENTAGE\"},
       \"Subscribers\": [{\"SubscriptionType\": \"EMAIL\", \"Address\": \"$ALERT_EMAIL\"}]},
      {\"Notification\": {\"NotificationType\": \"ACTUAL\", \"ComparisonOperator\": \"GREATER_THAN\",
        \"Threshold\": 80, \"ThresholdType\": \"PERCENTAGE\"},
       \"Subscribers\": [{\"SubscriptionType\": \"EMAIL\", \"Address\": \"$ALERT_EMAIL\"}]},
      {\"Notification\": {\"NotificationType\": \"FORECASTED\", \"ComparisonOperator\": \"GREATER_THAN\",
        \"Threshold\": 100, \"ThresholdType\": \"PERCENTAGE\"},
       \"Subscribers\": [{\"SubscriptionType\": \"EMAIL\", \"Address\": \"$ALERT_EMAIL\"}]}]"
fi
if [ "$(aws budgets describe-budget-actions-for-budget --account-id "$ACCOUNT" --budget-name "$BUDGET" \
        --query 'length(Actions)' --output text)" = "0" ]; then
  sleep 10   # a role created seconds ago is not yet assumable by Budgets
  aws budgets create-budget-action --account-id "$ACCOUNT" --budget-name "$BUDGET" \
    --notification-type ACTUAL --action-type APPLY_IAM_POLICY \
    --action-threshold ActionThresholdValue=100,ActionThresholdType=PERCENTAGE \
    --definition "{\"IamActionDefinition\": {\"PolicyArn\": \"$DENY_ARN\", \"Users\": [\"$USER\"]}}" \
    --execution-role-arn "$ROLE_ARN" --approval-model AUTOMATIC \
    --subscribers SubscriptionType=EMAIL,Address="$ALERT_EMAIL" >/dev/null
fi
echo "budget $BUDGET: \$$LIMIT_USD/month of Textract; at 100% actual, $USER is denied Textract"

# --- the key, last, and only if the user has none ----------------------------------------------
if [ "$(aws iam list-access-keys --user-name "$USER" --query 'length(AccessKeyMetadata)' --output text)" = "0" ]; then
  echo
  echo "=== COPY THESE NOW. AWS will not show the secret again. ==="
  aws iam create-access-key --user-name "$USER" \
    --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text \
    | awk '{print "AWS Access Key ID:     " $1 "\nAWS Secret Access Key: " $2}'
else
  echo "$USER already has an access key; none created"
fi
