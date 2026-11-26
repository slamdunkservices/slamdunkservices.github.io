#!/bin/sh
# Data store fulfillment: one-time setup and deploy. Safe to re-run; every step is idempotent.
#
#   _store/fulfillment/deploy.sh setup     bucket, service account, IAM, token secret
#   _store/fulfillment/deploy.sh deploy    build and deploy the function (needs the Stripe secret)
#   _store/fulfillment/deploy.sh status    what exists, and what it is allowed to cost
#
# The one step this script will not do for you: putting the Stripe restricted key in
# Secret Manager. Create a restricted key in Stripe (Developers > API keys > Create
# restricted key) with WRITE on Checkout Sessions and READ on Prices, Products, Customers,
# Charges and PaymentIntents, nothing else, then:
#
#   printf '%s' 'rk_live_...' | gcloud secrets create stripe-datastore-key \
#       --project decent-beacon-412817 --replication-policy automatic --data-file=-
#
# Cost ceiling (all of these are set below; change them here, not in the console):
#   - bucket is private with public access prevention; files leave only via 5-minute signed URLs
#   - soft delete off, no versioning: a daily-overwritten file is stored once, not eight times
#   - --max-instances 2, 256 MB, scale to zero: idle cost is zero, and Cloud Run's free tier
#     (2M requests a month) is far above anything a store this size sends
#   - downloads throttled per buyer in main.py (DOWNLOADS_PER_HOUR)
# Egress is the only cost that scales with use: about $0.12 per GB downloaded. A full
# season of every file for one league is tens of MB compressed.
set -eu

PROJECT="${PROJECT:-decent-beacon-412817}"
REGION="${REGION:-us-central1}"
BUCKET="${BUCKET:-sdbs_datastore}"
SERVICE="${SERVICE:-datastore-fulfill}"
SA_NAME="datastore-fulfill"
SA="$SA_NAME@$PROJECT.iam.gserviceaccount.com"
ORIGINS="${ALLOWED_ORIGINS:-https://slamdunk.bet,http://localhost:4321}"
here="$(cd "$(dirname "$0")" && pwd)"

setup() {
  if ! gcloud storage buckets describe "gs://$BUCKET" --project "$PROJECT" >/dev/null 2>&1; then
    gcloud storage buckets create "gs://$BUCKET" --project "$PROJECT" --location "$REGION" \
      --default-storage-class STANDARD --uniform-bucket-level-access \
      --public-access-prevention --soft-delete-duration=0
  fi
  gcloud storage buckets update "gs://$BUCKET" --project "$PROJECT" \
    --public-access-prevention --no-versioning --soft-delete-duration=0 \
    --update-labels purpose=datastore >/dev/null

  gcloud iam service-accounts describe "$SA" --project "$PROJECT" >/dev/null 2>&1 || \
    gcloud iam service-accounts create "$SA_NAME" --project "$PROJECT" \
      --display-name "Data store fulfillment (read files, sign URLs)"
  # Read the store bucket only. No access to the league buckets, models or odds.
  gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" --project "$PROJECT" \
    --member "serviceAccount:$SA" --role roles/storage.objectViewer >/dev/null
  # Signing URLs without a key file: the account signs as itself through IAM.
  gcloud iam service-accounts add-iam-policy-binding "$SA" --project "$PROJECT" \
    --member "serviceAccount:$SA" --role roles/iam.serviceAccountTokenCreator >/dev/null

  if ! gcloud secrets describe datastore-token-secret --project "$PROJECT" >/dev/null 2>&1; then
    openssl rand -base64 48 | tr -d '\n' | gcloud secrets create datastore-token-secret \
      --project "$PROJECT" --replication-policy automatic --data-file=-
  fi
  for secret in datastore-token-secret stripe-datastore-key; do
    if gcloud secrets describe "$secret" --project "$PROJECT" >/dev/null 2>&1; then
      gcloud secrets add-iam-policy-binding "$secret" --project "$PROJECT" \
        --member "serviceAccount:$SA" --role roles/secretmanager.secretAccessor >/dev/null
    else
      echo "NOTE: secret $secret does not exist yet (see the header of this script)." >&2
    fi
  done
  echo "setup done: gs://$BUCKET, $SA"
}

deploy() {
  gcloud secrets describe stripe-datastore-key --project "$PROJECT" >/dev/null 2>&1 || {
    echo "stripe-datastore-key is not in Secret Manager yet; see the header of this script." >&2
    exit 1
  }
  setup
  gcloud run deploy "$SERVICE" --project "$PROJECT" --region "$REGION" \
    --source "$here" --function store --base-image python313 \
    --service-account "$SA" --allow-unauthenticated \
    --min-instances 0 --max-instances 2 --memory 256Mi --cpu 1 --concurrency 40 --timeout 30 \
    --set-env-vars "^@^BUCKET=$BUCKET@ALLOWED_ORIGINS=$ORIGINS@SITE_URL=${SITE_URL:-https://slamdunk.bet}" \
    --set-secrets "STRIPE_API_KEY=stripe-datastore-key:latest,TOKEN_SECRET=datastore-token-secret:latest"
  url="$(gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format 'value(status.url)')"
  echo "deployed: $url"
  echo "put that URL in _store/catalog.yml (store.api) and rebuild the store pages."
}

status() {
  gcloud storage buckets describe "gs://$BUCKET" --project "$PROJECT" \
    --format 'yaml(name,location,iamConfiguration.publicAccessPrevention,softDeletePolicy,versioning)' || true
  gcloud storage du -s "gs://$BUCKET" --project "$PROJECT" 2>/dev/null || true
  gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" \
    --format 'yaml(status.url,spec.template.metadata.annotations,spec.template.spec.containerConcurrency)' 2>/dev/null \
    || echo "service $SERVICE is not deployed"
}

case "${1:-}" in
  setup)  setup ;;
  deploy) deploy ;;
  status) status ;;
  *) echo "usage: $0 setup|deploy|status" >&2; exit 2 ;;
esac
