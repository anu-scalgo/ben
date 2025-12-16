"""Stripe configuration and client initialization."""

import stripe
from .settings import settings

# Initialize Stripe client
stripe.api_key = settings.stripe_secret_key

stripe_client = stripe

